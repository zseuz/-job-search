import json
import unittest

from buscador_empleos.infrastructure.sources.hireline import HirelineSource
from tests.support import FakeHttpClient, LogCollector, no_pause


def card(href, title, location, updated="Hace más de 30 días."):
    return f"""<a class="hl-vacancy-card" href="{href}"><p class="updated-text">{updated}</p>
      <p class="vacancy-title">{title}</p><p class="vacancy-subtitle">$3750 USD</p>
      <p class="vacancy-location">{location}</p></a>"""


def detail(description="<p>Backend en Laravel y frontend en Vue</p>"):
    posting = {
        "@type": "JobPosting",
        "description": description,
        "datePosted": "2026-08-05",
        "baseSalary": {
            "currency": "MXN",
            "value": {"minValue": "70000", "maxValue": "80000", "unitText": "MONTH"},
        },
    }
    return f'<script type="application/ld+json">{json.dumps(posting)}</script>'


LISTING = (
    "<html>"
    + "".join(
        [
            card(
                "https://hireline.io/remoto/empleos/dev-full-stack/114348",
                "Desarrollador Full Stack en Ventus",
                "Remoto: México, Colombia",
            ),
            card(
                "https://hireline.io/remoto/empleos/dev-usa/114349",
                "Desarrollador Backend en Acme",
                "Remoto: Estados Unidos",
            ),
            card("https://hireline.io/co/empleos/contador/114350", "Contador en Acme", "Bogotá"),
            card("https://hireline.io/co/empleos/dev-cali/114351", "Programador Java en Acme", "Cali"),
            card("https://hireline.io/co/empleos/dev-bogota/114352", "Programador PHP en Acme", "Bogotá"),
        ]
    )
    + "</html>"
)


def make_source(detail_html=None):
    http = FakeHttpClient()
    http.when("/co/empleos-de-", text=LISTING)  # el listado de búsqueda
    http.when("/empleos/", text=detail_html if detail_html is not None else detail())
    return HirelineSource(http, pause=no_pause), http


class HirelineSourceTest(unittest.TestCase):
    def test_filters_by_role_and_location(self):
        source, _ = make_source()
        titles = sorted(job.title for job in source.search("desarrollador de software", pages=1))
        # fuera: otro cargo (Contador), remoto solo para EE. UU. (Backend) y presencial en Cali (Java)
        self.assertEqual(titles, ["Desarrollador Full Stack", "Programador PHP"])

    def test_splits_the_company_from_the_title(self):
        source, _ = make_source()
        job = next(
            j
            for j in source.search("desarrollador de software", pages=1)
            if j.title == "Desarrollador Full Stack"
        )
        self.assertEqual((job.company, job.id, job.modality), ("Ventus", "Hireline:114348", "Remoto"))

    def test_reads_description_date_and_salary_from_structured_data(self):
        source, _ = make_source()
        job = next(
            j for j in source.search("desarrollador de software", pages=1) if j.id == "Hireline:114348"
        )
        self.assertIn("Laravel", job.description)
        self.assertIn("Vue", job.techs)
        self.assertEqual(job.salary_text, "MXN 70.000 - 80.000 / mes")
        self.assertEqual(job.salary_min, 15_400_000)  # 70.000 MXN * 220
        self.assertTrue(job.posted.startswith("Hace "))

    def test_uses_the_configured_exchange_rates(self):
        http = FakeHttpClient().when("/co/empleos-de-", text=LISTING).when("/empleos/", text=detail())
        source = HirelineSource(http, pause=no_pause, rates={"MXN": 100})
        job = next(
            j for j in source.search("desarrollador de software", pages=1) if j.id == "Hireline:114348"
        )
        self.assertEqual(job.salary_min, 7_000_000)

    def test_a_detail_page_without_structured_data_keeps_the_card_data(self):
        source, _ = make_source("<html></html>")
        job = source.search("desarrollador de software", pages=1)[0]
        self.assertEqual((job.salary_min, job.description), (None, ""))
        self.assertEqual(job.posted, "Hace más de 30 días.")

    def test_a_failing_detail_is_logged(self):
        http = (
            FakeHttpClient()
            .when("/co/empleos-de-", text=LISTING)
            .when("/empleos/", error=TimeoutError("lento"))
        )
        log = LogCollector()
        jobs = HirelineSource(http, pause=no_pause).search("desarrollador de software", pages=1, log=log)
        self.assertEqual(len(jobs), 2)
        self.assertTrue(log.contains("sin detalle"))

    def test_a_failing_listing_is_logged(self):
        log = LogCollector()
        http = FakeHttpClient().when("/co/empleos-de-", error=ConnectionError("caído"))
        self.assertEqual(HirelineSource(http, pause=no_pause).search("desarrollador", pages=1, log=log), [])
        self.assertTrue(log.contains("Hireline: fallo"))


if __name__ == "__main__":
    unittest.main()
