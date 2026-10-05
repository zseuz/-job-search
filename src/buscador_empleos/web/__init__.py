"""Capa web (presentación): controladores, plantillas y recursos estáticos."""

from __future__ import annotations

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from buscador_empleos.bootstrap import Container, build_container
from buscador_empleos.settings import Settings
from buscador_empleos.web.controllers import api, pages
from buscador_empleos.web.errors import register_error_handlers
from buscador_empleos.web.security import install_security_headers


def create_app(settings: Settings | None = None, *, container: Container | None = None) -> Flask:
    """Fábrica de la aplicación Flask.

    Args:
        settings: configuración; por defecto se lee del entorno.
        container: servicios ya construidos (las pruebas pasan los suyos con fuentes y almacén falsos).
    """
    wired = container or build_container(settings or Settings.from_env())
    app = Flask(__name__)
    if isinstance(app.json, DefaultJSONProvider):
        app.json.ensure_ascii = False  # que los acentos viajen como acentos, no como ú
    app.extensions["container"] = wired
    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp)
    register_error_handlers(app)
    install_security_headers(app)
    return app
