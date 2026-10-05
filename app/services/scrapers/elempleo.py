"""Scraper de elempleo.com."""
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from app.services.scrapers.base import get
from app.models.job import Job
from app.utils.text import clean, clean_text, slug


def elempleo(query, pages=2, log=print):
    base = "https://www.elempleo.com"
    urls = []
    # Bogota, y todo el pais (de ahi solo se conservan las remotas, ver mas abajo)
    for suffix in (f"bogota/trabajo-{slug(query)}", f"trabajo-{slug(query)}"):
        for p in range(1, pages + 1):
            urls.append(f"{base}/co/ofertas-empleo/{suffix}" + (f"?Page={p}" if p > 1 else ""))
    cards = {}
    for u in urls:
        try:
            soup = BeautifulSoup(get(u).text, "html.parser")
        except Exception as e:
            log(f"  elempleo: fallo {u}: {e}")
            continue
        for c in soup.select(".result-item"):
            area = c.select_one("[data-ga4-offerdata]")
            if not area:
                continue
            try:
                meta = json.loads(area["data-ga4-offerdata"])
            except ValueError:
                continue
            link = area.get("data-url", "")
            posted = c.select_one(".info-publish-date")
            contract = ""
            for box in c.select(".small"):
                label = box.select_one(".small-text")
                if label and "contrato" in label.get_text().lower():
                    contract = clean(box.select_one("div").get_text())
            cards[meta["id"]] = (str(meta["id"]), meta.get("title", ""), meta.get("company", ""),
                                 meta.get("location", ""), base + link, clean(posted.get_text()) if posted else "",
                                 meta.get("salary", ""), contract)
        time.sleep(random.uniform(0.6, 1.2))

    def detail(c):
        jid, title, comp, loc, url, posted, sal, contract = c
        desc = ""
        try:
            time.sleep(random.uniform(0.5, 1.2))
            s = BeautifulSoup(get(url).text, "html.parser")
            d = s.select_one(".description-block")
            desc = clean_text(d.get_text("\n")) if d else ""
        except Exception as e:
            log(f"  elempleo: sin detalle {url}: {e}")
        job = Job.create("elempleo", jid, title, comp, loc, url, posted, desc, ([contract] if contract else []) + ["Salario: " + sal])
        return job

    with ThreadPoolExecutor(2) as ex:
        jobs = list(ex.map(detail, cards.values()))
    # fuera de Bogota solo sirven las ofertas remotas
    return [j for j in jobs if "bogot" in j.location.lower() or j.modality == "Remoto"]
