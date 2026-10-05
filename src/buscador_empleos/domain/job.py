"""Entidad principal del dominio: una oferta de empleo."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Any

from buscador_empleos.domain.catalog import CONTRACT_PATTERN
from buscador_empleos.domain.classification import classify_roles, extract_techs
from buscador_empleos.domain.dates import parse_age_days
from buscador_empleos.domain.modality import Modality, detect_modality
from buscador_empleos.domain.salary import Salary, parse_salary
from buscador_empleos.domain.text import clean

MAX_DESCRIPTION = 6000
#: Menos caracteres que esto son solo metadatos (jornada, salario), no una descripción real.
MIN_DESCRIPTION = 150


@dataclass(slots=True)
class Job:
    """Una oferta ya normalizada, sin importar de qué portal viene."""

    id: str  # '<fuente>:<id en la fuente>', único entre fuentes
    source: str
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    posted: str = ""  # texto original de la fuente ('Hace 3 días')
    age_days: float | None = None  # antigüedad que decía la fuente al leerla
    scraped_at: str = ""  # cuándo se leyó (ISO 8601, hora local)
    modality: str = Modality.UNKNOWN.value
    salary_text: str = ""
    salary_min: int | None = None  # pesos colombianos al mes
    contract: str = ""
    techs: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    description: str = ""
    query: str = ""  # búsqueda que la encontró

    # ---------------------------------------------------------------- construcción
    @classmethod
    def create(
        cls,
        *,
        source: str,
        source_id: str,
        title: str,
        company: str = "",
        location: str = "",
        url: str = "",
        posted: str = "",
        description: str = "",
        tags: Iterable[str] = (),
        salary: Salary | tuple[str, int | None] | None = None,
        modality: str | None = None,
        now: datetime | None = None,
    ) -> Job:
        """Crea una oferta a partir de los datos crudos de una fuente y deduce el resto.

        Args:
            tags: etiquetas de la oferta (contrato, jornada...). También se usan para detectar
                el salario, la modalidad y el tipo de contrato.
            salary: ``(texto, mínimo en COP/mes)`` cuando la fuente ya lo trae estructurado.
            modality: cuando la fuente ya la trae estructurada.
            now: reloj inyectable; por defecto la hora actual.
        """
        tag_list = list(tags)
        searchable = f"{title}\n{description}\n{' '.join(tag_list)}"
        salary_text, salary_min = salary if salary is not None else parse_salary(searchable)
        job = cls(
            id=f"{source}:{source_id}",
            source=source,
            title=clean(title),
            company=clean(company),
            location=clean(location),
            url=url,
            posted=clean(posted),
            age_days=parse_age_days(posted),
            scraped_at=(now or datetime.now()).isoformat(timespec="minutes"),
            modality=modality or detect_modality(f"{title} {location} {' '.join(tag_list)}", description),
            salary_text=salary_text,
            salary_min=salary_min,
            contract=next((tag for tag in tag_list if CONTRACT_PATTERN.search(tag)), ""),
            description=description[:MAX_DESCRIPTION],
        )
        job.refresh_derived()
        return job

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, refresh: bool = True) -> Job:
        """Reconstruye una oferta guardada; los campos desconocidos se ignoran."""
        known = {f.name for f in fields(cls)}
        job = cls(**{key: value for key, value in data.items() if key in known})
        if refresh:
            job.refresh_derived()
        return job

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ---------------------------------------------------------------- comportamiento
    def refresh_derived(self) -> None:
        """Recalcula tecnologías y tipo de cargo (dependen del catálogo, que puede cambiar)."""
        self.techs = extract_techs(f"{self.title}\n{self.description}")
        self.roles = classify_roles(self.title)

    def has_description(self) -> bool:
        return len(self.description.strip()) >= MIN_DESCRIPTION

    def days_ago(self, *, fallback_seen: str | None = None, now: datetime | None = None) -> float | None:
        """Días desde la publicación: lo que dice la fuente más el tiempo desde que se leyó.

        Devuelve ``None`` si la fuente no trae fecha.
        """
        age = parse_age_days(self.posted)
        if age is None:
            return None
        current = now or datetime.now()
        seen = datetime.fromisoformat(self.scraped_at or fallback_seen or current.isoformat())
        return round(max(0.0, (current - seen).total_seconds() / 86400) + age, 2)
