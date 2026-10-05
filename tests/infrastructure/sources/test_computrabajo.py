import unittest

from buscador_empleos.infrastructure.sources.computrabajo import ComputrabajoSource
from tests.support import FakeHttpClient, LogCollector, no_pause

LISTING = """
<article class="box_offer" data-id="ABC123">
  <h2><a class="js-o-link" href="/ofertas-de-trabajo/oferta-de-trabajo-de-dev-java-ABC123#lc=ListOffers">Desarrollador Java</a></h2>
  <p class="dFlex vm_fx fs16 fc_base mt5"><span class="fx_none mr10"><span class="fwB">4,4</span></span>
     <a class="fc_base" offer-grid-article-company-url href="/c">ACME S.A.</a></p>
  <p class="fs16 fc_base mt5"><span class="mr10">Bogotá, D.C., Bogotá, D.C.</span></p>
  <p class="fs13 fc_aux mt15">Hace  3  días</p>
</article>
<article class="box_offer"><p>sin enlace: se ignora</p></article>
"""
DETAIL = """
<div div-link="oferta">
  <h2 class="fwB fs18 mb20">Descripción de la oferta</h2>
  <div class="mbB"><span class="tag base">$ 4.000.000 (Mensual)</span>
    <span class="tag base">Contrato a término indefinido</span><span class="tag base">Tiempo Completo</span></div>
  <p class="mbB">Buscamos desarrollador con Java y Angular.
Requisitos: SQL Server</p>
</div>
"""


class ComputrabajoSourceTest(unittest.TestCase):
    def setUp(self):
        self.http = FakeHttpClient()
        self.http.when("/ofertas-de-trabajo/", text=DETAIL).when("/trabajo-de-", text=LISTING)
        self.source = ComputrabajoSource(self.http, pause=no_pause)

    def test_parses_listing_and_detail(self):
        jobs = self.source.search("desarrollador java", pages=1)
        self.assertEqual(len(jobs), 1)  # las dos búsquedas (Bogotá y remoto) traen la misma oferta
        job = jobs[0]
        self.assertEqual((job.id, job.source), ("Computrabajo:ABC123", "Computrabajo"))
        self.assertEqual((job.title, job.company), ("Desarrollador Java", "ACME S.A."))
        self.assertEqual(
            job.location, "Bogotá, D.C., Bogotá, D.C."
        )  # no confunde la ubicación con la calificación "4,4"
        self.assertEqual(
            job.url, "https://co.computrabajo.com/ofertas-de-trabajo/oferta-de-trabajo-de-dev-java-ABC123"
        )
        self.assertEqual(job.posted, "Hace 3 días")
        self.assertEqual(job.salary_min, 4_000_000)
        self.assertEqual(job.contract, "Contrato a término indefinido")
        self.assertTrue({"Java", "Angular", "SQL Server"} <= set(job.techs))

    def test_description_does_not_repeat_the_heading_or_the_tags(self):
        job = self.source.search("java", pages=1)[0]
        self.assertNotIn("Descripción de la oferta", job.description)
        self.assertNotIn("Tiempo Completo", job.description)
        self.assertIn("Buscamos desarrollador con Java y Angular.", job.description)

    def test_requests_the_bogota_and_remote_listings_page_by_page(self):
        self.source.search("analista de datos", pages=2)
        listings = [u for u in self.http.urls() if "/ofertas-de-trabajo/" not in u]
        self.assertEqual(
            listings,
            [
                "https://co.computrabajo.com/trabajo-de-analista-de-datos-en-bogota-dc",
                "https://co.computrabajo.com/trabajo-de-analista-de-datos-en-bogota-dc?p=2",
                "https://co.computrabajo.com/trabajo-de-analista-de-datos-remoto",
                "https://co.computrabajo.com/trabajo-de-analista-de-datos-remoto?p=2",
            ],
        )

    def test_keeps_the_offer_when_the_detail_fails(self):
        http = (
            FakeHttpClient()
            .when("/ofertas-de-trabajo/", error=TimeoutError("lento"))
            .when("/trabajo-de-", text=LISTING)
        )
        log = LogCollector()
        jobs = ComputrabajoSource(http, pause=no_pause).search("java", pages=1, log=log)
        self.assertEqual([j.title for j in jobs], ["Desarrollador Java"])
        self.assertFalse(jobs[0].has_description())
        self.assertTrue(log.contains("sin detalle"))

    def test_an_http_error_in_the_detail_is_also_handled(self):
        http = FakeHttpClient().when("/ofertas-de-trabajo/", status=403).when("/trabajo-de-", text=LISTING)
        log = LogCollector()
        jobs = ComputrabajoSource(http, pause=no_pause).search("java", pages=1, log=log)
        self.assertEqual(len(jobs), 1)
        self.assertTrue(log.contains("HTTP 403"))

    def test_a_failing_listing_is_logged_and_skipped(self):
        log = LogCollector()
        http = FakeHttpClient().when("/trabajo-de-", error=ConnectionError("caído"))
        self.assertEqual(ComputrabajoSource(http, pause=no_pause).search("java", pages=1, log=log), [])
        self.assertEqual(len([m for m in log.messages if "fallo" in m]), 2)

    def test_detail_page_without_the_offer_box_gives_a_basic_offer(self):
        http = (
            FakeHttpClient()
            .when("/ofertas-de-trabajo/", text="<html></html>")
            .when("/trabajo-de-", text=LISTING)
        )
        job = ComputrabajoSource(http, pause=no_pause).search("java", pages=1)[0]
        self.assertEqual((job.title, job.description), ("Desarrollador Java", ""))

    def test_source_name(self):
        self.assertEqual(ComputrabajoSource.name, "Computrabajo")


if __name__ == "__main__":
    unittest.main()
