import unittest
from datetime import datetime, timedelta

from buscador_empleos.infrastructure.persistence.json_repository import JsonJobRepository
from buscador_empleos.services.job_service import JobNotFoundError, JobService
from tests.support import make_job, temp_data_file


class JobServiceTest(unittest.TestCase):
    def setUp(self):
        tmp = temp_data_file()
        self.repo = JsonJobRepository(tmp.__enter__())
        self.addCleanup(tmp.__exit__, None, None, None)
        self.service = JobService(self.repo)

    def test_empty_listing(self):
        listing = self.service.list_jobs()
        self.assertEqual((listing.updated, listing.items), (None, []))

    def test_lists_offers_with_their_age_at_the_given_moment(self):
        job = make_job("1", posted="Hace 3 días")
        job.scraped_at = "2026-10-01T10:00"
        self.repo.merge([job])
        now = datetime(2026, 10, 2, 10, 0)
        (view,) = self.service.list_jobs(now=now).items
        self.assertEqual(view.job.id, "Fuente:1")
        self.assertEqual(view.days_ago, 4)

    def test_an_offer_without_a_date_has_no_age(self):
        self.repo.merge([make_job("1", posted="")])
        self.assertIsNone(self.service.list_jobs().items[0].days_ago)

    def test_age_uses_the_repository_update_date_when_the_offer_has_no_read_date(self):
        job = make_job("1", posted="Hace 1 día")
        job.scraped_at = ""
        self.repo.merge([job])
        updated = self.repo.load().updated
        later = datetime.fromisoformat(updated) + timedelta(days=2)  # type: ignore[arg-type]
        self.assertAlmostEqual(self.service.list_jobs(now=later).items[0].days_ago or 0, 3, delta=0.1)

    def test_get_job(self):
        self.repo.merge([make_job("1")])
        self.assertEqual(self.service.get_job("Fuente:1").id, "Fuente:1")

    def test_get_job_that_does_not_exist(self):
        with self.assertRaises(JobNotFoundError):
            self.service.get_job("Fuente:999")


if __name__ == "__main__":
    unittest.main()
