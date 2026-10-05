"""Controladores: reciben la petición HTTP, llaman a un servicio y devuelven la respuesta.

No contienen reglas de negocio: eso vive en ``domain`` y ``services``.
"""

from __future__ import annotations

from flask import current_app

from buscador_empleos.bootstrap import Container


def get_container() -> Container:
    """Los servicios de la aplicación en curso (los puso ``create_app``)."""
    container: Container = current_app.extensions["container"]
    return container
