"""Persistencia de ofertas en un archivo JSON."""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from app.models.catalog import CATALOG_VERSION
from app.models.job import Job


class JobRepository:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._cache = None

    def load(self) -> Tuple[Optional[str], List[Job]]:
        """Devuelve (fecha de la última actualización, ofertas). Se cachea mientras el archivo no cambie."""
        if not self.path.exists():
            return None, []
        stat = self.path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache
        if cached and cached[0] == stamp:
            return cached[1], cached[2]
        data = json.loads(self.path.read_text(encoding="utf-8"))
        # recalcular tecnologias/cargos es costoso: solo se hace si cambio el catalogo
        stale = data.get("catalog") != CATALOG_VERSION
        jobs = [Job.from_dict(j, refresh=stale) for j in data.get("jobs", [])]
        if stale:
            self._save(jobs, updated=data.get("updated"))
            stamp = (self.path.stat().st_mtime_ns, self.path.stat().st_size)
        result = (data.get("updated"), jobs)
        self._cache = (stamp, *result)
        return result

    def find(self, job_id: str) -> Optional[Job]:
        return next((j for j in self.load()[1] if j.id == job_id), None)

    def merge(self, found: Iterable[Job]) -> Tuple[int, int]:
        """Añade/actualiza ofertas conservando el historial. Devuelve (nuevas leídas, total guardado)."""
        with self._lock:
            _, existing = self.load()
            by_id = {j.id: j for j in existing}
            count = 0
            for job in found:
                count += 1
                # no pisar un detalle bueno con uno vacío (p. ej. por un 429 de la fuente)
                if not job.has_description() and by_id.get(job.id) and by_id[job.id].has_description():
                    continue
                by_id[job.id] = job
            self._save(by_id.values())
            return count, len(by_id)

    def _save(self, jobs: Iterable[Job], updated: Optional[str] = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"updated": updated or datetime.now().isoformat(timespec="minutes"),
                   "catalog": CATALOG_VERSION,
                   "jobs": [j.to_dict() for j in jobs]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
