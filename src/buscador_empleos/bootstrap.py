"""Raíz de composición: el único lugar donde se conectan las piezas concretas.

El resto del código recibe sus dependencias por constructor y no sabe qué implementación hay detrás.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from buscador_empleos.domain.repository import JobRepository
from buscador_empleos.infrastructure.persistence.json_repository import JsonJobRepository
from buscador_empleos.infrastructure.sources import JobSource, build_sources
from buscador_empleos.services.job_service import JobService
from buscador_empleos.services.search_service import SearchService
from buscador_empleos.settings import Settings


@dataclass(frozen=True, slots=True)
class Container:
    """Los servicios ya construidos que usa la capa web."""

    settings: Settings
    repository: JobRepository
    job_service: JobService
    search_service: SearchService


def build_container(
    settings: Settings,
    *,
    repository: JobRepository | None = None,
    sources: Mapping[str, JobSource] | None = None,
) -> Container:
    """Arma la aplicación. Las pruebas pasan ``repository`` y ``sources`` falsos."""
    repo = repository or JsonJobRepository(settings.data_file)
    available = (
        sources
        if sources is not None
        else build_sources(rates=settings.fx_rates, timeout=settings.http_timeout)
    )
    return Container(
        settings=settings,
        repository=repo,
        job_service=JobService(repo),
        search_service=SearchService(repo, available),
    )
