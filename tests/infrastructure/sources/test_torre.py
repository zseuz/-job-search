import unittest
from datetime import datetime, timedelta, timezone

from buscador_empleos.infrastructure.sources.torre import TorreSource
from tests.support import FakeHttpClient, LogCollector, no_pause


def item(offer_id="ed891Ekr", **overrides):
    data = {
        "id": offer_id,
        "objective": "Analista de Datos",
        "slug": "interactive-media-analista-de-datos",
        "type": "full-time-employment",
        "locations": ["Chicó Norte, Bogotá, Colombia"],
        "created": (datetime.now(timezone.utc) - timedelta(days=20, hours=1)).isoformat(),
        "organizations": [{"name": "Interactive Media"}],
        "place": {"remote": True, "anywhere": False, "locationType": "hybrid"},
        "compensation": {
            "data": {
                "code": "fixed",
                "currency": "COP",
                "minAmount": 6_000_000,
                "maxAmount": 8_500_000,
                "periodicity": "monthly",
            }
        },
    }
    data.update(overrides)
    return data


DETAIL = {
    "details": [
        {"code": "responsibilities", "content": "Analizar datos con Python y SQL."},
        {"code": "requirements", "content": "Experiencia con Power BI."},
        {"code": "vacio", "content": ""},
    ]
}


def make_source(results, *, search_status=200, rates=None):
    http = FakeHttpClient()
    http.when("search.torre.co", data={"results": results}, status=search_status)
    http.when("torre.ai/api/suite", data=DETAIL)
    return TorreSource(http, pause=no_pause, rates=rates), http


class TorreSourceTest(unittest.TestCase):
    def test_parses_an_offer_with_its_detail(self):
        source, _ = make_source([item()])
        jobs = source.search("analista de datos", pages=1)
        self.assertEqual(
            len(jobs), 1
        )  # las dos búsquedas (Bogotá y remoto) traen la misma: se deduplica por id
        job = jobs[0]
        self.assertEqual(
            (job.id, job.title, job.company), ("Torre:ed891Ekr", "Analista de Datos", "Interactive Media")
        )
        self.assertEqual(job.url, "https://torre.ai/post/ed891Ekr-interactive-media-analista-de-datos")
        self.assertEqual((job.location, job.posted), ("Chicó Norte, Bogotá, Colombia", "Hace 20 días"))
        self.assertTrue({"Python", "SQL", "Power BI"} <= set(job.techs))
        for section in ("Responsabilidades", "Requisitos"):
            self.assertIn(section, job.description)

    def test_a_salary_in_cop_is_not_converted(self):
        job = make_source([item()])[0].search("x", pages=1)[0]
        self.assertEqual((job.salary_text, job.salary_min), ("COP 6.000.000 - 8.500.000 / mes", 6_000_000))

    def test_a_salary_in_another_currency_and_period(self):
        offer = item(compensation={"data": {"currency": "USD", "minAmount": 60000, "periodicity": "yearly"}})
        self.assertEqual(make_source([offer])[0].search("x", pages=1)[0].salary_min, 20_000_000)

    def test_uses_the_configured_exchange_rates(self):
        offer = item(compensation={"data": {"currency": "USD", "minAmount": 1000, "periodicity": "monthly"}})
        self.assertEqual(
            make_source([offer], rates={"USD": 3000})[0].search("x", pages=1)[0].salary_min, 3_000_000
        )

    def test_to_be_agreed_has_no_salary(self):
        offer = item(compensation={"data": {"code": "to-be-agreed", "currency": "USD", "minAmount": 0.0}})
        job = make_source([offer])[0].search("x", pages=1)[0]
        self.assertEqual((job.salary_text, job.salary_min), ("", None))

    def test_modality(self):
        cases = (
            ({"remote": True, "locationType": "hybrid"}, "Híbrido"),
            ({"remote": True, "locationType": "remote"}, "Remoto"),
            ({"remote": False, "anywhere": True}, "Remoto"),
            ({"remote": False, "anywhere": False}, "Presencial"),
        )
        for place, expected in cases:
            self.assertEqual(
                make_source([item(place=place)])[0].search("x", pages=1)[0].modality, expected, place
            )

    def test_the_offer_type_becomes_the_contract_label(self):
        job = make_source([item(type="internship")])[0].search("x", pages=1)[0]
        self.assertEqual(job.contract, "Práctica")

    def test_sends_the_bogota_and_remote_filters(self):
        source, http = make_source([item()])
        source.search("analista de datos", pages=1)
        bodies = [c.body for c in http.calls if c.method == "POST"]
        self.assertEqual(len(bodies), 2)
        self.assertIn({"location": {"term": "Bogotá"}}, bodies[0]["and"])
        self.assertIn({"remote": {"term": True}}, bodies[1]["and"])
        self.assertEqual(bodies[0]["and"][0]["skill/role"]["text"], "analista de datos")

    def test_the_offer_is_kept_when_its_detail_fails(self):
        http = (
            FakeHttpClient().when("search.torre.co", data={"results": [item()]}).when("torre.ai", status=500)
        )
        log = LogCollector()
        jobs = TorreSource(http, pause=no_pause).search("analista de datos", pages=1, log=log)
        self.assertEqual(len(jobs), 1)
        self.assertFalse(jobs[0].has_description())
        self.assertTrue(log.contains("sin detalle"))

    def test_a_400_means_the_api_changed_and_is_reported_once(self):
        source, http = make_source([], search_status=400)
        log = LogCollector()
        self.assertEqual(source.search("analista de datos", pages=3, log=log), [])
        self.assertEqual(len(http.calls), 1)  # no insiste con la otra búsqueda ni con más páginas
        self.assertEqual(len(log.messages), 1)
        self.assertIn("400", log.messages[0])

    def test_other_http_errors_are_logged_without_crashing(self):
        source, _ = make_source([], search_status=500)
        log = LogCollector()
        self.assertEqual(source.search("analista de datos", pages=1, log=log), [])
        self.assertTrue(log.contains("fallo"))

    def test_a_connection_error_is_logged(self):
        http = FakeHttpClient().when("search.torre.co", error=ConnectionError("sin red"))
        log = LogCollector()
        self.assertEqual(TorreSource(http, pause=no_pause).search("x", pages=1, log=log), [])
        self.assertTrue(log.contains("Torre: fallo"))

    def test_asks_for_the_next_page_only_when_the_current_one_is_full(self):
        full_page = [item(f"id{n}") for n in range(20)]
        source, http = make_source(full_page)
        source.search("x", pages=2)
        offsets = [c.params["offset"] for c in http.calls if c.method == "POST"]
        self.assertEqual(offsets, [0, 20, 0, 20])  # dos páginas por cada una de las dos búsquedas


if __name__ == "__main__":
    unittest.main()
