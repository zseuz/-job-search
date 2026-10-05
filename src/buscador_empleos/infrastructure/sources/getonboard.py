"""Get on Board (API pública v0; empleo tecnológico en Latinoamérica)."""

from __future__ import annotations

from typing import Any

from buscador_empleos.domain.dates import ago_text
from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.domain.salary import Salary, format_salary, to_cop_monthly
from buscador_empleos.infrastructure.html import html_to_text
from buscador_empleos.infrastructure.http import JSON_HEADERS
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

API_URL = "https://www.getonbrd.com/api/v0/search/jobs"
PAGE_SIZE = 25
_MODALITIES = {"no_remote": Modality.ONSITE.value, "hybrid": Modality.HYBRID.value}
# (campo de la API, título de la sección en la descripción que armamos)
_SECTIONS = (
    ("projects", "Sobre el proyecto"),
    ("functions", "Funciones"),
    ("description", "Requisitos"),
    ("desirable", "Deseable"),
    ("benefits", "Beneficios"),
)


class GetOnBoardSource(JobSource):
    name = "Get on Board"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        jobs: list[Job] = []
        for page in range(1, pages + 1):
            try:
                body = self._get(
                    API_URL,
                    headers=JSON_HEADERS,
                    params={
                        "query": query,
                        "per_page": PAGE_SIZE,
                        "page": page,
                        "country_code": "CO",
                        "expand": '["company","location_cities"]',
                    },
                ).json()
            except Exception as exc:
                log(f"  Get on Board: fallo ({exc})")
                break
            jobs += [self._to_job(item) for item in body.get("data", [])]
            if page >= body.get("meta", {}).get("total_pages", 1):
                break
            self._pause(0.5, 1.0)
        return jobs

    def _to_job(self, item: dict[str, Any]) -> Job:
        attrs = item["attributes"]
        company = (attrs.get("company") or {}).get("data", {}).get("attributes", {}).get("name", "")
        cities = [
            city["attributes"]["name"]
            for city in (attrs.get("location_cities") or {}).get("data", [])
            if "attributes" in city
        ]
        modality = _MODALITIES.get(
            attrs.get("remote_modality"),
            Modality.REMOTE.value if attrs.get("remote") else Modality.UNKNOWN.value,
        )
        sections = [f"{title}\n{html_to_text(attrs[key])}" for key, title in _SECTIONS if attrs.get(key)]
        low, high = attrs.get("min_salary"), attrs.get("max_salary")
        salary = (
            Salary(
                format_salary(low, high, "USD", "month"),
                to_cop_monthly(low or high, "USD", "month", self._rates),
            )
            if (low or high)
            else None
        )
        return Job.create(
            source=self.name,
            source_id=item["id"],
            title=attrs.get("title", ""),
            company=company,
            location=", ".join(cities) or ", ".join(attrs.get("countries", [])),
            url=item["links"]["public_url"],
            posted=ago_text(attrs["published_at"]) if attrs.get("published_at") else "",
            description="\n\n".join(sections),
            tags=[attrs.get("category_name", "")],
            salary=salary,
            modality=modality,
        )
