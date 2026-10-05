import unittest
from datetime import datetime, timedelta, timezone

from buscador_empleos.domain.dates import ago_text, parse_age_days


class ParseAgeTest(unittest.TestCase):
    def test_relative_expressions(self):
        self.assertEqual(parse_age_days("Hoy"), 0)
        self.assertEqual(parse_age_days("Ayer"), 1)
        self.assertEqual(parse_age_days("Hace 3 días"), 3)
        self.assertEqual(parse_age_days("Hace  1  semana"), 7)
        self.assertEqual(parse_age_days("Hace 2 meses"), 60)
        self.assertEqual(parse_age_days("Hace 1 año"), 365)
        self.assertAlmostEqual(parse_age_days("Hace 12 horas") or 0, 0.5)
        self.assertAlmostEqual(parse_age_days("Hace 30 minutos") or 0, 30 / 1440)

    def test_more_than_n_is_older_than_n(self):
        self.assertEqual(parse_age_days("Más de 30 días"), 31)
        self.assertEqual(parse_age_days("Hace +30 días"), 31)

    def test_text_without_a_date(self):
        self.assertIsNone(parse_age_days(""))
        self.assertIsNone(parse_age_days(None))
        self.assertIsNone(parse_age_days("fecha desconocida"))


class AgoTextTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def test_minutes_hours_and_days(self):
        self.assertEqual(ago_text(self.now - timedelta(minutes=5, seconds=10)), "Hace 5 minutos")
        self.assertEqual(ago_text(self.now - timedelta(hours=3, minutes=1)), "Hace 3 horas")
        self.assertEqual(ago_text(self.now - timedelta(days=1, hours=1)), "Hace 1 día")
        self.assertEqual(ago_text(self.now - timedelta(days=20, hours=1)), "Hace 20 días")

    def test_months_and_years_in_singular_and_plural(self):
        self.assertEqual(ago_text(self.now - timedelta(days=100)), "Hace 3 meses")
        self.assertEqual(ago_text(self.now - timedelta(days=370)), "Hace 1 año")
        self.assertEqual(ago_text(self.now - timedelta(days=800)), "Hace 2 años")

    def test_accepts_epoch_iso_and_datetime(self):
        past = self.now - timedelta(days=3, hours=1)
        self.assertEqual(ago_text(past.timestamp()), "Hace 3 días")
        self.assertEqual(ago_text(past.isoformat()), "Hace 3 días")
        self.assertEqual(ago_text(past.strftime("%Y-%m-%dT%H:%M:%S.000Z")), "Hace 3 días")
        self.assertEqual(ago_text(past), "Hace 3 días")

    def test_naive_datetime_is_treated_as_utc(self):
        naive = (self.now - timedelta(days=2, hours=1)).replace(tzinfo=None)
        self.assertEqual(ago_text(naive), "Hace 2 días")

    def test_future_dates_do_not_go_negative(self):
        self.assertEqual(ago_text(self.now + timedelta(days=5)), "Hace 1 minutos")

    def test_output_can_be_read_back(self):
        past = self.now - timedelta(days=3, hours=1)
        self.assertEqual(parse_age_days(ago_text(past)), 3)


if __name__ == "__main__":
    unittest.main()
