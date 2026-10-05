"""Scraper de Hireline (empleo tecnológico; trae pocas ofertas por página y no filtra por texto)."""
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from curl_cffi import requests as cr

from app.models.extractors import format_salary, title_matches_query, to_cop_monthly
from app.models.job import Job
from app.services.scrapers.base import open_to_colombia
from app.utils.text import ago_text, clean, html_to_text, slug

BASE = "https://hireline.io"
UNIT = {"HOUR": "hour", "DAY": "day", "WEEK": "week", "MONTH": "month", "YEAR": "year"}


def _fetch(url):
    r = cr.get(url, impersonate="chrome", timeout=25)
    r.raise_for_status()
    return r.text


def hireline(query, pages=1, log=print):
    try:
        soup = BeautifulSoup(_fetch(f"{BASE}/co/empleos-de-{slug(query)}"), "html.parser")
    except Exception as e:
        log(f"  Hireline: fallo ({e})")
        return []
    cards = {}
    for a in soup.select("a.hl-vacancy-card"):
        title_el = a.select_one(".vacancy-title")
        loc = clean(a.select_one(".vacancy-location").get_text()) if a.select_one(".vacancy-location") else ""
        title = clean(title_el.get_text()) if title_el else ""
        # la pagina muestra los resultados generales cuando la busqueda no existe: filtrar aqui
        if not title or not title_matches_query(title, query):
            continue
        if "bogot" not in loc.lower() and not ("remot" in loc.lower() and open_to_colombia(loc)):
            continue
        title, _, company = title.rpartition(" en ") if " en " in title else (title, "", "")
        updated = a.select_one(".updated-text")
        cards[a["href"]] = (a["href"], title, company, loc, clean(updated.get_text()) if updated else "")
    with ThreadPoolExecutor(2) as ex:
        return list(ex.map(lambda c: _detail(c, log), cards.values()))


def _detail(card, log):
    url, title, company, loc, posted = card
    description, salary = "", None
    try:
        time.sleep(random.uniform(0.5, 1.2))
        soup = BeautifulSoup(_fetch(url), "html.parser")
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                ld = json.loads(tag.string or "")
            except ValueError:
                continue
            if isinstance(ld, dict) and ld.get("@type") == "JobPosting":
                description = html_to_text(ld.get("description", ""))
                if ld.get("datePosted"):
                    posted = ago_text(ld["datePosted"] + "T00:00:00+00:00")
                money = ld.get("baseSalary") or {}
                value = money.get("value") or {}
                low, high = value.get("minValue"), value.get("maxValue")
                if low:
                    period = UNIT.get(value.get("unitText", "MONTH"), "month")
                    low, high = float(low), float(high or 0)
                    salary = (format_salary(low, high, money.get("currency", "USD"), period),
                              to_cop_monthly(low, money.get("currency", "USD"), period))
    except Exception as e:
        log(f"  Hireline: sin detalle {url}: {e}")
    remote = "/remoto/" in url or "remot" in loc.lower()
    return Job.create("Hireline", re.search(r"/(\d+)$", url).group(1) if re.search(r"/(\d+)$", url) else url,
                      title, company, loc, url, posted, description, salary=salary,
                      modality="Remoto" if remote else None)
