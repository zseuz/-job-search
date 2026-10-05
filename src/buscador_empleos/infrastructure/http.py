"""Clientes HTTP intercambiables.

Las fuentes dependen de la interfaz :class:`HttpClient`, no de una biblioteca concreta. Así se pueden
probar sin red (con un cliente falso) y cambiar de biblioteca sin tocarlas.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import requests

DEFAULT_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}
JSON_HEADERS: Mapping[str, str] = {**DEFAULT_HEADERS, "Accept": "application/json"}


class HttpStatusError(Exception):
    """La fuente respondió con un código de error (4xx/5xx)."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} en {url}")
        self.status_code = status_code
        self.url = url


class HttpResponse(Protocol):
    """Lo que las fuentes leen de una respuesta (``requests`` y ``curl_cffi`` lo cumplen)."""

    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class HttpClient(Protocol):
    """Lo mínimo que necesitan las fuentes. No lanza error por códigos 4xx/5xx: lo decide quien llama."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...

    def post_json(
        self,
        url: str,
        body: Any,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse: ...


def ensure_ok(response: HttpResponse, url: str) -> HttpResponse:
    """Devuelve la respuesta tal cual o lanza :class:`HttpStatusError` si el código es 4xx/5xx."""
    if response.status_code >= 400:
        raise HttpStatusError(response.status_code, url)
    return response


class RequestsClient:
    """Cliente basado en ``requests``. Sirve para APIs JSON y para páginas sin protección anti-bot."""

    def __init__(self, timeout: float = 25.0, headers: Mapping[str, str] | None = None) -> None:
        self._timeout = timeout
        self._headers = dict(headers or DEFAULT_HEADERS)

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        return requests.get(
            url,
            params=dict(params or {}),
            headers={**self._headers, **(headers or {})},
            timeout=self._timeout,
        )

    def post_json(
        self,
        url: str,
        body: Any,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        return requests.post(
            url,
            params=dict(params or {}),
            json=body,
            headers={**self._headers, **(headers or {})},
            timeout=self._timeout,
        )


class ChromeClient:
    """Cliente que imita la huella TLS de Chrome (``curl_cffi``) para portales detrás de Cloudflare."""

    def __init__(self, timeout: float = 25.0, impersonate: str = "chrome") -> None:
        self._timeout = timeout
        self._impersonate = impersonate

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        from curl_cffi import requests as curl  # import diferido: solo hace falta si se usa

        return curl.get(
            url,
            params=dict(params or {}),
            headers=dict(headers or {}),
            impersonate=self._impersonate,
            timeout=self._timeout,
        )

    def post_json(
        self,
        url: str,
        body: Any,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        from curl_cffi import requests as curl

        return curl.post(
            url,
            params=dict(params or {}),
            json=body,
            headers=dict(headers or {}),
            impersonate=self._impersonate,
            timeout=self._timeout,
        )
