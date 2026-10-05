"""Línea de comandos: ``buscador-empleos`` o ``python -m buscador_empleos``."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from buscador_empleos import __version__
from buscador_empleos.settings import ConfigError, Settings
from buscador_empleos.web import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buscador-empleos",
        description="Servidor local del buscador de empleos (Bogotá y remoto).",
        epilog="Los valores por defecto salen de las variables BUSCADOR_* (ver buscador_empleos.settings).",
    )
    parser.add_argument("--host", help="dirección donde escucha (por defecto 127.0.0.1)")
    parser.add_argument("--port", type=int, help="puerto (por defecto 5000)")
    parser.add_argument("--data-file", type=Path, help="archivo JSON donde se guardan las ofertas")
    parser.add_argument("--debug", action="store_true", help="registro detallado")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("werkzeug").setLevel(logging.INFO if debug else logging.WARNING)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        overrides = {
            key: value
            for key, value in (("host", args.host), ("port", args.port), ("data_file", args.data_file))
            if value is not None
        }
        settings = replace(settings, debug=args.debug, **overrides)
    except ConfigError as exc:
        parser.error(str(exc))  # termina con código 2 y un mensaje claro

    configure_logging(settings.debug)
    app = create_app(settings)
    logging.getLogger(__name__).info("Escuchando en http://%s:%s", settings.host, settings.port)
    app.run(host=settings.host, port=settings.port, debug=False, threaded=True)
    return 0
