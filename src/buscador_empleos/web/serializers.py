"""Cómo se representan los objetos del dominio en JSON (el contrato con el navegador)."""

from __future__ import annotations

from typing import Any

from buscador_empleos.domain.job import Job
from buscador_empleos.services.job_service import JobListing, JobView


def job_summary(view: JobView) -> dict[str, Any]:
    """Una oferta para la lista: sin la descripción (se pide aparte, para que la lista cargue rápido)."""
    data = view.job.to_dict()
    del data["description"]
    data["has_description"] = view.job.has_description()
    data["days_ago"] = view.days_ago
    return data


def job_listing(listing: JobListing) -> dict[str, Any]:
    return {"updated": listing.updated, "jobs": [job_summary(view) for view in listing.items]}


def job_description(job: Job) -> dict[str, Any]:
    return {"id": job.id, "title": job.title, "description": job.description}
