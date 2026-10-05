"""API JSON que consume la página."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from buscador_empleos import __version__
from buscador_empleos.web import schemas, serializers
from buscador_empleos.web.controllers import get_container

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/health")
def health() -> Response:
    return jsonify({"status": "ok", "version": __version__})


@bp.get("/jobs")
def list_jobs() -> Response:
    return jsonify(serializers.job_listing(get_container().job_service.list_jobs()))


@bp.get("/jobs/<path:job_id>/description")
def job_description(job_id: str) -> Response:
    return jsonify(serializers.job_description(get_container().job_service.get_job(job_id)))


@bp.get("/status")
def status() -> Response:
    return jsonify(get_container().search_service.status())


@bp.post("/search")
def search() -> tuple[Response, int]:
    container = get_container()
    body = request.get_json(silent=True)
    search_request = schemas.parse_search_request(body, container.settings)
    if not container.search_service.start(search_request):
        return jsonify({"error": "Ya hay una búsqueda en curso"}), 409
    return jsonify({"ok": True}), 202
