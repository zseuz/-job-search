"""Salarios: lectura desde texto libre y conversión de monedas a pesos colombianos."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal, NamedTuple

from buscador_empleos.domain.text import clean

Period = Literal["hour", "day", "week", "month", "year"]

#: Tasas aproximadas a pesos colombianos. Son referenciales; se pueden sobrescribir por configuración.
DEFAULT_RATES: Mapping[str, float] = {
    "COP": 1,
    "USD": 4000,
    "EUR": 4400,
    "MXN": 220,
    "PEN": 1070,
    "CLP": 4.2,
    "ARS": 3,
    "BRL": 730,
}

#: Por debajo de este monto mensual se descarta el número (ruido: bonos, auxilios, años de experiencia).
MIN_PLAUSIBLE_MONTHLY_COP = 500_000

_PERIODS_PER_MONTH: Mapping[str, float] = {"hour": 160, "day": 22, "week": 4.33, "month": 1, "year": 1 / 12}
_PERIOD_LABELS: Mapping[str, str] = {
    "hour": "hora",
    "day": "día",
    "week": "semana",
    "month": "mes",
    "year": "año",
}

_LABELLED_SALARY = re.compile(
    r"(?:salario|sueldo|remuneraci[oó]n)[^\n$\d]{0,25}[:\-]?\s*"
    r"(\$?\s*[\d.,]+(?:\s*(?:a|-|–)\s*\$?\s*[\d.,]+)?(?:\s*millones?)?)",
    re.IGNORECASE,
)
_BARE_SALARY = re.compile(r"(\$\s*[\d.,]{6,}(?:\s*(?:a|-|–)\s*\$?\s*[\d.,]{6,})?)")
_NUMBER = re.compile(r"\d[\d.,]*")
_CENTS = re.compile(r"[.,]\d{1,2}$")


class Salary(NamedTuple):
    """Salario publicado: el texto original y su mínimo en pesos al mes (``None`` si no se pudo leer)."""

    text: str
    min_cop: int | None


NO_SALARY = Salary("", None)


def parse_salary(text: str) -> Salary:
    """Busca un salario en pesos dentro de un texto libre.

    Entiende '$ 3.000.000', '$ 2.655.000,00', '$3 a $3,5 millones' y rangos
    ('$ 3.000.000 - $ 4.000.000', se usa el límite inferior). 'A convenir' no es un salario.
    """
    normalized = text.replace("\xa0", " ")
    match = _LABELLED_SALARY.search(normalized) or _BARE_SALARY.search(normalized)
    if match is None:
        return NO_SALARY

    raw = clean(match.group(1))
    in_millions = "millon" in raw.lower() or "millón" in raw.lower()
    amounts: list[int] = []
    for number in _NUMBER.findall(raw):
        if in_millions:
            try:
                amounts.append(int(float(number.replace(".", "").replace(",", ".")) * 1_000_000))
            except ValueError:
                continue
        else:
            digits = re.sub(r"[.,]", "", _CENTS.sub("", number))
            amounts.append(int(digits) if digits else 0)
    plausible = [a for a in amounts if a >= MIN_PLAUSIBLE_MONTHLY_COP]
    return Salary(raw, min(plausible) if plausible else None)


def to_cop_monthly(
    amount: float | None,
    currency: str | None = "COP",
    period: str = "month",
    rates: Mapping[str, float] | None = None,
) -> int | None:
    """Convierte un monto por hora/día/semana/mes/año a pesos colombianos al mes.

    Devuelve ``None`` si el monto está vacío o si la moneda o el periodo no se conocen.
    """
    rate = (rates or DEFAULT_RATES).get((currency or "COP").upper())
    periods = _PERIODS_PER_MONTH.get(period)
    if not amount or rate is None or periods is None:
        return None
    return int(amount * periods * rate)


def format_salary(low: float | None, high: float | None, currency: str, period: str) -> str:
    """Texto legible en la moneda original: 'USD 3.000 - 4.500 / mes'."""
    numbers = " - ".join(f"{int(n):,}".replace(",", ".") for n in (low, high) if n)
    if not numbers:
        return ""
    unit = _PERIOD_LABELS.get(period)
    return f"{currency} {numbers}" + (f" / {unit}" if unit else "")
