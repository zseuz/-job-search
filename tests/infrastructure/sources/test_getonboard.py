import unittest
from datetime import datetime, timedelta, timezone

from buscador_empleos.infrastructure.sources.getonboard import GetOnBoardSource
from tests.support import FakeHttpClient, LogCollector, no_pause


def epoch_days_ago(days):
    return int((datetime.now(timezone.utc) - timedelta(days=days, hours=1)).timestamp())


def item(job_id="dev-1", **overrides):
    attrs = {
        "title": "Desarrollador Full-Stack",
        "remote": True,
        "remote_modality": "remote_local",
        "countries": ["Colombia"],
        "category_name": "Programming",
        "min_salary": 2200,
        "max_salary": 2500,
        "published_at": epoch_days_ago(2),
        "projects": "<p>Construimos productos con <b>Node.js</b></p>",
        "functions": "<ul><li>Backend</li><li>Frontend</li></ul>",
        "description": "<p>Experiencia en JavaScript y PostgreSQL</p>",
        "desirable": "",
        "benefits": "<p>Seguro</p>",
        "company": {"data": {"attributes": {"name": "Mediastream"}}},
        "location_cities": {"data": [{"attributes": {"name": "Bogotá", "country": "Colombia"}}]},
    }
    attrs.update(overrides)
    return {
        "id": job_id,
        "type": "job",
        "attributes": attrs,
        "links": {"public_url": f"https://www.getonbrd.com/jobs/{job_id}"},
    }


def search(items, *, total_pages=1, pages=1, rates=None):
    http = FakeHttpClient().when("getonbrd.com", data={"data": items, "meta": {"total_pages": total_pages}})
    source = GetOnBoardSource(http, pause=no_pause, rates=rates)
    return source.search("desarrollador", pages=pages), http


class GetOnBoardSourceTest(unittest.TestCase):
    def test_parses_an_offer(self):
        jobs, http = search([item()])
        job = jobs[0]
        self.assertEqual(
            (job.id, job.title, job.company),
            ("Get on Board:dev-1", "Desarrollador Full-Stack", "Mediastream"),
        )
        self.assertEqual((job.location, job.url), ("Bogotá", "https://www.getonbrd.com/jobs/dev-1"))
        self.assertEqual((job.modality, job.posted), ("Remoto", "Hace 2 días"))
        self.assertTrue({"Node.js", "JavaScript", "PostgreSQL"} <= set(job.techs))
        self.assertEqual(http.calls[0].params["country_code"], "CO")
        self.assertEqual(http.calls[0].headers["Accept"], "application/json")

    def test_salary_is_converted_to_cop(self):
        job = search([item()])[0][0]
        self.assertEqual((job.salary_text, job.salary_min), ("USD 2.200 - 2.500 / mes", 8_800_000))

    def test_uses_the_configured_exchange_rates(self):
        job = search([item()], rates={"USD": 3000})[0][0]
        self.assertEqual(job.salary_min, 6_600_000)

    def test_only_a_maximum_salary(self):
        job = search([item(min_salary=None, max_salary=3000)])[0][0]
        self.assertEqual(job.salary_min, 12_000_000)

    def test_without_salary(self):
        job = search([item(min_salary=None, max_salary=None)])[0][0]
        self.assertEqual((job.salary_text, job.salary_min), ("", None))

    def test_modality_mapping(self):
        cases = (
            ("no_remote", False, "Presencial"),
            ("hybrid", False, "Híbrido"),
            ("remote_local", True, "Remoto"),
            ("fully_remote", True, "Remoto"),
            ("otro", False, "No indicado"),
        )
        for api_value, remote, expected in cases:
            job = search([item(remote_modality=api_value, remote=remote)])[0][0]
            self.assertEqual(job.modality, expected, api_value)

    def test_description_is_assembled_from_sections_as_plain_text(self):
        job = search([item()])[0][0]
        for fragment in ("Sobre el proyecto", "• Backend", "Requisitos", "Beneficios"):
            self.assertIn(fragment, job.description)
        self.assertNotIn("Deseable", job.description)  # sección vacía
        self.assertNotIn("<", job.description)

    def test_location_falls_back_to_the_countries(self):
        self.assertEqual(search([item(location_cities={"data": []})])[0][0].location, "Colombia")

    def test_stops_when_there_are_no_more_pages(self):
        self.assertEqual(len(search([item()], total_pages=1, pages=3)[1].calls), 1)

    def test_walks_every_requested_page(self):
        _, http = search([item()], total_pages=3, pages=3)
        self.assertEqual([c.params["page"] for c in http.calls], [1, 2, 3])

    def test_a_network_error_is_logged(self):
        http = FakeHttpClient().when("getonbrd.com", error=ConnectionError("sin red"))
        log = LogCollector()
        self.assertEqual(GetOnBoardSource(http, pause=no_pause).search("dev", pages=2, log=log), [])
        self.assertTrue(log.contains("Get on Board: fallo"))

    def test_an_http_error_is_logged(self):
        http = FakeHttpClient().when("getonbrd.com", status=500)
        log = LogCollector()
        self.assertEqual(GetOnBoardSource(http, pause=no_pause).search("dev", pages=1, log=log), [])
        self.assertTrue(log.contains("HTTP 500"))


if __name__ == "__main__":
    unittest.main()
