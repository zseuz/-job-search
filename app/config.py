"""Configuracion de la aplicacion."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "jobs.json"
HOST = "127.0.0.1"
PORT = 5000
DEFAULT_PAGES = 2
MAX_PAGES = 5

# Tasas aproximadas a pesos colombianos para comparar salarios de ofertas en otras monedas.
# Son referenciales: ajustalas si quieres mas precision.
FX_TO_COP = {"COP": 1, "USD": 4000, "EUR": 4400, "MXN": 220, "PEN": 1070, "CLP": 4.2, "ARS": 3, "BRL": 730}
