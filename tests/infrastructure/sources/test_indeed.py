import unittest

from buscador_empleos.infrastructure.sources.indeed import IndeedSource
from tests.support import FakeHttpClient, LogCollector, no_pause


def card(job_key, title, location="Bogotá, Cundinamarca", *attributes):
    spans = "".join(f'<span data-testid="attribute_snippet_testid">{a}</span>' for a in attributes)
    return f"""<div class="job_seen_beacon"><h3 class="jobTitle"><a class="jcs-JobTitle" data-jk="{job_key}"><span>{title}</span></a></h3>
      <span data-testid="company-name">ACME</span><div data-testid="text-location">{location}</div>{spans}</div>"""


def search(html="", **reply):
    http = FakeHttpClient().when("indeed.com/jobs", text=html, **reply)
    log = LogCollector()
    jobs = IndeedSource(http, pause=no_pause).search("analista de datos", pages=1, log=log)
    return jobs, log, http


class IndeedSourceTest(unittest.TestCase):
    def test_parses_the_result_card(self):
        jobs, _, _ = search(
            card("abc", "Analista de datos", "Bogotá, Cundinamarca", "$2.000.000 por mes", "Tiempo completo")
        )
        self.assertEqual(len(jobs), 1)  # las dos búsquedas devuelven la misma oferta: se deduplica
        job = jobs[0]
        self.assertEqual((job.id, job.title, job.company), ("Indeed:abc", "Analista de datos", "ACME"))
        self.assertEqual(job.url, "https://co.indeed.com/viewjob?jk=abc")
        self.assertEqual(job.salary_min, 2_000_000)
        self.assertFalse(job.has_description())  # Indeed no entrega descripción

    def test_yearly_salary_is_converted_to_monthly(self):
        jobs, _, _ = search(card("y1", "Dev", "Bogotá", "$24.000.000 por año"))
        self.assertEqual(jobs[0].salary_min, 2_000_000)

    def test_cloudflare_block_is_reported(self):
        jobs, log, _ = search("<html>Just a moment...</html>", status=403)
        self.assertEqual(jobs, [])
        self.assertTrue(log.contains("bloqueado (403)"))

    def test_rate_limit_is_reported_as_blocked_too(self):
        _, log, _ = search("", status=429)
        self.assertTrue(log.contains("bloqueado (429)"))

    def test_other_http_errors_are_reported(self):
        _, log, _ = search("", status=500)
        self.assertTrue(log.contains("HTTP 500"))

    def test_searches_bogota_then_remote(self):
        _, _, http = search(card("abc", "Dev"))
        self.assertEqual([c.params["l"] for c in http.calls], ["Bogotá", "Remoto"])

    def test_offers_from_the_remote_search_are_marked_remote(self):
        http = FakeHttpClient()
        http.when(lambda c: c.params["l"] == "Remoto", text=card("r1", "Dev remoto sin marca", "Colombia"))
        http.when("indeed.com/jobs", text="")
        jobs = IndeedSource(http, pause=no_pause).search("dev", pages=1)
        self.assertEqual([(j.id, j.modality) for j in jobs], [("Indeed:r1", "Remoto")])

    def test_duplicates_are_collapsed(self):
        jobs, _, _ = search(card("a", "Dev", "Bogotá") + card("b", "Dev", "Bogotá"))
        self.assertEqual(len(jobs), 1)

    def test_a_page_without_results_gives_nothing(self):
        jobs, _, _ = search("<html><body>Sin resultados</body></html>")
        self.assertEqual(jobs, [])

    def test_a_connection_error_is_logged(self):
        http = FakeHttpClient().when("indeed.com/jobs", error=ConnectionError("sin red"))
        log = LogCollector()
        self.assertEqual(IndeedSource(http, pause=no_pause).search("dev", pages=1, log=log), [])
        self.assertTrue(log.contains("Indeed: fallo"))


if __name__ == "__main__":
    unittest.main()
