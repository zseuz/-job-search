import threading
import time
import unittest
from unittest import mock

from buscador_empleos.domain.repository import RepositoryError
from buscador_empleos.infrastructure.persistence.json_repository import JsonJobRepository
from buscador_empleos.services.search_service import SearchRequest, SearchService
from tests.support import make_job, temp_data_file


class FakeSource:
    """Fuente de mentira: registra con qué se la llamó y devuelve una oferta por búsqueda."""

    def __init__(self, name, *, behavior=None):
        self.name = name
        self.calls = []
        self._behavior = behavior

    def search(self, query, pages, log):
        self.calls.append((query, pages))
        if self._behavior:
            return self._behavior(query, pages, log)
        log(f"  {self.name}: leyendo")
        return [make_job(f"{self.name}-{query}", source=self.name, title=f"Desarrollador {query}")]


def wait_until_done(service, timeout=10):
    end = time.time() + timeout
    while service.status()["running"]:
        if time.time() > end:
            raise AssertionError("la búsqueda no terminó")
        time.sleep(0.01)


class SearchServiceTest(unittest.TestCase):
    def setUp(self):
        tmp = temp_data_file()
        self.path = tmp.__enter__()
        self.addCleanup(tmp.__exit__, None, None, None)
        self.repo = JsonJobRepository(self.path)
        self.a, self.b = FakeSource("A"), FakeSource("B")
        self.service = SearchService(self.repo, {"A": self.a, "B": self.b})

    def run_search(self, roles, sources, pages=2, expand=False):
        started = self.service.start(SearchRequest(tuple(roles), tuple(sources), pages, expand))
        wait_until_done(self.service)
        return started

    def test_runs_every_role_on_every_source_and_saves_the_results(self):
        self.assertTrue(self.run_search(["python", "java"], ["A", "B"], pages=3))
        self.assertEqual(self.a.calls, [("python", 3), ("java", 3)])
        self.assertEqual(self.b.calls, [("python", 3), ("java", 3)])
        self.assertEqual(len(self.repo.load().jobs), 4)

    def test_tags_each_offer_with_the_search_that_found_it(self):
        self.run_search(["python"], ["A"])
        self.assertEqual(self.repo.find("A:A-python").query, "python")  # type: ignore[union-attr]

    def test_progress_and_log(self):
        self.run_search(["python", "java"], ["A", "B"])
        status = self.service.status()
        self.assertEqual((status["done"], status["total"], status["running"]), (4, 4, False))
        self.assertIn("Buscando 'python' en A...", status["log"])
        self.assertIn("  A: leyendo", status["log"])
        self.assertTrue(status["log"][-1].startswith("Listo: 4 ofertas encontradas"))

    def test_a_failing_source_does_not_stop_the_others(self):
        def broken(query, pages, log):
            raise RuntimeError("se cayó")

        service = SearchService(self.repo, {"A": FakeSource("A", behavior=broken), "B": self.b})
        service.start(SearchRequest(("python",), ("A", "B")))
        wait_until_done(service)
        self.assertIn("  A: error se cayó", service.status()["log"])
        self.assertEqual([j.id for j in self.repo.load().jobs], ["B:B-python"])

    def test_ignores_unknown_sources_and_blank_roles(self):
        self.run_search(["  python  ", "   ", ""], ["A", "Inventada"], pages=1)
        self.assertEqual(self.a.calls, [("python", 1)])

    def test_expand_adds_related_roles(self):
        self.run_search(["desarrollador de software"], ["A"], pages=1, expand=True)
        searched = [query for query, _ in self.a.calls]
        self.assertEqual(searched[0], "desarrollador de software")
        self.assertIn("programador", searched)
        self.assertGreater(len(searched), 3)

    def test_without_expand_only_the_given_roles_are_searched(self):
        self.run_search(["desarrollador de software"], ["A"], pages=1)
        self.assertEqual([query for query, _ in self.a.calls], ["desarrollador de software"])

    def test_allows_only_one_search_at_a_time(self):
        gate = threading.Event()
        slow = FakeSource("A", behavior=lambda q, p, log: gate.wait(5) and [])
        service = SearchService(self.repo, {"A": slow})
        self.assertTrue(service.start(SearchRequest(("python",), ("A",))))
        self.assertTrue(service.status()["running"])
        self.assertFalse(service.start(SearchRequest(("java",), ("A",))))
        gate.set()
        wait_until_done(service)
        self.assertTrue(service.start(SearchRequest(("java",), ("A",))))  # ya terminó: otra vez se puede
        wait_until_done(service)

    def test_a_saving_error_is_reported_and_does_not_leave_the_service_locked(self):
        with mock.patch.object(self.repo, "merge", side_effect=RepositoryError("disco lleno")):
            self.run_search(["python"], ["A"])
        status = self.service.status()
        self.assertFalse(status["running"])
        self.assertIn("Error al guardar las ofertas: disco lleno", status["log"])
        self.assertTrue(self.run_search(["python"], ["A"]))  # se puede volver a intentar

    def test_lists_the_registered_sources(self):
        self.assertEqual(self.service.source_names, ["A", "B"])

    def test_status_returns_a_copy(self):
        status = self.service.status()
        status["running"] = True
        status["log"].append("x")
        self.assertEqual(self.service.status()["log"], [])
        self.assertFalse(self.service.status()["running"])

    def test_a_new_search_starts_with_a_clean_log(self):
        self.run_search(["python"], ["A"])
        first_log = self.service.status()["log"]
        self.run_search(["java"], ["A"])
        self.assertNotIn("Buscando 'python' en A...", self.service.status()["log"])
        self.assertTrue(first_log)


if __name__ == "__main__":
    unittest.main()
