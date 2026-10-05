"""Controlador de la API: lista ofertas, lanza búsquedas y reporta su progreso."""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.config import DEFAULT_PAGES, MAX_PAGES

bp = Blueprint("jobs", __name__, url_prefix="/api")


def _services():
    return current_app.extensions["repository"], current_app.extensions["search_service"]


@bp.get("/jobs")
def list_jobs():
    repository, _ = _services()
    updated, jobs = repository.load()
    now = datetime.now()
    payload = []
    for job in jobs:
        item = job.to_dict()
        item["has_description"] = job.has_description()
        del item["description"]  # se pide aparte (/api/jobs/<id>/description) para no inflar la lista
        item["days_ago"] = job.days_ago(fallback_seen=updated, now=now)
        payload.append(item)
    return jsonify({"updated": updated, "jobs": payload})


@bp.get("/jobs/<path:job_id>/description")
def job_description(job_id):
    repository, _ = _services()
    job = repository.find(job_id)
    if job is None:
        return jsonify({"error": "Oferta no encontrada"}), 404
    return jsonify({"id": job.id, "title": job.title, "description": job.description})


@bp.get("/status")
def status():
    _, service = _services()
    return jsonify(service.status())


@bp.post("/search")
def search():
    _, service = _services()
    body = request.get_json(force=True, silent=True) or {}
    pages = max(1, min(int(body.get("pages", DEFAULT_PAGES)), MAX_PAGES))
    started = service.start(body.get("roles", []), body.get("sources", []), pages,
                            expand=bool(body.get("expand", False)))
    if not started:
        return jsonify({"error": "Ya hay una búsqueda en curso"}), 409
    return jsonify({"ok": True})
