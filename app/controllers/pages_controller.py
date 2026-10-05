"""Controlador de páginas: entrega la vista principal."""
from flask import Blueprint, current_app, render_template

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    service = current_app.extensions["search_service"]
    return render_template("index.html", sources=service.sources)
