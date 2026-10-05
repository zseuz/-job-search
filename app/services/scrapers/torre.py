"""Scraper de Torre.co (API pública de búsqueda; plataforma de origen colombiano)."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from app.models.extractors import format_salary, to_cop_monthly
from app.models.job import Job
from app.services.scrapers.base import JSON_HEADERS
from app.utils.text import ago_text, clean_text

SEARCH = "https://search.torre.co/opportunities/_search/"
DETAIL = "https://torre.ai/api/suite/opportunities/{}"
PAGE_SIZE = 20
TYPES = {"full-time-employment": "Tiempo completo", "part-time-employment": "Medio tiempo",
         "internship": "Práctica", "freelance-gigs": "Freelance"}
PERIOD = {"hourly": "hour", "daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}
SECTION_TITLES = {"responsibilities": "Responsabilidades", "requirements": "Requisitos", "qualifications": "Requisitos",
                  "benefits": "Beneficios", "additional": "Información adicional", "details": "Detalles"}


def torre(query, pages=2, log=print):
    role = {"skill/role": {"text": query, "experience": "potential-to-develop"}}
    filters = [  # en Bogotá, y remotas para Colombia
        {"and": [role, {"location": {"term": "Bogotá"}}]},
        {"and": [role, {"remote": {"term": True}}, {"location": {"term": "Colombia"}}]},
    ]
    found = {}
    for body in filters:
        for page in range(pages):
            try:
                r = requests.post(SEARCH, params={"size": PAGE_SIZE, "offset": page * PAGE_SIZE, "lang": "es"},
                                  json=body, headers=JSON_HEADERS, timeout=25)
                r.raise_for_status()
                results = r.json().get("results", [])
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 400:
                    log("  Torre: su API pública rechaza la búsqueda (400); probablemente cambió. Se omite esta fuente.")
                    return []
                log(f"  Torre: fallo ({e})")
                break
            except Exception as e:
                log(f"  Torre: fallo ({e})")
                break
            for item in results:
                found.setdefault(item["id"], item)
            if len(results) < PAGE_SIZE:
                break
            time.sleep(random.uniform(0.5, 1.0))

    def build(item):
        return _to_job(item, _description(item["id"], log))

    with ThreadPoolExecutor(2) as ex:
        return list(ex.map(build, found.values()))


def _description(oid, log):
    try:
        time.sleep(random.uniform(0.4, 0.9))
        r = requests.get(DETAIL.format(oid), headers=JSON_HEADERS, timeout=25)
        r.raise_for_status()
        sections = [f"{SECTION_TITLES.get(d.get('code'), (d.get('code') or '').capitalize())}\n{d.get('content', '')}"
                    for d in r.json().get("details", []) if d.get("content")]
        return clean_text("\n\n".join(sections))
    except Exception as e:
        log(f"  Torre: sin detalle {oid}: {e}")
        return ""


def _to_job(item, description):
    place = item.get("place") or {}
    remote = place.get("remote") or place.get("anywhere")
    if remote:
        modality = "Híbrido" if place.get("locationType") == "hybrid" else "Remoto"
    else:
        modality = "Presencial"
    comp = (item.get("compensation") or {}).get("data") or {}
    salary = None
    if comp.get("minAmount"):
        period = PERIOD.get(comp.get("periodicity"), "month")
        salary = (format_salary(comp["minAmount"], comp.get("maxAmount"), comp.get("currency", "USD"), period),
                  to_cop_monthly(comp["minAmount"], comp.get("currency", "USD"), period))
    orgs = item.get("organizations") or []
    return Job.create(
        "Torre", item["id"], item.get("objective", ""), orgs[0]["name"] if orgs else "",
        ", ".join(item.get("locations") or []) or ("Remoto" if remote else ""),
        f"https://torre.ai/post/{item['id']}-{item.get('slug', '')}".rstrip("-"),
        ago_text(item["created"]) if item.get("created") else "", description,
        tags=[TYPES.get(item.get("type"), item.get("type") or "")], salary=salary, modality=modality)
