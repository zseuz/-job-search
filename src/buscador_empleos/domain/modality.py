"""Modalidad de trabajo: remoto, híbrido o presencial."""

from __future__ import annotations

import re
from enum import Enum


class Modality(str, Enum):
    """Valores que se guardan y se muestran. Al ser ``str`` se serializan tal cual a JSON."""

    REMOTE = "Remoto"
    HYBRID = "Híbrido"
    ONSITE = "Presencial"
    UNKNOWN = "No indicado"


_HYBRID = re.compile(r"h[ií]brid|semi-?\s?presencial")
_REMOTE = re.compile(r"remot|teletrabajo|home office|trabajo en casa|desde casa|100% virtual")
_EXPLICIT_LINE = re.compile(r"modalidad[^:]{0,20}:\s*([^.]{0,60})", re.IGNORECASE)


def _classify(text: str) -> Modality | None:
    """Clasifica un fragmento; lo híbrido manda sobre lo remoto, y lo remoto sobre lo presencial."""
    lowered = text.lower()
    if _HYBRID.search(lowered):
        return Modality.HYBRID
    if _REMOTE.search(lowered):
        return Modality.REMOTE
    if "presencial" in lowered:
        return Modality.ONSITE
    return None


def detect_modality(head: str, description: str = "") -> str:
    """Deduce la modalidad de una oferta.

    Args:
        head: título, ubicación y etiquetas. Es lo más fiable, por eso se mira primero.
        description: texto libre. Primero se busca una línea 'Modalidad de trabajo: ...' y,
            si no existe, se usa el texto completo.
    """
    found = _classify(head)
    if found is None:
        line = _EXPLICIT_LINE.search(description)
        found = (_classify(line.group(1)) if line else None) or _classify(description)
    return (found or Modality.UNKNOWN).value
