"""Configuración de la aplicación, leída de variables de entorno.

Variable                    Por defecto       Descripción
BUSCADOR_HOST               127.0.0.1         Dirección donde escucha el servidor
BUSCADOR_PORT               5000              Puerto
BUSCADOR_DATA_FILE          data/jobs.json    Archivo donde se guardan las ofertas
BUSCADOR_DEFAULT_PAGES      2                 Páginas por fuente si no se indica otra cosa
BUSCADOR_MAX_PAGES          5                 Tope de páginas por fuente
BUSCADOR_HTTP_TIMEOUT       25                Segundos de espera por petición
BUSCADOR_FX                 (vacío)           Tasas a pesos, ej. 'USD=3900,EUR=4300'
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from buscador_empleos.domain.salary import DEFAULT_RATES

_PREFIX = "BUSCADOR_"


class ConfigError(ValueError):
    """Un valor de configuración no es válido."""


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 5000
    data_file: Path = Path("data") / "jobs.json"
    default_pages: int = 2
    max_pages: int = 5
    http_timeout: float = 25.0
    fx_rates: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_RATES))
    debug: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ConfigError(f"El puerto debe estar entre 1 y 65535 (recibido {self.port}).")
        if self.max_pages < 1:
            raise ConfigError(f"MAX_PAGES debe ser al menos 1 (recibido {self.max_pages}).")
        if not 1 <= self.default_pages <= self.max_pages:
            raise ConfigError(
                f"DEFAULT_PAGES debe estar entre 1 y {self.max_pages} (recibido {self.default_pages})."
            )
        if self.http_timeout <= 0:
            raise ConfigError(f"HTTP_TIMEOUT debe ser positivo (recibido {self.http_timeout}).")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Valores por defecto, sobrescritos con lo que haya en el entorno."""
        source = os.environ if env is None else env
        defaults = cls()
        rates = dict(DEFAULT_RATES)
        rates.update(_parse_rates(source.get(f"{_PREFIX}FX", "")))
        return cls(
            host=_text(source, "HOST", defaults.host),
            port=_integer(source, "PORT", defaults.port),
            data_file=Path(_text(source, "DATA_FILE", str(defaults.data_file))),
            default_pages=_integer(source, "DEFAULT_PAGES", defaults.default_pages),
            max_pages=_integer(source, "MAX_PAGES", defaults.max_pages),
            http_timeout=_decimal(source, "HTTP_TIMEOUT", defaults.http_timeout),
            fx_rates=rates,
        )


def _text(source: Mapping[str, str], name: str, default: str) -> str:
    raw = source.get(_PREFIX + name, "").strip()
    return raw or default


def _integer(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(_PREFIX + name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{_PREFIX}{name}={raw!r} no es válido: se esperaba un número entero.") from exc


def _decimal(source: Mapping[str, str], name: str, default: float) -> float:
    raw = source.get(_PREFIX + name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{_PREFIX}{name}={raw!r} no es válido: se esperaba un número.") from exc


def _parse_rates(raw: str) -> dict[str, float]:
    """'USD=3900, EUR=4300' -> {'USD': 3900.0, 'EUR': 4300.0}."""
    rates: dict[str, float] = {}
    for item in filter(None, (part.strip() for part in raw.split(","))):
        code, separator, value = item.partition("=")
        try:
            if not separator or not code.strip():
                raise ValueError(item)
            rates[code.strip().upper()] = float(value)
        except ValueError as exc:
            raise ConfigError(f"{_PREFIX}FX tiene un valor inválido: {item!r} (usa 'USD=3900').") from exc
    return rates
