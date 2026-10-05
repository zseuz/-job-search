"""Scraper de LinkedIn usando su API publica de empleos (sin iniciar sesion)."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from app.services.scrapers.base import get
from app.models.job import Job
from app.utils.text import clean, clean_text, slug


def linkedin(query, pages=2, log=print):
    api = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    searches = [
        {"keywords": query, "location": "Bogotá, Colombia"},
        {"keywords": query, "location": "Colombia", "f_WT": "2"},  # solo remoto
    ]
    cards = {}
    for params in searches:
        for p in range(pages):
            try:
                soup = BeautifulSoup(get(api, params={**params, "start": p * 25}).text, "html.parser")
            except Exception as e:
                log(f"  LinkedIn: fallo ({e}). Si es 429, espera unos minutos.")
                break
            items = soup.select("li div.base-card")
            if not items:
                break
            for c in items:
                urn = c.get("data-entity-urn", "")
                jid = urn.split(":")[-1]
                if not jid:
                    continue
                t = c.select_one(".base-search-card__title")
                co = c.select_one(".base-search-card__subtitle")
                lo = c.select_one(".job-search-card__location")
                dt = c.select_one("time")
                a = c.select_one("a.base-card__full-link")
                cards[jid] = (jid, t.get_text() if t else "", co.get_text() if co else "",
                              lo.get_text() if lo else "", (a["href"].split("?")[0] if a else ""),
                              dt.get_text() if dt else "", params.get("f_WT") == "2")
            time.sleep(random.uniform(1.0, 2.0))

    def detail(c):
        jid, title, comp, loc, url, posted, remote_search = c
        desc, tags = "", []
        try:
            s = BeautifulSoup(get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}").text, "html.parser")
            d = s.select_one(".show-more-less-html__markup")
            desc = clean_text(d.get_text("\n")) if d else ""
            tags = [clean(x.get_text()) for x in s.select(".description__job-criteria-text")]
            time.sleep(random.uniform(1.0, 1.8))
        except Exception as e:
            log(f"  LinkedIn: sin detalle {jid}: {e}")
        job = Job.create("LinkedIn", jid, title, comp, loc, url, posted, desc, tags)
        if remote_search and job.modality == "No indicado":
            job.modality = "Remoto"
        return job

    with ThreadPoolExecutor(2) as ex:
        return list(ex.map(detail, cards.values()))
