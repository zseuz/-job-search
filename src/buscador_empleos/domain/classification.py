"""Clasificación de ofertas: tecnologías mencionadas, tipo de cargo y búsquedas relacionadas."""

from __future__ import annotations

import re
from collections.abc import Iterable

from buscador_empleos.domain.catalog import (
    RELATED_QUERIES,
    ROLE_OTHER,
    ROLE_PATTERNS,
    TECH_PATTERNS,
)


def extract_techs(text: str) -> list[str]:
    """Tecnologías del catálogo que se mencionan en ``text``, en el orden del catálogo."""
    return [tech for tech, pattern in TECH_PATTERNS.items() if pattern.search(text)]


def classify_roles(title: str) -> list[str]:
    """Tipos de cargo según el **título** (la descripción tiene demasiado ruido).

    Un título puede ser de varios tipos ('Data Developer'); si no encaja en ninguno es ``Otros``.
    """
    roles = [role for role, pattern in ROLE_PATTERNS.items() if pattern.search(title)]
    return roles or [ROLE_OTHER]


def title_matches_query(title: str, query: str, extra: str = "") -> bool:
    """¿El título corresponde al cargo buscado? Sirve para fuentes que no filtran por texto.

    Si la búsqueda es de un tipo conocido (por ejemplo 'desarrollador de software') se compara el tipo
    de cargo, así 'Software Engineer' también cuenta. Si no, deben aparecer todas sus palabras clave.
    """
    wanted = set(classify_roles(query)) - {ROLE_OTHER}
    if wanted:
        return bool(wanted & set(classify_roles(title)))
    words = re.findall(r"\w{4,}", query.lower())
    haystack = f"{title} {extra}".lower()
    return bool(words) and all(word in haystack for word in words)


def expand_queries(queries: Iterable[str]) -> list[str]:
    """Agrega los cargos relacionados de cada búsqueda, sin repetir y conservando el orden."""
    expanded: list[str] = []
    seen: set[str] = set()
    for query in queries:
        related = [term for role in classify_roles(query) for term in RELATED_QUERIES.get(role, ())]
        for term in (query, *related):
            if term.lower() not in seen:
                seen.add(term.lower())
                expanded.append(term)
    return expanded
