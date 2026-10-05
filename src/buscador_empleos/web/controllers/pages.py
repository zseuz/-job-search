"""Páginas HTML."""

from __future__ import annotations

from flask import Blueprint, render_template

from buscador_empleos import __version__
from buscador_empleos.domain.catalog import ROLE_DATA, ROLE_DEVELOPER, ROLE_OTHER, TECH_GROUPS
from buscador_empleos.domain.modality import Modality
from buscador_empleos.web.controllers import get_container

bp = Blueprint("pages", __name__)


@bp.get("/")
def index() -> str:
    container = get_container()
    settings = container.settings
    return render_template(
        "index.html",
        version=__version__,
        sources=container.search_service.source_names,
        modalities=[m.value for m in Modality],
        role_kinds=[ROLE_DATA, ROLE_DEVELOPER, ROLE_OTHER],
        default_pages=settings.default_pages,
        max_pages=settings.max_pages,
        page_options=sorted(
            {1, 2, 3, settings.default_pages, settings.max_pages} & set(range(1, settings.max_pages + 1))
        ),
        # Se entrega al JavaScript como JSON: los grupos viven una sola vez, en el dominio.
        boot={"techGroups": {group: list(techs) for group, techs in TECH_GROUPS.items()}},
    )
