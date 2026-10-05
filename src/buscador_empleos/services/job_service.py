"""Caso de uso «consultar ofertas guardadas»."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.repository import JobRepository


class JobNotFoundError(LookupError):
    """No existe una oferta con ese identificador."""


@dataclass(frozen=True, slots=True)
class JobView:
    """Una oferta junto con los datos que dependen del momento de la consulta."""

    job: Job
    days_ago: float | None


@dataclass(frozen=True, slots=True)
class JobListing:
    updated: str | None
    items: list[JobView]


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def list_jobs(self, *, now: datetime | None = None) -> JobListing:
        """Todas las ofertas guardadas con su antigüedad calculada a ``now``."""
        snapshot = self._repository.load()
        current = now or datetime.now()
        items = [
            JobView(job, job.days_ago(fallback_seen=snapshot.updated, now=current)) for job in snapshot.jobs
        ]
        return JobListing(snapshot.updated, items)

    def get_job(self, job_id: str) -> Job:
        job = self._repository.find(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job
