"""Validación de lo que llega por HTTP: convierte el JSON del cliente en objetos del servicio."""

from __future__ import annotations

from typing import Any

from buscador_empleos.services.search_service import SearchRequest
from buscador_empleos.settings import Settings


class RequestError(ValueError):
    """La petición del cliente es inválida (se responde 400 con el mensaje)."""


def parse_search_request(body: Any, settings: Settings) -> SearchRequest:
    """Valida el cuerpo de ``POST /api/search``.

    Raises:
        RequestError: si no es un objeto JSON, faltan cargos o fuentes, o los tipos no son los esperados.
    """
    if not isinstance(body, dict):
        raise RequestError("El cuerpo de la petición debe ser un objeto JSON.")
    roles = _strings(body.get("roles"), "roles")
    sources = _strings(body.get("sources"), "sources")
    if not roles:
        raise RequestError("Indica al menos un cargo a buscar.")
    if not sources:
        raise RequestError("Indica al menos una fuente donde buscar.")
    expand = body.get("expand", False)
    if not isinstance(expand, bool):
        raise RequestError("'expand' debe ser verdadero o falso.")
    return SearchRequest(
        roles=tuple(roles),
        sources=tuple(sources),
        pages=_pages(body.get("pages", settings.default_pages), settings.max_pages),
        expand=expand,
    )


def _strings(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RequestError(f"'{name}' debe ser una lista de textos.")
    return [item.strip() for item in value if item.strip()]


def _pages(value: Any, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestError("'pages' debe ser un número entero.")
    return max(1, min(value, maximum))
