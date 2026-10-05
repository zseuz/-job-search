"""Hireline (HTML con datos estructurados JSON-LD).

La página trae pocas ofertas y, cuando la búsqueda no existe, muestra los resultados generales:
por eso se filtra por cargo y ubicación aquí.
"""

from __future__ import annotations

import json
import re
from typing import Any, NamedTuple

from buscador_empleos.domain.classification import title_matches_query
from buscador_empleos.domain.dates import ago_text
from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.domain.salary import Salary, format_salary, to_cop_monthly
from buscador_empleos.domain.text import slug
from buscador_empleos.infrastructure.html import attr, html_to_text, parse_html, text_of
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log, is_open_to_colombia

BASE = "https://hireline.io"
_UNITS = {"HOUR": "hour", "DAY": "day", "WEEK": "week", "MONTH": "month", "YEAR": "year"}
_NUMERIC_ID = re.compile(r"/(\d+)$")


class _Card(NamedTuple):
    url: str
    title: str
    company: str
    location: str
    posted: str


class HirelineSource(JobSource):
    name = "Hireline"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        try:
            soup = parse_html(self._get(f"{BASE}/co/empleos-de-{slug(query)}").text)
        except Exception as exc:
            log(f"  Hireline: fallo ({exc})")
            return []
        cards: dict[str, _Card] = {}
        for link in soup.select("a.hl-vacancy-card"):
            title = text_of(link.select_one(".vacancy-title"))
            location = text_of(link.select_one(".vacancy-location"))
            if not title or not title_matches_query(title, query):
                continue
            if not self._is_reachable(location):
                continue
            title, company = self._split_company(title)
            href = attr(link, "href")
            cards[href] = _Card(href, title, company, location, text_of(link.select_one(".updated-text")))
        return self._map_parallel(lambda card: self._build_job(card, log), cards.values())

    @staticmethod
    def _is_reachable(location: str) -> bool:
        """En Bogotá, o remoto abierto a Colombia."""
        lowered = location.lower()
        return "bogot" in lowered or ("remot" in lowered and is_open_to_colombia(location))

    @staticmethod
    def _split_company(title: str) -> tuple[str, str]:
        """'Desarrollador Full Stack en Ventus' -> ('Desarrollador Full Stack', 'Ventus')."""
        if " en " not in title:
            return title, ""
        role, _, company = title.rpartition(" en ")
        return role, company

    def _build_job(self, card: _Card, log: LogFn) -> Job:
        description, salary, posted = "", None, card.posted
        try:
            self._pause(0.5, 1.2)
            posting = self._read_job_posting(self._get(card.url).text)
            if posting is not None:
                description = html_to_text(posting.get("description", ""))
                if posting.get("datePosted"):
                    posted = ago_text(posting["datePosted"] + "T00:00:00+00:00")
                salary = self._salary_of(posting)
        except Exception as exc:
            log(f"  Hireline: sin detalle {card.url}: {exc}")
        remote = "/remoto/" in card.url or "remot" in card.location.lower()
        match = _NUMERIC_ID.search(card.url)
        return Job.create(
            source=self.name,
            source_id=match.group(1) if match else card.url,
            title=card.title,
            company=card.company,
            location=card.location,
            url=card.url,
            posted=posted,
            description=description,
            salary=salary,
            modality=Modality.REMOTE.value if remote else None,
        )

    @staticmethod
    def _read_job_posting(markup: str) -> dict[str, Any] | None:
        """Datos estructurados (schema.org/JobPosting) de la página de detalle."""
        for script in parse_html(markup).select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
        return None

    def _salary_of(self, posting: dict[str, Any]) -> Salary | None:
        money = posting.get("baseSalary") or {}
        value = money.get("value") or {}
        low, high = value.get("minValue"), value.get("maxValue")
        if not low:
            return None
        period = _UNITS.get(value.get("unitText", "MONTH"), "month")
        currency = money.get("currency", "USD")
        low, high = float(low), float(high or 0)
        return Salary(
            format_salary(low, high, currency, period),
            to_cop_monthly(low, currency, period, self._rates),
        )
