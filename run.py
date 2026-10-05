"""Atajo para arrancar sin instalar el paquete:  py run.py

Equivale a ``python -m buscador_empleos`` (o al comando ``buscador-empleos`` si instalaste el
proyecto con ``pip install -e .``). Acepta las mismas opciones, p. ej. ``py run.py --port 8000``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from buscador_empleos.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
