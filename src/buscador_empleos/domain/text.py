"""Utilidades puras de texto."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def strip_accents(text: str) -> str:
    """Quita los acentos y diéresis ('Canción' -> 'Cancion', 'año' -> 'ano')."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def clean(text: str | None) -> str:
    """Colapsa cualquier espacio en blanco (incluidos saltos de línea) en un solo espacio."""
    return _WHITESPACE.sub(" ", text or "").strip()


def clean_text(text: str | None) -> str:
    """Como :func:`clean`, pero conserva los saltos de línea para poder leer párrafos."""
    value = (text or "").replace("\r", "").replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" ?\n ?", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def slug(text: str) -> str:
    """Convierte un texto en un fragmento de URL ('Analista de Datos' -> 'analista-de-datos')."""
    return _NON_SLUG.sub("-", strip_accents(text).lower()).strip("-")
