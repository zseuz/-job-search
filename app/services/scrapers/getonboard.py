"""Scraper de Get on Board (API pública v0; empleo tecnológico en Latinoamérica)."""
import random
import time

import requests

from app.models.extractors import format_salary, to_cop_monthly
from app.models.job import Job
from app.services.scrapers.base import JSON_HEADERS
from app.utils.text import ago_text, html_to_text

API = "https://www.getonbrd.com/api/v0/search/jobs"
MODALITY = {"no_remote": "Presencial", "hybrid": "Híbrido"}  # cualquier otro valor remoto -> "Remoto"
SECTIONS = (("projects", "Sobre el proyecto"), ("functions", "Funciones"),
            ("description", "Requisitos"), ("desirable", "Deseable"), ("benefits", "Beneficios"))


def getonboard(query, pages=2, log=print):
    jobs = []
    for page in range(1, pages + 1):
        try:
            r = requests.get(API, headers=JSON_HEADERS, timeout=20, params={
                "query": query, "per_page": 25, "page": page, "country_code": "CO",
                "expand": '["company","location_cities"]'})
            r.raise_for_status()
            body = r.json()
        except Exception as e:
            log(f"  Get on Board: fallo ({e})")
            break
        jobs += [_to_job(item) for item in body.get("data", [])]
        if page >= body.get("meta", {}).get("total_pages", 1):
            break
        time.sleep(random.uniform(0.5, 1.0))
    return jobs


def _to_job(item):
    a = item["attributes"]
    company = (a.get("company") or {}).get("data", {}).get("attributes", {}).get("name", "")
    cities = [c["attributes"]["name"] for c in (a.get("location_cities") or {}).get("data", []) if "attributes" in c]
    modality = MODALITY.get(a.get("remote_modality"), "Remoto" if a.get("remote") else "No indicado")
    parts = [f"{title}\n{html_to_text(a[key])}" for key, title in SECTIONS if a.get(key)]
    low, high = a.get("min_salary"), a.get("max_salary")
    salary = (format_salary(low, high, "USD", "month"), to_cop_monthly(low or high, "USD", "month")) if (low or high) else None
    return Job.create(
        "Get on Board", item["id"], a.get("title", ""), company,
        ", ".join(cities) or ", ".join(a.get("countries", [])), item["links"]["public_url"],
        ago_text(a["published_at"]) if a.get("published_at") else "", "\n\n".join(parts),
        tags=[a.get("category_name", "")], salary=salary, modality=modality)
