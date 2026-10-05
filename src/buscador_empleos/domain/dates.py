"""Fechas de publicación: las fuentes las dan como texto relativo ('Hace 3 días')."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from buscador_empleos.domain.text import strip_accents

_AGE_PATTERN = re.compile(r"(\d+)\s*(minuto|hora|dia|semana|mes|ano)")
_DAYS_PER_UNIT = {"minuto": 1 / 1440, "hora": 1 / 24, "dia": 1, "semana": 7, "mes": 30, "ano": 365}


def parse_age_days(text: str | None) -> float | None:
    """Convierte un texto relativo en antigüedad en días.

    Entiende 'Hoy', 'Ayer', 'Hace 3 días', 'Hace 1 semana', 'Hace 12 horas',
    'Más de 30 días'. Devuelve ``None`` si el texto no trae fecha.
    """
    normalized = strip_accents((text or "").lower())
    if not normalized.strip():
        return None
    if any(word in normalized for word in ("hoy", "reciente", "ahora")):
        return 0.0
    if "ayer" in normalized:
        return 1.0
    match = _AGE_PATTERN.search(normalized)
    if match is None:
        return None
    amount, unit = int(match.group(1)), match.group(2)
    if "mas de" in normalized or "+" in normalized:  # 'Más de 30 días' es más antigua que 30
        amount += 1
    return amount * _DAYS_PER_UNIT[unit]


def ago_text(when: float | int | str | datetime) -> str:
    """Convierte una fecha en el mismo formato relativo que usan las fuentes.

    Args:
        when: epoch en segundos, texto ISO 8601 o ``datetime`` (sin zona se asume UTC).
    """
    if isinstance(when, (int, float)):
        moment = datetime.fromtimestamp(when, tz=timezone.utc)
    elif isinstance(when, str):
        moment = datetime.fromisoformat(when.replace("Z", "+00:00"))
    else:
        moment = when
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    seconds = max(0.0, (datetime.now(timezone.utc) - moment).total_seconds())
    if seconds < 3600:
        return f"Hace {max(1, int(seconds // 60))} minutos"
    if seconds < 86400:
        return f"Hace {int(seconds // 3600)} horas"
    days = int(seconds // 86400)
    if days < 90:
        return "Hace 1 día" if days == 1 else f"Hace {days} días"
    if days < 365:
        months = days // 30
        return "Hace 1 mes" if months == 1 else f"Hace {months} meses"
    years = days // 365
    return "Hace 1 año" if years == 1 else f"Hace {years} años"
