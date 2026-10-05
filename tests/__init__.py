"""Pruebas. Los mensajes de ``logging`` de la aplicación no deben ensuciar la salida de las pruebas."""

import logging

logging.getLogger("buscador_empleos").addHandler(logging.NullHandler())
