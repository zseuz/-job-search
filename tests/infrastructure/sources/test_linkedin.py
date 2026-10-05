import unittest

from buscador_empleos.infrastructure.sources.linkedin import LinkedinSource
from tests.support import FakeHttpClient, LogCollector, no_pause

LISTING = """
<li><div class="base-card" data-entity-urn="urn:li:jobPosting:111">
  <a class="base-card__full-link" href="https://co.linkedin.com/jobs/view/data-analyst-111?position=1&refId=x"></a>
  <h3 class="base-search-card__title">Data Analyst</h3>
  <h4 class="base-search-card__subtitle">ACME</h4>
  <span class="job-search-card__location">Bogotá, Colombia</span>
  <time>Hace 2 días</time></div></li>
<li><div class="base-card"><h3 class="base-search-card__title">Sin identificador</h3></div></li>
"""
DETAIL = """
<div class="show-more-less-html__markup"><p>Buscamos analista con <strong>Python</strong> y SQL.</p><p>Power BI deseable.</p></div>
<span class="description__job-criteria-text">Tiempo completo</span>
<span class="description__job-criteria-text">Intermedio</span>
"""


def make_source(detail_reply=None):
    http = FakeHttpClient()
    if detail_reply is None:
        http.when("jobPosting/", text=DETAIL)
    else:
        http.when("jobPosting/", **detail_reply)
    # el listado solo trae resultados en la primera página; la siguiente viene vacía
    http.when(lambda call: call.params is not None and call.params["start"] == 0, text=LISTING)
    http.when("seeMoreJobPostings", text="<ul></ul>")
    return LinkedinSource(http, pause=no_pause), http


class LinkedinSourceTest(unittest.TestCase):
    def test_parses_listing_and_detail(self):
        source, _ = make_source()
        jobs = source.search("analista de datos", pages=2)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual((job.id, job.title, job.company), ("LinkedIn:111", "Data Analyst", "ACME"))
        self.assertEqual(
            job.url, "https://co.linkedin.com/jobs/view/data-analyst-111"
        )  # sin los parámetros de rastreo
        self.assertEqual((job.location, job.posted), ("Bogotá, Colombia", "Hace 2 días"))
        self.assertTrue({"Python", "SQL", "Power BI"} <= set(job.techs))
        self.assertIn("Buscamos analista con", job.description)
        self.assertEqual(job.roles, ["Analista de datos"])

    def test_an_offer_found_by_the_remote_search_is_marked_remote(self):
        source, _ = make_source()
        # la última búsqueda es la de f_WT=2 (solo remoto) y la oferta no indica modalidad
        self.assertEqual(source.search("analista de datos", pages=1)[0].modality, "Remoto")

    def test_searches_bogota_and_then_remote_only(self):
        source, http = make_source()
        source.search("dev", pages=1)
        searches = [c.params for c in http.calls if c.params and "location" in c.params]
        self.assertEqual(
            [(p["location"], p.get("f_WT")) for p in searches],
            [("Bogotá, Colombia", None), ("Colombia", "2")],
        )

    def test_rate_limit_is_logged_and_gives_nothing(self):
        log = LogCollector()
        http = FakeHttpClient().when("seeMoreJobPostings", status=429)
        self.assertEqual(LinkedinSource(http, pause=no_pause).search("dev", pages=2, log=log), [])
        self.assertTrue(log.contains("429"))
        self.assertEqual(len(http.calls), 2)  # una por búsqueda: no insiste con las demás páginas

    def test_a_failed_detail_keeps_the_offer_without_description(self):
        log = LogCollector()
        source, _ = make_source({"status": 429})
        job = source.search("dev", pages=1, log=log)[0]
        self.assertTrue(log.contains("sin detalle 111"))
        self.assertFalse(job.has_description())
        self.assertEqual(job.title, "Data Analyst")


if __name__ == "__main__":
    unittest.main()
