"""Interfaz común de las fuentes de empleo y utilidades compartidas."""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any, ClassVar, TypeVar

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.salary import DEFAULT_RATES
from buscador_empleos.infrastructure.http import HttpClient, HttpResponse, ensure_ok

T = TypeVar("T")
R = TypeVar("R")

#: Recibe mensajes para mostrar al usuario ('  Torre: fallo ...').
LogFn = Callable[[str], None]
#: Espera cortés entre peticiones: ``pause(mínimo, máximo)`` segundos.
Pause = Callable[[float, float], None]


def ignore_log(_message: str) -> None:
    """Registro por defecto: descarta los mensajes."""


def random_pause(low: float, high: float) -> None:
    """Espera un tiempo aleatorio para no saturar a la fuente ni parecer un robot."""
    time.sleep(random.uniform(low, high))


_PARALLEL_DETAILS = 2


class JobSource(ABC):
    """Un portal de empleo. Cada fuente se implementa en su propio módulo.

    Para agregar una: subclasifica, define ``name`` e implementa :meth:`search`, y regístrala en
    :func:`buscador_empleos.infrastructure.sources.build_sources`.
    """

    #: Nombre visible (casillas de la página, filtros e identificador de las ofertas).
    name: ClassVar[str]

    def __init__(
        self,
        http: HttpClient,
        *,
        rates: Mapping[str, float] | None = None,
        pause: Pause | None = None,
    ) -> None:
        self._http = http
        self._rates = rates or DEFAULT_RATES
        self._pause = pause or random_pause

    @abstractmethod
    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        """Busca ofertas para un cargo.

        Args:
            query: cargo buscado ('analista de datos').
            pages: cuántas páginas de resultados leer.
            log: para avisar al usuario de problemas (sin lanzar excepciones por una página caída).
        """

    # ---------------------------------------------------------------- ayudas para las subclases
    def _get(self, url: str, **kwargs: Any) -> HttpResponse:
        """GET que lanza :class:`~buscador_empleos.infrastructure.http.HttpStatusError` si es 4xx/5xx."""
        return ensure_ok(self._http.get(url, **kwargs), url)

    def _post_json(self, url: str, body: Any, **kwargs: Any) -> HttpResponse:
        return ensure_ok(self._http.post_json(url, body, **kwargs), url)

    @staticmethod
    def _map_parallel(function: Callable[[T], R], items: Iterable[T]) -> list[R]:
        """Aplica ``function`` a cada elemento con unos pocos hilos (pedir detalles es lo lento)."""
        with ThreadPoolExecutor(_PARALLEL_DETAILS) as pool:
            return list(pool.map(function, items))


def is_open_to_colombia(restrictions: str | Iterable[str] | None) -> bool:
    """Ofertas remotas: ¿puede aplicar alguien en Colombia? (sin restricción, o que la incluye)."""
    if not restrictions:
        return True
    text = restrictions if isinstance(restrictions, str) else " ".join(restrictions)
    lowered = text.lower()
    return any(marker in lowered for marker in _OPEN_MARKERS)


_OPEN_MARKERS = (
    "colombia",
    "latam",
    "latin america",
    "latinoam",
    "south america",
    "americas",
    "worldwide",
    "anywhere",
    "global",
    "world",
    "everywhere",
)
