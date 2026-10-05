"""Contrato de persistencia de ofertas (puerto). La implementación vive en ``infrastructure``."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple, Protocol

from buscador_empleos.domain.job import Job


class RepositoryError(RuntimeError):
    """No se pudo leer o escribir el almacenamiento (archivo dañado, disco lleno, permisos...)."""


class Snapshot(NamedTuple):
    """Lo guardado en un momento dado."""

    updated: str | None  # cuándo se actualizó por última vez (ISO 8601)
    jobs: list[Job]


class MergeResult(NamedTuple):
    found: int  # ofertas recibidas
    total: int  # ofertas guardadas tras la mezcla


class JobRepository(Protocol):
    """Almacén de ofertas. Cualquier implementación que cumpla esto sirve (archivo, SQLite, memoria...)."""

    def load(self) -> Snapshot: ...

    def find(self, job_id: str) -> Job | None: ...

    def merge(self, jobs: Iterable[Job]) -> MergeResult:
        """Agrega o actualiza ofertas conservando el historial.

        Una oferta nueva sin descripción **no** reemplaza a una guardada que sí la tiene
        (por ejemplo cuando la fuente respondió 429 al pedir el detalle).
        """
        ...
