"""Traduce las excepciones de la aplicación a respuestas HTTP coherentes (JSON en la API)."""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException

from buscador_empleos.domain.repository import RepositoryError
from buscador_empleos.services.job_service import JobNotFoundError
from buscador_empleos.web.schemas import RequestError

logger = logging.getLogger(__name__)

_MESSAGES = {404: "Recurso no encontrado", 405: "Método no permitido", 413: "La petición es demasiado grande"}


def _json_error(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"error": message}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(RequestError)
    def bad_request(error: RequestError) -> tuple[Response, int]:
        return _json_error(str(error), 400)

    @app.errorhandler(JobNotFoundError)
    def not_found(_error: JobNotFoundError) -> tuple[Response, int]:
        return _json_error("Oferta no encontrada", 404)

    @app.errorhandler(RepositoryError)
    def storage_failure(error: RepositoryError) -> tuple[Response, int]:
        logger.error("Error de almacenamiento: %s", error)
        return _json_error(str(error), 500)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> tuple[Response, int] | HTTPException:
        # En la API siempre JSON; las páginas conservan la respuesta HTML por defecto.
        if request.path.startswith("/api/"):
            status = error.code or 500
            return _json_error(_MESSAGES.get(status, error.name), status)
        return error
