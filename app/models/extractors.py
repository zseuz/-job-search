"""Reglas de negocio: extraen datos estructurados del texto de una oferta."""
import re

from app.models.catalog import ROLE_RES, TECH_RE
from app.utils.text import clean


def extract_techs(text):
    return [t for t, rx in TECH_RE.items() if rx.search(text)]


def classify_roles(title):
    """Tipo de cargo segun el titulo (la descripcion es demasiado ruidosa)."""
    roles = [r for r, rx in ROLE_RES.items() if rx.search(title)]
    return roles or ["Otros"]


def _mod(t):
    t = t.lower()
    if re.search(r"h[ií]brid|semi-?\s?presencial", t):
        return "Híbrido"
    if re.search(r"remot|teletrabajo|home office|trabajo en casa|desde casa|100% virtual", t):
        return "Remoto"
    if "presencial" in t:
        return "Presencial"
    return ""


def detect_modality(head, description=""):
    """head = titulo/ubicacion/etiquetas (fiable); description = texto libre (menos fiable)."""
    m = _mod(head)
    if m:
        return m
    exp = re.search(r"modalidad[^:]{0,20}:\s*([^.]{0,60})", description, re.I)
    if exp and _mod(exp.group(1)):
        return _mod(exp.group(1))
    return _mod(description) or "No indicado"


def parse_salary(text):
    """Devuelve (texto, minimo_COP_mensual o None). Entiende '$ 3.000.000', '3 millones', 'A convenir'."""
    t = text.replace("\xa0", " ")
    m = re.search(r"(?:salario|sueldo|remuneraci[oó]n)[^\n$\d]{0,25}[:\-]?\s*(\$?\s*[\d.,]+(?:\s*(?:a|-|–)\s*\$?\s*[\d.,]+)?(?:\s*millones?)?)",
                  t, re.I)
    if not m:
        m = re.search(r"(\$\s*[\d.,]{6,}(?:\s*(?:a|-|–)\s*\$?\s*[\d.,]{6,})?)", t)
    if not m:
        return ("", None)
    raw = clean(m.group(1))
    nums = []
    millions = "millon" in raw.lower() or "millón" in raw.lower()
    for n in re.findall(r"\d[\d.,]*", raw):
        if millions:
            try:
                v = int(float(n.replace(".", "").replace(",", ".")) * 1_000_000)
            except ValueError:
                continue
        else:
            digits = re.sub(r"[.,]\d{1,2}$", "", n)  # quita centavos (",00")
            digits = re.sub(r"[.,]", "", digits)
            v = int(digits) if digits else 0
        nums.append(v)
    nums = [n for n in nums if n >= 500_000]
    return (raw, min(nums) if nums else None)


def parse_age_days(text):
    """'Hace 3 días' / 'Hace 1 semana' / 'Ayer' / 'Hoy' -> antigüedad en días (None si no hay fecha)."""
    t = (text or "").lower()
    t = t.replace("í", "i").replace("á", "a").replace("ñ", "n")
    if not t.strip():
        return None
    if "hoy" in t or "reciente" in t or "ahora" in t:
        return 0.0
    if "ayer" in t:
        return 1.0
    m = re.search(r"(\d+)\s*(minuto|hora|dia|semana|mes|ano)", t)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    if "mas de" in t or "+" in t:  # "Más de 30 días": es mas antigua que eso
        n += 1
    return n * {"minuto": 1 / 1440, "hora": 1 / 24, "dia": 1, "semana": 7, "mes": 30, "ano": 365}[unit]


# ---- salarios en otras monedas -----------------------------------------------------------
_HOURS_PER_MONTH = 160
_PERIOD_TO_MONTH = {"hour": _HOURS_PER_MONTH, "day": 22, "week": 4.33, "month": 1, "year": 1 / 12}


def to_cop_monthly(amount, currency="COP", period="month"):
    """Convierte un monto (por hora/dia/semana/mes/año) a pesos colombianos mensuales; None si no se puede."""
    from app.config import FX_TO_COP
    rate = FX_TO_COP.get((currency or "COP").upper())
    factor = _PERIOD_TO_MONTH.get(period)
    if not amount or rate is None or factor is None:
        return None
    return int(amount * factor * rate)


def format_salary(low, high, currency, period):
    """'USD 3.000 - 4.500 / mes' para mostrar el salario en su moneda original."""
    unit = {"hour": "hora", "day": "día", "week": "semana", "month": "mes", "year": "año"}.get(period, "")
    nums = " - ".join(f"{int(n):,}".replace(",", ".") for n in (low, high) if n)
    return f"{currency} {nums}" + (f" / {unit}" if unit else "") if nums else ""


def title_matches_query(title, query, extra=""):
    """Para fuentes en ingles que no filtran por texto: ¿el titulo corresponde al cargo buscado?

    Reutiliza la clasificacion de cargos (ej. 'desarrollador de software' -> Desarrollador, que
    tambien reconoce 'Software Engineer', 'Backend Developer'...). Si la busqueda no es de un
    tipo conocido, exige que aparezcan sus palabras clave.
    """
    wanted = set(classify_roles(query)) - {"Otros"}
    if wanted:
        return bool(wanted & set(classify_roles(title)))
    words = [w for w in re.findall(r"\w{4,}", query.lower())]
    hay = f"{title} {extra}".lower()
    return bool(words) and all(w in hay for w in words)


# ---- ampliar la busqueda con cargos relacionados -----------------------------------------
RELATED_QUERIES = {
    "Analista de datos": ["data analyst", "analista de bi", "analista de inteligencia de negocios",
                          "ingeniero de datos", "científico de datos"],
    "Desarrollador": ["programador", "ingeniero de software", "desarrollador backend",
                      "desarrollador frontend", "desarrollador full stack"],
}


def expand_queries(queries):
    """Agrega cargos relacionados a cada busqueda ('desarrollador de software' -> + 'programador', ...).

    Conserva el orden, sin repetidos; las busquedas de un tipo desconocido se dejan tal cual.
    """
    out, seen = [], set()
    for q in queries:
        extra = [r for role in classify_roles(q) for r in RELATED_QUERIES.get(role, [])]
        for term in [q, *extra]:
            if term.lower() not in seen:
                seen.add(term.lower())
                out.append(term)
    return out
