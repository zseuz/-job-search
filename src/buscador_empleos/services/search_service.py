"""Caso de uso «actualizar ofertas»: busca en las fuentes elegidas y guarda el resultado."""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from buscador_empleos.domain.classification import expand_queries
from buscador_empleos.domain.job import Job
from buscador_empleos.domain.repository import JobRepository
from buscador_empleos.infrastructure.sources import JobSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Lo que el usuario pide buscar."""

    roles: tuple[str, ...]
    sources: tuple[str, ...]
    pages: int = 2
    expand: bool = False


@dataclass(slots=True)
class SearchStatus:
    """Progreso de la búsqueda en curso (o de la última)."""

    running: bool = False
    log: list[str] = field(default_factory=list)
    done: int = 0
    total: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {**asdict(self), "log": list(self.log)}


class SearchService:
    """Lanza una búsqueda en un hilo de fondo; solo permite una a la vez."""

    def __init__(self, repository: JobRepository, sources: Mapping[str, JobSource]) -> None:
        self._repository = repository
        self._sources = sources
        self._lock = threading.Lock()
        self._status = SearchStatus()

    @property
    def source_names(self) -> list[str]:
        return list(self._sources)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status.snapshot()

    def start(self, request: SearchRequest) -> bool:
        """Inicia la búsqueda. Devuelve ``False`` si ya hay una en curso."""
        roles = [role.strip() for role in request.roles if role.strip()]
        if request.expand:
            roles = expand_queries(roles)
        sources = [name for name in request.sources if name in self._sources]
        with self._lock:
            if self._status.running:
                return False
            self._status = SearchStatus(running=True, total=len(roles) * len(sources))
        thread = threading.Thread(
            target=self._run, args=(roles, sources, request.pages), name="job-search", daemon=True
        )
        thread.start()
        return True

    # ---------------------------------------------------------------- hilo de fondo
    def _log(self, message: str) -> None:
        logger.info(message.strip())
        with self._lock:
            self._status.log.append(message)

    def _advance(self) -> None:
        with self._lock:
            self._status.done += 1

    def _run(self, roles: Sequence[str], sources: Sequence[str], pages: int) -> None:
        try:
            found: dict[str, Job] = {}
            for role in roles:
                for name in sources:
                    self._log(f"Buscando '{role}' en {name}...")
                    try:
                        for job in self._sources[name].search(role, pages, self._log):
                            job.query = role
                            found.setdefault(job.id, job)
                    except Exception as exc:  # una fuente caída no debe tumbar las demás
                        logger.exception("Falló la fuente %s", name)
                        self._log(f"  {name}: error {exc}")
                    self._advance()
            result = self._repository.merge(found.values())
            self._log(f"Listo: {result.found} ofertas encontradas ({result.total} en total).")
        except Exception as exc:  # p. ej. disco lleno: avisar en pantalla en vez de fallar en silencio
            logger.exception("No se pudieron guardar las ofertas")
            self._log(f"Error al guardar las ofertas: {exc}")
        finally:
            with self._lock:
                self._status.running = False
