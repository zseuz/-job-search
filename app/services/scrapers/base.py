"""Cliente HTTP comun a los scrapers."""
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}


def get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=20, **kw)
    r.raise_for_status()
    return r


JSON_HEADERS = {**HEADERS, "Accept": "application/json"}
_OPEN_TO_COLOMBIA = ("colombia", "latam", "latin america", "latinoam", "south america", "americas",
                     "worldwide", "anywhere", "global", "world", "everywhere")


def open_to_colombia(restrictions):
    """Ofertas remotas globales: ¿puede aplicar alguien en Colombia? (sin restricciones, o las incluye)."""
    if not restrictions:
        return True
    text = " ".join(restrictions if isinstance(restrictions, (list, tuple)) else [str(restrictions)]).lower()
    return any(k in text for k in _OPEN_TO_COLOMBIA)
