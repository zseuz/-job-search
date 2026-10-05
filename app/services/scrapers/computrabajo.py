"""Scraper de Computrabajo Colombia."""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from app.services.scrapers.base import get
from app.models.job import Job
from app.utils.text import clean, clean_text, slug


def computrabajo(query, pages=2, log=print):
    base = "https://co.computrabajo.com"
    urls = []
    for suffix in (f"trabajo-de-{slug(query)}-en-bogota-dc", f"trabajo-de-{slug(query)}-remoto"):
        for p in range(1, pages + 1):
            urls.append(f"{base}/{suffix}" + (f"?p={p}" if p > 1 else ""))
    cards = {}
    for u in urls:
        try:
            soup = BeautifulSoup(get(u).text, "html.parser")
        except Exception as e:
            log(f"  Computrabajo: fallo {u}: {e}")
            continue
        for a in soup.select("article.box_offer"):
            link = a.select_one("h2 a")
            if not link:
                continue
            jid = a.get("data-id") or link["href"]
            comp = a.select_one("a[offer-grid-article-company-url]") or a.select_one("p a")
            loc = a.select_one("p.fs16.fc_base.mt5:not(.dFlex) span.mr10")
            posted = a.select_one("p.fs13")
            cards[jid] = (jid, link.get_text(), comp.get_text() if comp else "",
                          loc.get_text() if loc else "", base + link["href"].split("#")[0],
                          posted.get_text() if posted else "")
        time.sleep(random.uniform(0.6, 1.2))

    def detail(c):
        jid, title, comp, loc, url, posted = c
        try:
            time.sleep(random.uniform(0.5, 1.2))
            s = BeautifulSoup(get(url).text, "html.parser")
            box = s.select_one("div[div-link=oferta]")
            tags = [clean(t.get_text()) for t in box.select("span.tag")] if box else []
            # las etiquetas (salario, contrato, jornada) ya van aparte: no se repiten en la descripcion
            for el in (box.select("h2, span.tag") if box else []):
                el.decompose()
            desc = clean_text(box.get_text("\n")) if box else ""
            # el salario viene como etiqueta ("$ 4.000.000 (Mensual)" / "A convenir")
            return Job.create("Computrabajo", jid, title, comp, loc, url, posted, desc, tags)
        except Exception as e:
            log(f"  Computrabajo: sin detalle {url}: {e}")
            return Job.create("Computrabajo", jid, title, comp, loc, url, posted)

    with ThreadPoolExecutor(2) as ex:
        return list(ex.map(detail, cards.values()))
