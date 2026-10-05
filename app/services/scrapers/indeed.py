"""Scraper de Indeed Colombia (curl_cffi imita la huella TLS de Chrome para evitar el 403)."""
import random
import re
import time

from bs4 import BeautifulSoup

from app.models.job import Job
from app.utils.text import clean, slug


def indeed(query, pages=1, log=print):
    try:
        from curl_cffi import requests as cr
    except ImportError:
        log("  Indeed: falta instalar curl_cffi (py -m pip install curl_cffi)")
        return []

    def fetch(url, **kw):
        r = cr.get(url, impersonate="chrome", timeout=25, **kw)
        if r.status_code in (403, 429):
            raise RuntimeError(f"bloqueado ({r.status_code})")
        r.raise_for_status()
        return r

    cards = {}
    searches = [{"q": query, "l": "Bogotá"}, {"q": query, "l": "Remoto"}]
    for params in searches:
        for p in range(pages):
            try:
                soup = BeautifulSoup(fetch("https://co.indeed.com/jobs", params={**params, "sort": "date", "start": p * 10}).text, "html.parser")
            except Exception as e:
                log(f"  Indeed: fallo ({e})")
                break
            items = soup.select("div.job_seen_beacon")
            if not items:
                break
            for c in items:
                a = c.select_one("h3.jobTitle a, h2.jobTitle a, a.jcs-JobTitle")
                if not a:
                    continue
                jid = a.get("data-jk") or a.get("id", "").replace("job_", "")
                co = c.select_one("[data-testid=company-name]")
                lo = c.select_one("[data-testid=text-location]")
                attrs = [clean(x.get_text()) for x in c.select("[data-testid=attribute_snippet_testid], [class*=salary-snippet], [class*=metadata]")]
                date = c.select_one("[data-testid=myJobsStateDate], .date")
                cards[jid] = (jid, clean(a.get_text()), co.get_text() if co else "", lo.get_text() if lo else "",
                              f"https://co.indeed.com/viewjob?jk={jid}", clean(date.get_text()) if date else "",
                              attrs, params["l"] == "Remoto")
            time.sleep(random.uniform(1.5, 3.0))

    # La pagina de detalle de Indeed responde 401, asi que solo se usan los datos de la tarjeta
    # (titulo, empresa, ciudad, salario, jornada). Las tecnologias salen unicamente del titulo.
    jobs, seen = [], set()
    for jid, title, comp, loc, url, posted, attrs, remote_search in cards.values():
        key = (title.lower(), comp.lower(), loc.lower())
        if key in seen:
            continue
        seen.add(key)
        job = Job.create("Indeed", jid, title, comp, loc, url, posted, "", attrs)
        if remote_search and job.modality == "No indicado":
            job.modality = "Remoto"
        if job.salary_min and any("por año" in a for a in attrs):
            job.salary_min //= 12
        jobs.append(job)
    return jobs
