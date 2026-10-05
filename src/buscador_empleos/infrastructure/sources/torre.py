"""Torre.co (API pública de búsqueda; plataforma de origen colombiano).

Nota: a principios de octubre de 2026 la API de búsqueda empezó a responder 400 a cualquier consulta.
Si eso ocurre, la fuente avisa una sola vez y se omite, sin afectar a las demás.
"""

from __future__ import annotations

from typing import Any

from buscador_empleos.domain.dates import ago_text
from buscador_empleos.domain.job import Job
from buscador_empleos.domain.modality import Modality
from buscador_empleos.domain.salary import Salary, format_salary, to_cop_monthly
from buscador_empleos.domain.text import clean_text
from buscador_empleos.infrastructure.http import JSON_HEADERS, HttpStatusError
from buscador_empleos.infrastructure.sources.base import JobSource, LogFn, ignore_log

SEARCH_URL = "https://search.torre.co/opportunities/_search/"
DETAIL_URL = "https://torre.ai/api/suite/opportunities/{}"
PAGE_SIZE = 20
_TYPES = {
    "full-time-employment": "Tiempo completo",
    "part-time-employment": "Medio tiempo",
    "internship": "Práctica",
    "freelance-gigs": "Freelance",
}
_PERIODS = {"hourly": "hour", "daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}
_SECTION_TITLES = {
    "responsibilities": "Responsabilidades",
    "requirements": "Requisitos",
    "qualifications": "Requisitos",
    "benefits": "Beneficios",
    "additional": "Información adicional",
    "details": "Detalles",
}


def _section_title(code: str | None) -> str:
    return _SECTION_TITLES.get(code or "", (code or "").capitalize())


class TorreSource(JobSource):
    name = "Torre"

    def search(self, query: str, pages: int, log: LogFn = ignore_log) -> list[Job]:
        found = self._find_offers(query, pages, log)
        if found is None:
            return []
        return self._map_parallel(
            lambda item: self._to_job(item, self._description(item["id"], log)), found.values()
        )

    def _find_offers(self, query: str, pages: int, log: LogFn) -> dict[str, dict[str, Any]] | None:
        """Ofertas de la búsqueda, o ``None`` si la API rechaza la consulta (cambió)."""
        role = {"skill/role": {"text": query, "experience": "potential-to-develop"}}
        filters = (  # en Bogotá, y remotas para Colombia
            {"and": [role, {"location": {"term": "Bogotá"}}]},
            {"and": [role, {"remote": {"term": True}}, {"location": {"term": "Colombia"}}]},
        )
        found: dict[str, dict[str, Any]] = {}
        for body in filters:
            for page in range(pages):
                try:
                    results = (
                        self._post_json(
                            SEARCH_URL,
                            body,
                            headers=JSON_HEADERS,
                            params={"size": PAGE_SIZE, "offset": page * PAGE_SIZE, "lang": "es"},
                        )
                        .json()
                        .get("results", [])
                    )
                except HttpStatusError as exc:
                    if exc.status_code == 400:
                        log(
                            "  Torre: su API pública rechaza la búsqueda (400); probablemente cambió. "
                            "Se omite esta fuente."
                        )
                        return None
                    log(f"  Torre: fallo ({exc})")
                    break
                except Exception as exc:
                    log(f"  Torre: fallo ({exc})")
                    break
                for item in results:
                    found.setdefault(item["id"], item)
                if len(results) < PAGE_SIZE:
                    break
                self._pause(0.5, 1.0)
        return found

    def _description(self, offer_id: str, log: LogFn) -> str:
        try:
            self._pause(0.4, 0.9)
            details = self._get(DETAIL_URL.format(offer_id), headers=JSON_HEADERS).json().get("details", [])
        except Exception as exc:
            log(f"  Torre: sin detalle {offer_id}: {exc}")
            return ""
        sections = [
            f"{_section_title(d.get('code'))}\n{d.get('content', '')}" for d in details if d.get("content")
        ]
        return clean_text("\n\n".join(sections))

    def _to_job(self, item: dict[str, Any], description: str) -> Job:
        place = item.get("place") or {}
        remote = bool(place.get("remote") or place.get("anywhere"))
        if not remote:
            modality = Modality.ONSITE.value
        elif place.get("locationType") == "hybrid":
            modality = Modality.HYBRID.value
        else:
            modality = Modality.REMOTE.value

        compensation = (item.get("compensation") or {}).get("data") or {}
        salary = None
        if compensation.get("minAmount"):
            period = _PERIODS.get(str(compensation.get("periodicity")), "month")
            currency = compensation.get("currency", "USD")
            salary = Salary(
                format_salary(compensation["minAmount"], compensation.get("maxAmount"), currency, period),
                to_cop_monthly(compensation["minAmount"], currency, period, self._rates),
            )
        organizations = item.get("organizations") or []
        offer_type = str(item.get("type") or "")
        return Job.create(
            source=self.name,
            source_id=item["id"],
            title=item.get("objective", ""),
            company=organizations[0]["name"] if organizations else "",
            location=", ".join(item.get("locations") or []) or ("Remoto" if remote else ""),
            url=f"https://torre.ai/post/{item['id']}-{item.get('slug', '')}".rstrip("-"),
            posted=ago_text(item["created"]) if item.get("created") else "",
            description=description,
            tags=[_TYPES.get(offer_type, offer_type)],
            salary=salary,
            modality=modality,
        )
