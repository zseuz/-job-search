"""Indeed Colombia (HTML detrás de Cloudflare: requiere el cliente que imita a Chrome).

La página de detalle de Indeed responde 401, así que solo se usan los datos de la tarjeta de resultados
(título, empresa, ciudad, salario y jornada). Las tecnologías salen únicamente del título.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple

from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.infrastructure.html import attr, parse_html, text_of
from buscador_empleos.infrastructure.http import ensure_ok
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

SEARCH_URL = "https://co.indeed.com/jobs"
PAGE_SIZE = 10
_BLOCKED = (403, 429)


class SourceBlockedError(RuntimeError):
    """El portal bloqueó la petición (Cloudflare o límite de consultas)."""


class _Card(NamedTuple):
    id: str
    title: str
    company: str
    location: str
    posted: str
    attributes: list[str]
    from_remote_search: bool


class IndeedSource(JobSource):
    name = "Indeed"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        jobs: list[Job] = []
        seen: set[tuple[str, str, str]] = set()
        for card in self._collect_cards(query, pages, log).values():
            key = (card.title.lower(), card.company.lower(), card.location.lower())
            if key in seen:  # la misma oferta aparece en la búsqueda de Bogotá y en la remota
                continue
            seen.add(key)
            jobs.append(self._build_job(card))
        return jobs

    def _fetch(self, params: Mapping[str, Any]) -> str:
        response = self._http.get(SEARCH_URL, params=params)
        if response.status_code in _BLOCKED:
            raise SourceBlockedError(f"bloqueado ({response.status_code})")
        return ensure_ok(response, SEARCH_URL).text

    def _collect_cards(self, query: str, pages: int, log: LogFn) -> dict[str, _Card]:
        cards: dict[str, _Card] = {}
        for location in ("Bogotá", "Remoto"):
            for page in range(pages):
                params = {"q": query, "l": location, "sort": "date", "start": page * PAGE_SIZE}
                try:
                    soup = parse_html(self._fetch(params))
                except Exception as exc:
                    log(f"  Indeed: fallo ({exc})")
                    break
                results = soup.select("div.job_seen_beacon")
                if not results:
                    break
                for result in results:
                    link = result.select_one("h3.jobTitle a, h2.jobTitle a, a.jcs-JobTitle")
                    if link is None:
                        continue
                    job_id = attr(link, "data-jk") or attr(link, "id").replace("job_", "")
                    attributes = [
                        text_of(node)
                        for node in result.select(
                            "[data-testid=attribute_snippet_testid], [class*=salary-snippet], "
                            "[class*=metadata]"
                        )
                    ]
                    cards[job_id] = _Card(
                        id=job_id,
                        title=text_of(link),
                        company=text_of(result.select_one("[data-testid=company-name]")),
                        location=text_of(result.select_one("[data-testid=text-location]")),
                        posted=text_of(result.select_one("[data-testid=myJobsStateDate], .date")),
                        attributes=attributes,
                        from_remote_search=location == "Remoto",
                    )
                self._pause(1.5, 3.0)
        return cards

    def _build_job(self, card: _Card) -> Job:
        job = Job.create(
            source=self.name,
            source_id=card.id,
            title=card.title,
            company=card.company,
            location=card.location,
            url=f"https://co.indeed.com/viewjob?jk={card.id}",
            posted=card.posted,
            tags=card.attributes,
        )
        if card.from_remote_search and job.modality == Modality.UNKNOWN.value:
            job.modality = Modality.REMOTE.value
        if job.salary_min and any("por año" in attribute for attribute in card.attributes):
            job.salary_min //= 12  # la tarjeta muestra el salario anual
        return job
