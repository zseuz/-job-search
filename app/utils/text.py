"""Utilidades de texto compartidas."""
import re


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()
                  .replace("á", "a").replace("é", "e").replace("í", "i")
                  .replace("ó", "o").replace("ú", "u").replace("ñ", "n")).strip("-")


def clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def clean_text(t):
    """Como clean(), pero conserva los saltos de linea (parrafos) para poder leer la descripcion."""
    t = (t or "").replace("\r", "").replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def html_to_text(html):
    """HTML (descripciones de ofertas) -> texto con parrafos y viñetas."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")
    for br in soup.select("br"):
        br.replace_with("\n")
    for li in soup.select("li"):
        li.insert(0, "• ")
    for block in soup.select("p, div, li, ul, ol, h1, h2, h3, h4, h5, h6, tr"):
        block.append("\n")
    return clean_text(soup.get_text(""))


def ago_text(when):
    """Fecha (epoch en segundos, ISO 8601 o datetime) -> 'Hace 3 días', el formato que usa el resto de fuentes."""
    from datetime import datetime, timezone
    if isinstance(when, (int, float)):
        dt = datetime.fromtimestamp(when, tz=timezone.utc)
    elif isinstance(when, str):
        dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
    else:
        dt = when
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = max(0, (datetime.now(timezone.utc) - dt).total_seconds())
    if secs < 3600:
        return f"Hace {max(1, int(secs // 60))} minutos"
    if secs < 86400:
        return f"Hace {int(secs // 3600)} horas"
    days = int(secs // 86400)
    if days < 90:
        return "Hace 1 día" if days == 1 else f"Hace {days} días"
    if days < 365:
        n = days // 30
        return "Hace 1 mes" if n == 1 else f"Hace {n} meses"
    n = days // 365
    return "Hace 1 año" if n == 1 else f"Hace {n} años"
