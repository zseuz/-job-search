"""Repositorio de ofertas en un archivo JSON."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from buscador_empleos.domain.catalog import CATALOG_VERSION
from buscador_empleos.domain.job import Job
from buscador_empleos.domain.repository import MergeResult, RepositoryError, Snapshot

logger = logging.getLogger(__name__)


class JsonJobRepository:
    """Implementa :class:`~buscador_empleos.domain.repository.JobRepository` sobre un archivo JSON.

    * Es seguro entre hilos (la búsqueda corre en segundo plano mientras la web lee).
    * Cachea lo leído mientras el archivo no cambie (reconstruir cada oferta es costoso).
    * Escribe de forma atómica (archivo temporal + reemplazo): un corte a mitad no deja el JSON dañado.
    * Si el catálogo de tecnologías cambió, reclasifica las ofertas guardadas una sola vez.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._cache: tuple[tuple[int, int], Snapshot] | None = None

    # ---------------------------------------------------------------- lectura
    def load(self) -> Snapshot:
        with self._lock:
            if not self.path.exists():
                return Snapshot(None, [])
            stat = self.path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            if self._cache is not None and self._cache[0] == stamp:
                return self._cache[1]

            data = self._read()
            stale = data.get("catalog") != CATALOG_VERSION
            jobs = self._build_jobs(data.get("jobs", []), refresh=stale)
            updated = data.get("updated")
            if stale:
                self._write(jobs, updated=updated)
                stat = self.path.stat()
                stamp = (stat.st_mtime_ns, stat.st_size)
            snapshot = Snapshot(updated, jobs)
            self._cache = (stamp, snapshot)
            return snapshot

    def find(self, job_id: str) -> Job | None:
        return next((job for job in self.load().jobs if job.id == job_id), None)

    # ---------------------------------------------------------------- escritura
    def merge(self, jobs: Iterable[Job]) -> MergeResult:
        with self._lock:
            by_id = {job.id: job for job in self.load().jobs}
            received = 0
            for job in jobs:
                received += 1
                previous = by_id.get(job.id)
                # No pisar un detalle bueno con uno vacío (p. ej. la fuente respondió 429).
                if previous is not None and not job.has_description() and previous.has_description():
                    continue
                by_id[job.id] = job
            self._write(by_id.values())
            return MergeResult(received, len(by_id))

    # ---------------------------------------------------------------- internos
    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RepositoryError(f"No se pudo leer {self.path}: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("jobs", []), list):
            raise RepositoryError(f"Formato inesperado en {self.path}: se esperaba {{'jobs': [...]}}")
        return data

    @staticmethod
    def _build_jobs(raw_jobs: list[Any], *, refresh: bool) -> list[Job]:
        jobs: list[Job] = []
        for raw in raw_jobs:
            try:
                jobs.append(Job.from_dict(raw, refresh=refresh))
            except (TypeError, ValueError):
                logger.warning("Se omite una oferta guardada con formato inválido: %.80r", raw)
        return jobs

    def _write(self, jobs: Iterable[Job], *, updated: str | None = None) -> None:
        payload = {
            "updated": updated or datetime.now().isoformat(timespec="minutes"),
            "catalog": CATALOG_VERSION,
            "jobs": [job.to_dict() for job in jobs],
        }
        temp = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.path)
        except OSError as exc:
            raise RepositoryError(f"No se pudo guardar {self.path}: {exc}") from exc
