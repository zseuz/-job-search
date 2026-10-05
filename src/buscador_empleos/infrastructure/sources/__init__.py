"""Fuentes de empleo disponibles y su construcción."""

from __future__ import annotations

from collections.abc import Mapping

from buscador_empleos.infrastructure.http import ChromeClient, HttpClient, RequestsClient
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, Pause
from buscador_empleos.infrastructure.sources.computrabajo import ComputrabajoSource
from buscador_empleos.infrastructure.sources.elempleo import ElempleoSource
from buscador_empleos.infrastructure.sources.getonboard import GetOnBoardSource
from buscador_empleos.infrastructure.sources.hireline import HirelineSource
from buscador_empleos.infrastructure.sources.indeed import IndeedSource
from buscador_empleos.infrastructure.sources.linkedin import LinkedinSource
from buscador_empleos.infrastructure.sources.torre import TorreSource

__all__ = ["JobSource", "LogFn", "Pause", "build_sources"]


def build_sources(
    *,
    http: HttpClient | None = None,
    chrome: HttpClient | None = None,
    rates: Mapping[str, float] | None = None,
    pause: Pause | None = None,
    timeout: float = 25.0,
) -> dict[str, JobSource]:
    """Crea todas las fuentes, en el orden en que se muestran, indexadas por nombre.

    Args:
        http: cliente para APIs y páginas sin protección anti-bot (por defecto ``requests``).
        chrome: cliente que imita a Chrome, para portales detrás de Cloudflare (por defecto ``curl_cffi``).
        rates: tasas de cambio a pesos para los salarios en otras monedas.
        pause: espera entre peticiones (inyectable para que las pruebas no esperen).
    """
    plain = http or RequestsClient(timeout)
    browser = chrome or ChromeClient(timeout)
    sources: list[JobSource] = [
        ComputrabajoSource(plain, rates=rates, pause=pause),
        ElempleoSource(plain, rates=rates, pause=pause),
        HirelineSource(browser, rates=rates, pause=pause),
        GetOnBoardSource(plain, rates=rates, pause=pause),
        TorreSource(plain, rates=rates, pause=pause),
        LinkedinSource(plain, rates=rates, pause=pause),
        IndeedSource(browser, rates=rates, pause=pause),
    ]
    return {source.name: source for source in sources}
