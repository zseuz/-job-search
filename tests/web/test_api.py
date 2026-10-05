import threading
import time
from unittest import mock

from buscador_empleos.domain.repository import RepositoryError
from buscador_empleos.services.search_service import SearchRequest
from tests.services.test_search_service import FakeSource
from tests.support import make_job
from tests.web.base import WebTestCase


class HealthTest(WebTestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/api/health").get_json(), {"status": "ok", "version": "1.0.0"})


class JobsListTest(WebTestCase):
    def test_empty_list(self):
        self.assertEqual(self.client.get("/api/jobs").get_json(), {"updated": None, "jobs": []})

    def test_the_list_has_no_descriptions_but_flags_them(self):
        self.repo.merge([make_job("1", description="Python y SQL. " * 20), make_job("2", description="")])
        data = self.client.get("/api/jobs").get_json()
        self.assertTrue(data["updated"])
        by_id = {job["id"]: job for job in data["jobs"]}
        self.assertNotIn("description", by_id["Fuente:1"])
        self.assertTrue(by_id["Fuente:1"]["has_description"])
        self.assertFalse(by_id["Fuente:2"]["has_description"])

    def test_the_list_includes_the_days_since_publication(self):
        self.repo.merge([make_job("1", posted="Hace 3 días"), make_job("2", posted="")])
        by_id = {job["id"]: job for job in self.client.get("/api/jobs").get_json()["jobs"]}
        self.assertAlmostEqual(by_id["Fuente:1"]["days_ago"], 3, delta=0.1)
        self.assertIsNone(by_id["Fuente:2"]["days_ago"])

    def test_the_contract_with_the_browser(self):
        """El JavaScript depende de estos campos: si cambian, hay que cambiar también filters.js/render.js."""
        self.repo.merge([make_job("1")])
        job = self.client.get("/api/jobs").get_json()["jobs"][0]
        expected = {
            "id",
            "source",
            "title",
            "company",
            "location",
            "url",
            "posted",
            "age_days",
            "scraped_at",
            "modality",
            "salary_text",
            "salary_min",
            "contract",
            "techs",
            "roles",
            "query",
            "has_description",
            "days_ago",
        }
        self.assertEqual(set(job), expected)

    def test_accents_are_not_escaped(self):
        self.repo.merge([make_job("1", title="Analista de datos – Bogotá")])
        self.assertIn("Bogotá".encode(), self.client.get("/api/jobs").data)

    def test_a_storage_failure_is_a_json_500(self):
        with mock.patch.object(self.repo, "load", side_effect=RepositoryError("archivo dañado")):
            res = self.client.get("/api/jobs")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.get_json(), {"error": "archivo dañado"})


class JobDescriptionTest(WebTestCase):
    def test_returns_the_full_description(self):
        text = "Experiencia en Java y Angular. " * 10
        self.repo.merge([make_job("1", description=text)])
        res = self.client.get("/api/jobs/Fuente:1/description")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.get_json(), {"id": "Fuente:1", "title": "Desarrollador Python", "description": text}
        )

    def test_the_id_can_be_url_encoded(self):
        self.repo.merge([make_job("1")])
        self.assertEqual(self.client.get("/api/jobs/Fuente%3A1/description").status_code, 200)

    def test_unknown_offer_is_404(self):
        res = self.client.get("/api/jobs/Fuente:999/description")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json(), {"error": "Oferta no encontrada"})


class SearchTest(WebTestCase):
    def test_passes_the_validated_request_to_the_service(self):
        with mock.patch.object(self.search_service, "start", return_value=True) as start:
            res = self.client.post(
                "/api/search", json={"roles": [" python "], "sources": ["Falsa"], "pages": 3, "expand": True}
            )
        self.assertEqual((res.status_code, res.get_json()), (202, {"ok": True}))
        start.assert_called_once_with(SearchRequest(("python",), ("Falsa",), 3, True))

    def test_default_pages_come_from_the_settings(self):
        with mock.patch.object(self.search_service, "start", return_value=True) as start:
            self.client.post("/api/search", json={"roles": ["a"], "sources": ["Falsa"]})
        self.assertEqual(start.call_args.args[0].pages, self.settings.default_pages)

    def test_pages_are_limited_to_the_allowed_range(self):
        with mock.patch.object(self.search_service, "start", return_value=True) as start:
            self.client.post("/api/search", json={"roles": ["a"], "sources": ["Falsa"], "pages": 999})
            self.client.post("/api/search", json={"roles": ["a"], "sources": ["Falsa"], "pages": 0})
        self.assertEqual([c.args[0].pages for c in start.call_args_list], [self.settings.max_pages, 1])

    def test_invalid_requests_are_400_with_a_message(self):
        cases = {
            "no es json": "debe ser un objeto JSON",
            "[]": "debe ser un objeto JSON",
        }
        for body, message in cases.items():
            res = self.client.post("/api/search", data=body, content_type="application/json")
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(message, res.get_json()["error"])
        for payload, message in (
            ({}, "al menos un cargo"),
            ({"roles": ["a"]}, "al menos una fuente"),
            ({"roles": ["   "], "sources": ["Falsa"]}, "al menos un cargo"),
            ({"roles": "python", "sources": ["Falsa"]}, "lista de textos"),
            ({"roles": ["a"], "sources": ["Falsa"], "pages": "dos"}, "número entero"),
            ({"roles": ["a"], "sources": ["Falsa"], "expand": "si"}, "verdadero o falso"),
        ):
            res = self.client.post("/api/search", json=payload)
            self.assertEqual(res.status_code, 400, payload)
            self.assertIn(message, res.get_json()["error"], payload)

    def test_conflict_when_a_search_is_already_running(self):
        with mock.patch.object(self.search_service, "start", return_value=False):
            res = self.client.post("/api/search", json={"roles": ["a"], "sources": ["Falsa"]})
        self.assertEqual(res.status_code, 409)
        self.assertIn("en curso", res.get_json()["error"])

    def test_status(self):
        self.assertEqual(
            self.client.get("/api/status").get_json(), {"running": False, "log": [], "done": 0, "total": 0}
        )

    def test_unknown_api_routes_and_methods_answer_in_json(self):
        not_found = self.client.get("/api/nada")
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(not_found.get_json(), {"error": "Recurso no encontrado"})
        wrong_method = self.client.get("/api/search")
        self.assertEqual(wrong_method.status_code, 405)
        self.assertEqual(wrong_method.get_json(), {"error": "Método no permitido"})


class FullFlowTest(WebTestCase):
    def setUp(self):
        self.gate = threading.Event()
        self.sources = {"Falsa": FakeSource("Falsa", behavior=self.slow_search)}
        super().setUp()

    def slow_search(self, query, pages, log):
        self.gate.wait(5)
        return [make_job("x", source="Falsa", title=f"Desarrollador {query}")]

    def test_search_then_follow_progress_then_list(self):
        post = lambda body: self.client.post("/api/search", json=body)  # noqa: E731
        self.assertEqual(post({"roles": ["python"], "sources": ["Falsa"]}).status_code, 202)
        self.assertTrue(self.client.get("/api/status").get_json()["running"])
        self.assertEqual(post({"roles": ["java"], "sources": ["Falsa"]}).status_code, 409)
        self.gate.set()
        deadline = time.time() + 10
        while self.client.get("/api/status").get_json()["running"]:
            self.assertLess(time.time(), deadline)
            time.sleep(0.01)
        jobs = self.client.get("/api/jobs").get_json()["jobs"]
        self.assertEqual([j["title"] for j in jobs], ["Desarrollador python"])
        self.assertEqual(jobs[0]["query"], "python")
