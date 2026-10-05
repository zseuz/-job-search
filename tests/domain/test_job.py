import unittest
from datetime import datetime, timedelta

from buscador_empleos.domain.job import MAX_DESCRIPTION, MIN_DESCRIPTION, Job
from tests.support import make_job


class JobCreateTest(unittest.TestCase):
    def test_derives_fields_from_raw_data(self):
        job = Job.create(
            source="Computrabajo",
            source_id="A1",
            title="Desarrollador Java Senior",
            company="ACME S.A.",
            location="Bogotá, D.C.",
            url="https://x/a1",
            posted="Hace 3 días",
            description="Buscamos experto en Java y Angular. Modalidad de trabajo: Presencial. Salario: $ 5.000.000",
            tags=["Contrato a término indefinido", "Tiempo Completo"],
        )
        self.assertEqual(job.id, "Computrabajo:A1")
        self.assertEqual(job.roles, ["Desarrollador"])
        self.assertTrue({"Java", "Angular"} <= set(job.techs))
        self.assertEqual(job.modality, "Presencial")
        self.assertEqual(job.salary_min, 5_000_000)
        self.assertEqual(job.contract, "Contrato a término indefinido")
        self.assertEqual(job.age_days, 3)

    def test_uses_the_injected_clock(self):
        job = Job.create(source="X", source_id="1", title="Dev", now=datetime(2026, 10, 1, 8, 30, 45))
        self.assertEqual(job.scraped_at, "2026-10-01T08:30")

    def test_cleans_text_fields(self):
        job = Job.create(
            source="X",
            source_id="1",
            title="  Dev \n Python ",
            company=" ACME  \n",
            location=" Bogotá ",
            posted=" Hace 1 día ",
        )
        self.assertEqual(
            (job.title, job.company, job.location, job.posted), ("Dev Python", "ACME", "Bogotá", "Hace 1 día")
        )

    def test_explicit_salary_and_modality_win_over_deduction(self):
        job = Job.create(
            source="X",
            source_id="1",
            title="Dev",
            description="Salario: $ 1.000.000 presencial",
            salary=("USD 3.000 / mes", 12_000_000),
            modality="Remoto",
        )
        self.assertEqual(
            (job.salary_text, job.salary_min, job.modality), ("USD 3.000 / mes", 12_000_000, "Remoto")
        )

    def test_salary_is_also_read_from_tags(self):
        job = Job.create(
            source="Indeed", source_id="1", title="Dev", tags=["$2.000.000 por mes", "Tiempo completo"]
        )
        self.assertEqual(job.salary_min, 2_000_000)

    def test_description_is_capped(self):
        job = Job.create(source="X", source_id="1", title="Dev", description="x" * 20000)
        self.assertEqual(len(job.description), MAX_DESCRIPTION)

    def test_minimal_offer(self):
        job = Job.create(source="X", source_id="1", title="Contador")
        self.assertEqual(
            (job.salary_min, job.contract, job.age_days, job.modality), (None, "", None, "No indicado")
        )
        self.assertEqual(job.roles, ["Otros"])

    def test_requires_keyword_arguments(self):
        with self.assertRaises(TypeError):
            Job.create("X", "1", "Dev")  # type: ignore[misc]


class JobDescriptionTest(unittest.TestCase):
    def test_short_metadata_is_not_a_description(self):
        self.assertFalse(make_job(description="Tiempo completo").has_description())
        self.assertFalse(make_job(description="").has_description())

    def test_threshold(self):
        self.assertTrue(make_job(description="x" * MIN_DESCRIPTION).has_description())
        self.assertFalse(make_job(description="x" * (MIN_DESCRIPTION - 1)).has_description())


class JobSerializationTest(unittest.TestCase):
    def test_roundtrip(self):
        original = make_job("7", title="Data Analyst", description="SQL y Power BI. " * 20)
        self.assertEqual(Job.from_dict(original.to_dict()), original)

    def test_from_dict_ignores_unknown_keys(self):
        data = make_job().to_dict()
        data["campo_futuro"] = "x"
        self.assertEqual(Job.from_dict(data).id, data["id"])

    def test_from_dict_recomputes_derived_fields_by_default(self):
        data = make_job(title="Desarrollador").to_dict()
        data["techs"], data["roles"] = [], []
        job = Job.from_dict(data)
        self.assertIn("Python", job.techs)
        self.assertEqual(job.roles, ["Desarrollador"])

    def test_from_dict_can_skip_recomputing(self):
        data = make_job().to_dict()
        data["techs"], data["roles"] = ["Marca"], ["Nada"]
        job = Job.from_dict(data, refresh=False)
        self.assertEqual((job.techs, job.roles), (["Marca"], ["Nada"]))

    def test_from_dict_rejects_data_without_required_fields(self):
        with self.assertRaises(TypeError):
            Job.from_dict({"title": "sin id"})


class JobDaysAgoTest(unittest.TestCase):
    def test_adds_the_time_since_it_was_read(self):
        job = make_job(posted="Hace 2 días")
        job.scraped_at = (datetime.now() - timedelta(days=3)).isoformat()
        self.assertAlmostEqual(job.days_ago() or 0, 5, delta=0.05)

    def test_uses_the_fallback_when_it_has_no_read_date(self):
        job = make_job(posted="Hace 1 día")
        job.scraped_at = ""
        fallback = (datetime.now() - timedelta(days=2)).isoformat()
        self.assertAlmostEqual(job.days_ago(fallback_seen=fallback) or 0, 3, delta=0.05)

    def test_no_date_means_unknown(self):
        self.assertIsNone(make_job(posted="").days_ago())

    def test_never_negative(self):
        job = make_job(posted="Hoy")
        job.scraped_at = (datetime.now() + timedelta(days=1)).isoformat()
        self.assertEqual(job.days_ago(), 0)

    def test_uses_the_given_now(self):
        job = make_job(posted="Hace 1 día")
        job.scraped_at = "2026-10-01T10:00"
        self.assertEqual(job.days_ago(now=datetime(2026, 10, 3, 10, 0)), 3)


if __name__ == "__main__":
    unittest.main()
