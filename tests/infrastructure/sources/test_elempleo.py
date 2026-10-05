import json
import unittest

from buscador_empleos.infrastructure.sources.elempleo import ElempleoSource
from tests.support import FakeHttpClient, LogCollector, no_pause


def card(offer_id, title, location, salary="$3 a $3,5 millones", contract="Indefinido"):
    meta = json.dumps(
        {"id": offer_id, "title": title, "company": "ACME", "location": location, "salary": salary}
    )
    return f"""<div class="result-item"><div data-ga4-offerdata='{meta}' data-url="/co/ofertas-trabajo/oferta-{offer_id}">
      <span class="info-publish-date">Hoy</span>
      <div class="small"><div>{contract}</div><div class="small-text">Tipo de contrato</div></div></div></div>"""


LISTING = (
    "<html>"
    + card(1, "Programador C#", "Bogotá")
    + card(2, "Desarrollador remoto", "Medellín")
    + card(3, "Contador", "Cali")
    + '<div class="result-item"><p>sin datos</p></div></html>'
)
REMOTE_DETAIL = (
    '<div class="description-block"><p>Descripción del cargo</p><p>Trabajo remoto con C# y .NET</p></div>'
)
ONSITE_DETAIL = '<div class="description-block"><p>Debes asistir a la oficina todos los días.</p></div>'


def make_source(listing=LISTING):
    http = FakeHttpClient()
    http.when("oferta-3", text=ONSITE_DETAIL)  # la oferta de Cali no dice nada de remoto
    http.when("/ofertas-trabajo/", text=REMOTE_DETAIL).when("/ofertas-empleo/", text=listing)
    return ElempleoSource(http, pause=no_pause), http


class ElempleoSourceTest(unittest.TestCase):
    def test_parses_the_embedded_offer_data(self):
        source, _ = make_source()
        job = {j.id: j for j in source.search("programador", pages=1)}["elempleo:1"]
        self.assertEqual((job.title, job.company, job.location), ("Programador C#", "ACME", "Bogotá"))
        self.assertEqual(job.url, "https://www.elempleo.com/co/ofertas-trabajo/oferta-1")
        self.assertEqual((job.posted, job.contract), ("Hoy", "Indefinido"))
        self.assertEqual((job.salary_text, job.salary_min), ("$3 a $3,5 millones", 3_000_000))
        self.assertTrue({"C#", ".NET"} <= set(job.techs))

    def test_outside_bogota_only_remote_offers_survive(self):
        source, _ = make_source()
        ids = {j.id for j in source.search("programador", pages=1)}
        self.assertIn("elempleo:1", ids)  # Bogotá
        self.assertIn("elempleo:2", ids)  # Medellín, pero su descripción dice «remoto»
        self.assertNotIn("elempleo:3", ids)  # Cali y presencial

    def test_search_urls_cover_bogota_and_the_whole_country(self):
        source, http = make_source()
        source.search("analista de datos", pages=2)
        listings = [u for u in http.urls() if "/ofertas-trabajo/" not in u]
        self.assertEqual(
            listings,
            [
                "https://www.elempleo.com/co/ofertas-empleo/bogota/trabajo-analista-de-datos",
                "https://www.elempleo.com/co/ofertas-empleo/bogota/trabajo-analista-de-datos?Page=2",
                "https://www.elempleo.com/co/ofertas-empleo/trabajo-analista-de-datos",
                "https://www.elempleo.com/co/ofertas-empleo/trabajo-analista-de-datos?Page=2",
            ],
        )

    def test_survives_an_expired_offer(self):
        http = (
            FakeHttpClient()
            .when("/ofertas-trabajo/", status=410)
            .when("/ofertas-empleo/", text=card(9, "Dev", "Bogotá"))
        )
        log = LogCollector()
        jobs = ElempleoSource(http, pause=no_pause).search("dev", pages=1, log=log)
        self.assertEqual([j.id for j in jobs], ["elempleo:9"])
        self.assertTrue(log.contains("sin detalle"))
        self.assertTrue(log.contains("HTTP 410"))

    def test_malformed_embedded_json_is_ignored(self):
        broken = '<div class="result-item"><div data-ga4-offerdata="{no es json" data-url="/x"></div></div>'
        source, _ = make_source(broken + card(1, "Dev", "Bogotá"))
        self.assertEqual([j.id for j in source.search("dev", pages=1)], ["elempleo:1"])

    def test_a_failing_listing_is_logged(self):
        log = LogCollector()
        http = FakeHttpClient().when("/ofertas-empleo/", error=ConnectionError("caído"))
        self.assertEqual(ElempleoSource(http, pause=no_pause).search("dev", pages=1, log=log), [])
        self.assertTrue(log.contains("elempleo: fallo"))


if __name__ == "__main__":
    unittest.main()
