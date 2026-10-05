"""Cabeceras de seguridad para todas las respuestas."""

from __future__ import annotations

from flask import Flask, Response

# La página solo carga recursos propios (sin scripts ni estilos en línea): se puede prohibir todo lo demás.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


def install_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response: Response) -> Response:
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
