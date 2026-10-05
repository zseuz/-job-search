"""Modelo de dominio: una oferta de empleo."""
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Optional

from app.models.extractors import (
    classify_roles, detect_modality, extract_techs, parse_age_days, parse_salary,
)
from app.utils.text import clean

CONTRACT_HINT = r"t[eé]rmino|indefinid|fijo|obra|prestaci|aprendiz|pr[aá]ctic|temporal|freelance"
MAX_DESCRIPTION = 6000
MIN_DESCRIPTION = 150   # menos que esto es solo metadatos (p. ej. jornada y salario de Indeed), no una descripcion


@dataclass
class Job:
    id: str
    source: str
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    posted: str = ""                      # texto original de la fuente ("Hace 3 días")
    age_days: Optional[float] = None      # antigüedad al momento de leerla
    scraped_at: str = ""                  # cuándo se leyó (ISO)
    modality: str = "No indicado"
    salary_text: str = ""
    salary_min: Optional[int] = None
    contract: str = ""
    techs: list = field(default_factory=list)
    roles: list = field(default_factory=list)
    description: str = ""
    query: str = ""                       # búsqueda que la encontró

    # ------------------------------------------------------------ construcción
    @classmethod
    def create(cls, source, jid, title, company, location, url, posted, description="", tags=None,
               salary=None, modality=None):
        """Crea una oferta a partir de los datos crudos de una fuente, derivando el resto.

        `salary` = (texto, mínimo en COP/mes) y `modality` se pasan cuando la fuente ya los trae
        estructurados; si no, se deducen del texto.
        """
        import re
        tags = tags or []
        salary_text, salary_min = salary or parse_salary(f"{title}\n{description}\n{' '.join(tags)}")
        job = cls(
            id=f"{source}:{jid}", source=source, title=clean(title), company=clean(company),
            location=clean(location), url=url, posted=clean(posted),
            age_days=parse_age_days(posted), scraped_at=datetime.now().isoformat(timespec="minutes"),
            modality=modality or detect_modality(f"{title} {location} {' '.join(tags)}", description),
            salary_text=salary_text, salary_min=salary_min,
            contract=next((t for t in tags if re.search(CONTRACT_HINT, t, re.I)), ""),
            description=description[:MAX_DESCRIPTION],
        )
        job.refresh_derived()
        return job

    @classmethod
    def from_dict(cls, data: dict, refresh: bool = True) -> "Job":
        known = {f.name for f in fields(cls)}
        job = cls(**{k: v for k, v in data.items() if k in known})
        if refresh:
            job.refresh_derived()
        return job

    # ------------------------------------------------------------ comportamiento
    def refresh_derived(self) -> None:
        """Recalcula lo que depende de las listas del catálogo (por si se ampliaron)."""
        self.techs = extract_techs(f"{self.title}\n{self.description}")
        self.roles = classify_roles(self.title)

    def has_description(self) -> bool:
        return len(self.description.strip()) >= MIN_DESCRIPTION

    def days_ago(self, fallback_seen: Optional[str] = None, now: Optional[datetime] = None) -> Optional[float]:
        """Días desde la publicación: tiempo desde que se leyó + antigüedad que decía entonces."""
        age = parse_age_days(self.posted)
        if age is None:
            return None
        now = now or datetime.now()
        seen = datetime.fromisoformat(self.scraped_at or fallback_seen or now.isoformat())
        return round(max(0.0, (now - seen).total_seconds() / 86400) + age, 2)

    def to_dict(self) -> dict:
        return asdict(self)
