"""Computrabajo Colombia (HTML)."""

from __future__ import annotations

from typing import NamedTuple

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.text import slug
from buscador_empleos.infrastructure.html import attr, paragraphs_of, parse_html, text_of
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

BASE = "https://co.computrabajo.com"


class _Card(NamedTuple):
    id: str
    title: str
    company: str
    location: str
    url: str
    posted: str


class ComputrabajoSource(JobSource):
    name = "Computrabajo"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        cards = self._collect_cards(query, pages, log)
        return self._map_parallel(lambda card: self._build_job(card, log), cards.values())

    def _urls(self, query: str, pages: int) -> list[str]:
        urls = []
        for suffix in (f"trabajo-de-{slug(query)}-en-bogota-dc", f"trabajo-de-{slug(query)}-remoto"):
            for page in range(1, pages + 1):
                urls.append(f"{BASE}/{suffix}" + (f"?p={page}" if page > 1 else ""))
        return urls

    def _collect_cards(self, query: str, pages: int, log: LogFn) -> dict[str, _Card]:
        cards: dict[str, _Card] = {}
        for url in self._urls(query, pages):
            try:
                soup = parse_html(self._get(url).text)
            except Exception as exc:  # una página caída no debe tumbar la búsqueda
                log(f"  Computrabajo: fallo {url}: {exc}")
                continue
            for article in soup.select("article.box_offer"):
                link = article.select_one("h2 a")
                if link is None:
                    continue
                href = attr(link, "href")
                job_id = attr(article, "data-id") or href
                company = article.select_one("a[offer-grid-article-company-url]") or article.select_one("p a")
                cards[job_id] = _Card(
                    id=job_id,
                    title=text_of(link, ""),
                    company=text_of(company),
                    # el primer <p> con esas clases es el de la empresa y la calificación: se excluye
                    location=text_of(article.select_one("p.fs16.fc_base.mt5:not(.dFlex) span.mr10")),
                    url=BASE + href.split("#")[0],
                    posted=text_of(article.select_one("p.fs13")),
                )
            self._pause(0.6, 1.2)
        return cards

    def _build_job(self, card: _Card, log: LogFn) -> Job:
        def create(description: str = "", tags: list[str] | None = None) -> Job:
            return Job.create(
                source=self.name,
                source_id=card.id,
                title=card.title,
                company=card.company,
                location=card.location,
                url=card.url,
                posted=card.posted,
                description=description,
                tags=tags or [],
            )

        try:
            self._pause(0.5, 1.2)
            box = parse_html(self._get(card.url).text).select_one("div[div-link=oferta]")
            if box is None:
                return create()
            tags = [text_of(tag) for tag in box.select("span.tag")]
            # El salario, el contrato y la jornada vienen como etiquetas: no se repiten en el texto.
            for element in box.select("h2, span.tag"):
                element.decompose()
            return create(paragraphs_of(box), tags)
        except Exception as exc:
            log(f"  Computrabajo: sin detalle {card.url}: {exc}")
            return create()
