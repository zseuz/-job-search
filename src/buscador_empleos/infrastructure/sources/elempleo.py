"""elempleo.com (HTML con los datos de cada oferta embebidos como JSON)."""

from __future__ import annotations

import json
from typing import NamedTuple

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.domain.text import slug
from buscador_empleos.infrastructure.html import attr, paragraphs_of, parse_html, text_of
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

BASE = "https://www.elempleo.com"


class _Card(NamedTuple):
    id: str
    title: str
    company: str
    location: str
    url: str
    posted: str
    salary: str
    contract: str


class ElempleoSource(JobSource):
    name = "elempleo"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        cards = self._collect_cards(query, pages, log)
        jobs = self._map_parallel(lambda card: self._build_job(card, log), cards.values())
        # Fuera de Bogotá solo sirven las ofertas remotas.
        return [j for j in jobs if "bogot" in j.location.lower() or j.modality == Modality.REMOTE.value]

    def _urls(self, query: str, pages: int) -> list[str]:
        # Bogotá y todo el país (de ahí solo se conservan las remotas).
        urls = []
        for suffix in (f"bogota/trabajo-{slug(query)}", f"trabajo-{slug(query)}"):
            for page in range(1, pages + 1):
                urls.append(f"{BASE}/co/ofertas-empleo/{suffix}" + (f"?Page={page}" if page > 1 else ""))
        return urls

    def _collect_cards(self, query: str, pages: int, log: LogFn) -> dict[str, _Card]:
        cards: dict[str, _Card] = {}
        for url in self._urls(query, pages):
            try:
                soup = parse_html(self._get(url).text)
            except Exception as exc:
                log(f"  elempleo: fallo {url}: {exc}")
                continue
            for result in soup.select(".result-item"):
                area = result.select_one("[data-ga4-offerdata]")
                if area is None:
                    continue
                try:
                    meta = json.loads(attr(area, "data-ga4-offerdata"))
                except ValueError:
                    continue
                contract = ""
                for box in result.select(".small"):
                    label = box.select_one(".small-text")
                    if label is not None and "contrato" in label.get_text().lower():
                        contract = text_of(box.select_one("div"))
                cards[str(meta["id"])] = _Card(
                    id=str(meta["id"]),
                    title=meta.get("title", ""),
                    company=meta.get("company", ""),
                    location=meta.get("location", ""),
                    url=BASE + attr(area, "data-url"),
                    posted=text_of(result.select_one(".info-publish-date")),
                    salary=meta.get("salary", ""),
                    contract=contract,
                )
            self._pause(0.6, 1.2)
        return cards

    def _build_job(self, card: _Card, log: LogFn) -> Job:
        description = ""
        try:
            self._pause(0.5, 1.2)
            description = paragraphs_of(parse_html(self._get(card.url).text).select_one(".description-block"))
        except Exception as exc:
            log(f"  elempleo: sin detalle {card.url}: {exc}")
        tags = ([card.contract] if card.contract else []) + [f"Salario: {card.salary}"]
        return Job.create(
            source=self.name,
            source_id=card.id,
            title=card.title,
            company=card.company,
            location=card.location,
            url=card.url,
            posted=card.posted,
            description=description,
            tags=tags,
        )
