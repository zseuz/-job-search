"""Pruebas del modelo (sin red):  py -m unittest discover -s tests"""
import tempfile
import unittest
from pathlib import Path

from app.models.extractors import classify_roles, detect_modality, extract_techs, parse_age_days, parse_salary
from app.models.job import Job
from app.models.job_repository import JobRepository


class ExtractorsTest(unittest.TestCase):
    def test_salary(self):
        self.assertEqual(parse_salary("Salario: $3 a $3,5 millones")[1], 3_000_000)
        self.assertEqual(parse_salary("$ 2.655.000,00 (Mensual)")[1], 2_655_000)
        self.assertIsNone(parse_salary("Salario: A convenir")[1])

    def test_age(self):
        self.assertEqual(parse_age_days("Hoy"), 0)
        self.assertEqual(parse_age_days("Ayer"), 1)
        self.assertEqual(parse_age_days("Hace 2 semanas"), 14)
        self.assertEqual(parse_age_days("Más de 30 días"), 31)
        self.assertIsNone(parse_age_days(""))

    def test_roles_and_techs(self):
        self.assertEqual(classify_roles("Desarrollador Java Senior"), ["Desarrollador"])
        self.assertEqual(classify_roles("Analista Comercial"), ["Otros"])
        self.assertIn("Java", extract_techs("Experiencia en Java y Angular"))
        self.assertNotIn("Java", extract_techs("Experiencia en JavaScript"))
        self.assertNotIn("SQL", extract_techs("Conocimiento de NoSQL"))

    def test_modality(self):
        self.assertEqual(detect_modality("Analista Semipresencial"), "Híbrido")
        self.assertEqual(detect_modality("Dev", "100% remoto"), "Remoto")


class RepositoryTest(unittest.TestCase):
    def test_merge_keeps_good_description(self):
        with tempfile.TemporaryDirectory() as d:
            repo = JobRepository(Path(d) / "jobs.json")
            good = Job.create("X", "1", "Desarrollador Python", "ACME", "Bogotá", "u", "Hoy", "Python y SQL")
            repo.merge([good])
            empty = Job.create("X", "1", "Desarrollador Python", "ACME", "Bogotá", "u", "Hoy", "")
            repo.merge([empty])
            _, jobs = repo.load()
            self.assertEqual(len(jobs), 1)
            self.assertIn("Python", jobs[0].techs)


if __name__ == "__main__":
    unittest.main()


class DescriptionTest(unittest.TestCase):
    def test_short_metadata_is_not_a_description(self):
        short = Job.create("Indeed", "1", "Dev", "A", "Bogotá", "u", "", "", ["$2.000.000 por mes", "Tiempo completo"])
        self.assertFalse(short.has_description())
        self.assertEqual(short.salary_min, 2_000_000)  # el salario se sigue leyendo de las etiquetas
        long = Job.create("X", "2", "Dev", "A", "Bogotá", "u", "", "Texto largo. " * 30)
        self.assertTrue(long.has_description())


class SalaryDatesAndFiltersTest(unittest.TestCase):
    def test_currency_conversion(self):
        from app.models.extractors import format_salary, to_cop_monthly
        self.assertEqual(to_cop_monthly(3000, "USD", "month"), 12_000_000)
        self.assertEqual(to_cop_monthly(60000, "USD", "year"), 20_000_000)
        self.assertIsNone(to_cop_monthly(100, "XXX", "month"))
        self.assertEqual(format_salary(3000, 4500, "USD", "month"), "USD 3.000 - 4.500 / mes")

    def test_title_matches_query_in_english(self):
        from app.models.extractors import title_matches_query
        self.assertTrue(title_matches_query("Senior Software Engineer", "desarrollador de software"))
        self.assertTrue(title_matches_query("Data Analyst III", "analista de datos"))
        self.assertFalse(title_matches_query("Sales Manager", "desarrollador de software"))

    def test_open_to_colombia(self):
        from app.services.scrapers.base import open_to_colombia
        self.assertTrue(open_to_colombia([]))
        self.assertTrue(open_to_colombia(["LATAM", "USA"]))
        self.assertFalse(open_to_colombia(["United States"]))

    def test_relative_dates(self):
        from datetime import datetime, timedelta, timezone
        from app.utils.text import ago_text
        now = datetime.now(timezone.utc)
        self.assertEqual(ago_text(now - timedelta(days=1, hours=1)), "Hace 1 día")
        self.assertEqual(ago_text(now - timedelta(days=400)), "Hace 1 año")
        self.assertEqual(parse_age_days(ago_text(now - timedelta(days=3, hours=1))), 3)


class ExpandQueriesTest(unittest.TestCase):
    def test_expand_adds_related_roles_without_duplicates(self):
        from app.models.extractors import expand_queries
        out = expand_queries(["desarrollador de software", "analista de datos"])
        self.assertEqual(out[0], "desarrollador de software")
        self.assertIn("programador", out)
        self.assertIn("data analyst", out)
        self.assertEqual(len(out), len({q.lower() for q in out}))

    def test_unknown_role_is_left_alone(self):
        from app.models.extractors import expand_queries
        self.assertEqual(expand_queries(["contador"]), ["contador"])
