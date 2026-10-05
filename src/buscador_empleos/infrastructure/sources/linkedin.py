"""LinkedIn, mediante su API pública de empleos (sin iniciar sesión ni usar tu cuenta)."""

from __future__ import annotations

from typing import NamedTuple

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.infrastructure.html import attr, paragraphs_of, parse_html, text_of
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
PAGE_SIZE = 25


class _Card(NamedTuple):
    id: str
    title: str
    company: str
    location: str
    url: str
    posted: str
    from_remote_search: bool


class LinkedinSource(JobSource):
    name = "LinkedIn"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        cards = self._collect_cards(query, pages, log)
        return self._map_parallel(lambda card: self._build_job(card, log), cards.values())

    def _collect_cards(self, query: str, pages: int, log: LogFn) -> dict[str, _Card]:
        searches = (
            {"keywords": query, "location": "Bogotá, Colombia"},
            {"keywords": query, "location": "Colombia", "f_WT": "2"},  # f_WT=2: solo remoto
        )
        cards: dict[str, _Card] = {}
        for params in searches:
            for page in range(pages):
                try:
                    soup = parse_html(
                        self._get(SEARCH_URL, params={**params, "start": page * PAGE_SIZE}).text
                    )
                except Exception as exc:
                    log(f"  LinkedIn: fallo ({exc}). Si es 429, espera unos minutos.")
                    break
                items = soup.select("li div.base-card")
                if not items:
                    break
                for item in items:
                    job_id = attr(item, "data-entity-urn").split(":")[-1]
                    if not job_id:
                        continue
                    cards[job_id] = _Card(
                        id=job_id,
                        title=text_of(item.select_one(".base-search-card__title")),
                        company=text_of(item.select_one(".base-search-card__subtitle")),
                        location=text_of(item.select_one(".job-search-card__location")),
                        url=attr(item.select_one("a.base-card__full-link"), "href").split("?")[0],
                        posted=text_of(item.select_one("time")),
                        from_remote_search="f_WT" in params,
                    )
                self._pause(1.0, 2.0)
        return cards

    def _build_job(self, card: _Card, log: LogFn) -> Job:
        description, tags = "", []
        try:
            soup = parse_html(self._get(DETAIL_URL.format(card.id)).text)
            description = paragraphs_of(soup.select_one(".show-more-less-html__markup"))
            tags = [text_of(tag) for tag in soup.select(".description__job-criteria-text")]
            self._pause(1.0, 1.8)
        except Exception as exc:
            log(f"  LinkedIn: sin detalle {card.id}: {exc}")
        job = Job.create(
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
        if card.from_remote_search and job.modality == Modality.UNKNOWN.value:
            job.modality = Modality.REMOTE.value
        return job
