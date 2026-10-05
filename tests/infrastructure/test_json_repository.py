import json
import threading
import unittest
from unittest import mock

from buscador_empleos.domain.catalog import CATALOG_VERSION
from buscador_empleos.domain.repository import MergeResult, RepositoryError, Snapshot
from buscador_empleos.infrastructure.persistence.json_repository import JsonJobRepository
from tests.support import make_job, temp_data_file


class LoadTest(unittest.TestCase):
    def test_missing_file_gives_an_empty_snapshot(self):
        with temp_data_file() as path:
            self.assertEqual(JsonJobRepository(path).load(), Snapshot(None, []))

    def test_save_and_load_roundtrip_between_instances(self):
        with temp_data_file() as path:
            JsonJobRepository(path).merge([make_job("1"), make_job("2", title="Data Analyst")])
            updated, jobs = JsonJobRepository(path).load()
            self.assertTrue(updated)
            self.assertEqual({j.id for j in jobs}, {"Fuente:1", "Fuente:2"})

    def test_creates_missing_folders(self):
        with temp_data_file() as path:
            self.assertFalse(path.parent.exists())
            JsonJobRepository(path).merge([make_job()])
            self.assertTrue(path.exists())

    def test_find(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1"), make_job("2")])
            self.assertEqual(repo.find("Fuente:2").id, "Fuente:2")  # type: ignore[union-attr]
            self.assertIsNone(repo.find("no-existe"))


class MergeTest(unittest.TestCase):
    def test_returns_received_and_total_counts(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            self.assertEqual(repo.merge([make_job("1"), make_job("2")]), MergeResult(2, 2))
            self.assertEqual(repo.merge([make_job("2"), make_job("3")]), (2, 3))

    def test_a_newer_version_replaces_the_older(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1", posted="Hace 10 días")])
            repo.merge([make_job("1", posted="Hace 1 día")])
            self.assertEqual(repo.find("Fuente:1").posted, "Hace 1 día")  # type: ignore[union-attr]

    def test_does_not_replace_a_good_description_with_an_empty_one(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1", description="Python y SQL. " * 20)])
            repo.merge([make_job("1", description="")])  # p. ej. la fuente respondió 429
            job = repo.find("Fuente:1")
            self.assertTrue(job.has_description())  # type: ignore[union-attr]
            self.assertIn("Python", job.techs)  # type: ignore[union-attr]

    def test_a_good_description_does_replace_an_empty_one(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1", description="")])
            repo.merge([make_job("1", description="Java y Angular. " * 20)])
            self.assertIn("Java", repo.find("Fuente:1").techs)  # type: ignore[union-attr]

    def test_keeps_offers_that_were_not_found_this_time(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1"), make_job("2")])
            repo.merge([make_job("3")])
            self.assertEqual(len(repo.load().jobs), 3)

    def test_concurrent_merges_do_not_lose_offers(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            threads = [threading.Thread(target=repo.merge, args=([make_job(str(n))],)) for n in range(12)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(len(repo.load().jobs), 12)


class CacheTest(unittest.TestCase):
    def test_reuses_the_cache_while_the_file_does_not_change(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job()])
            self.assertIs(repo.load(), repo.load())

    def test_notices_changes_made_by_someone_else(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1")])
            self.assertEqual(len(repo.load().jobs), 1)
            JsonJobRepository(path).merge([make_job("2")])
            self.assertEqual(len(repo.load().jobs), 2)


class CatalogVersionTest(unittest.TestCase):
    def test_an_old_catalog_triggers_a_one_time_reclassification(self):
        with temp_data_file() as path:
            JsonJobRepository(path).merge([make_job("1", title="Desarrollador", description="Python " * 30)])
            data = json.loads(path.read_text(encoding="utf-8"))
            data["catalog"] = CATALOG_VERSION - 1
            data["jobs"][0]["techs"], data["jobs"][0]["roles"] = [], []
            path.write_text(json.dumps(data), encoding="utf-8")

            _, jobs = JsonJobRepository(path).load()
            self.assertIn("Python", jobs[0].techs)
            self.assertEqual(jobs[0].roles, ["Desarrollador"])
            rewritten = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(rewritten["catalog"], CATALOG_VERSION)  # no se vuelve a recalcular
            self.assertEqual(rewritten["updated"], data["updated"])  # conserva la fecha de actualización

    def test_a_current_catalog_trusts_the_stored_values(self):
        with temp_data_file() as path:
            JsonJobRepository(path).merge([make_job("1")])
            data = json.loads(path.read_text(encoding="utf-8"))
            data["jobs"][0]["techs"] = ["Marca"]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(JsonJobRepository(path).load().jobs[0].techs, ["Marca"])


class FailureTest(unittest.TestCase):
    def test_a_corrupted_file_is_reported_clearly(self):
        with temp_data_file() as path:
            path.parent.mkdir(parents=True)
            path.write_text("{no es json", encoding="utf-8")
            with self.assertRaisesRegex(RepositoryError, "No se pudo leer"):
                JsonJobRepository(path).load()

    def test_unexpected_structure_is_reported(self):
        with temp_data_file() as path:
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(["no", "es", "un", "objeto"]), encoding="utf-8")
            with self.assertRaisesRegex(RepositoryError, "Formato inesperado"):
                JsonJobRepository(path).load()

    def test_invalid_stored_offers_are_skipped_but_the_rest_survive(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1")])
            data = json.loads(path.read_text(encoding="utf-8"))
            data["jobs"].append({"title": "sin id ni fuente"})
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertLogs("buscador_empleos.infrastructure.persistence.json_repository", "WARNING"):
                jobs = JsonJobRepository(path).load().jobs
            self.assertEqual([j.id for j in jobs], ["Fuente:1"])

    def test_write_failure_is_reported_and_leaves_the_previous_file_intact(self):
        with temp_data_file() as path:
            repo = JsonJobRepository(path)
            repo.merge([make_job("1")])
            before = path.read_text(encoding="utf-8")
            with (
                mock.patch("os.replace", side_effect=OSError("disco lleno")),
                self.assertRaisesRegex(RepositoryError, "No se pudo guardar"),
            ):
                repo.merge([make_job("2")])
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_writes_are_atomic_no_temporary_file_is_left_behind(self):
        with temp_data_file() as path:
            JsonJobRepository(path).merge([make_job()])
            self.assertEqual([p.name for p in path.parent.iterdir()], ["jobs.json"])


if __name__ == "__main__":
    unittest.main()
