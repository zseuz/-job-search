"""Fábrica de la aplicación Flask (arquitectura MVC)."""
import threading

from flask import Flask

from app import config
from app.controllers import jobs_controller, pages_controller
from app.models.job_repository import JobRepository
from app.services.search_service import SearchService


def create_app(data_file=config.DATA_FILE) -> Flask:
    app = Flask(__name__, template_folder="views/templates", static_folder="views/static")

    repository = JobRepository(data_file)                       # Modelo
    app.extensions["repository"] = repository
    app.extensions["search_service"] = SearchService(repository)

    threading.Thread(target=repository.load, daemon=True).start()  # precalienta la cache de ofertas

    app.register_blueprint(pages_controller.bp)                 # Controladores
    app.register_blueprint(jobs_controller.bp)
    return app
