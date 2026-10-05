"""Orquesta las búsquedas en las fuentes y guarda el resultado, en un hilo de fondo."""
import threading
from typing import List

from app.models.extractors import expand_queries
from app.models.job_repository import JobRepository
from app.services.scrapers import SOURCES


class SearchService:
    def __init__(self, repository: JobRepository):
        self.repository = repository
        self._lock = threading.Lock()
        self._state = {"running": False, "log": [], "done": 0, "total": 0}

    @property
    def sources(self) -> List[str]:
        return list(SOURCES)

    def status(self) -> dict:
        return dict(self._state)

    def start(self, roles: List[str], sources: List[str], pages: int, expand: bool = False) -> bool:
        """Lanza la búsqueda. Devuelve False si ya hay una en curso."""
        roles = [r.strip() for r in roles if r.strip()]
        if expand:
            roles = expand_queries(roles)
        sources = [s for s in sources if s in SOURCES]
        with self._lock:
            if self._state["running"]:
                return False
            self._state.update(running=True, log=[], done=0, total=len(roles) * len(sources))
        threading.Thread(target=self._run, args=(roles, sources, pages), daemon=True).start()
        return True

    def _log(self, message: str) -> None:
        self._state["log"].append(message)

    def _run(self, roles, sources, pages) -> None:
        try:
            found = {}
            for role in roles:
                for name in sources:
                    self._log(f"Buscando '{role}' en {name}...")
                    try:
                        for job in SOURCES[name](role, pages, self._log):
                            job.query = role
                            found.setdefault(job.id, job)
                    except Exception as e:  # una fuente caída no debe tumbar las demás
                        self._log(f"  {name}: error {e}")
                    self._state["done"] += 1
            count, total = self.repository.merge(found.values())
            self._log(f"Listo: {count} ofertas encontradas ({total} en total).")
        finally:
            self._state["running"] = False
