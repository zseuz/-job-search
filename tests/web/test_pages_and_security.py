import json
import re

from buscador_empleos.bootstrap import build_container
from buscador_empleos.domain.catalog import TECH_GROUPS
from buscador_empleos.settings import Settings
from buscador_empleos.web import create_app
from tests.web.base import WebTestCase


class HomePageTest(WebTestCase):
    def setUp(self):
        super().setUp()
        self.html = self.client.get("/").get_data(as_text=True)

    def test_serves_the_page(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertIn("<title>Buscador de empleos</title>", self.html)

    def test_every_source_has_a_search_checkbox_and_a_filter_checkbox(self):
        for source in ("Falsa", "Otra"):
            self.assertIn(f'class="search-source" value="{source}"', self.html)
            self.assertIn(f'class="filter-source" value="{source}"', self.html)

    def test_modalities_and_role_kinds_come_from_the_domain(self):
        for text in (
            "Remoto",
            "Híbrido",
            "Presencial",
            "No indicado",
            "Analista de datos",
            "Desarrollador",
            "Otros",
        ):
            self.assertIn(text, self.html)

    def test_tech_groups_are_delivered_once_as_json(self):
        boot = re.search(r'<script type="application/json" id="boot-data">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(boot)
        self.assertEqual(
            json.loads(boot.group(1))["techGroups"], {g: list(t) for g, t in TECH_GROUPS.items()}
        )

    def test_loads_the_script_as_an_es_module_and_has_no_inline_scripts_or_styles(self):
        self.assertIn('<script type="module" src="/static/js/main.js">', self.html)
        self.assertNotIn(" style=", self.html)
        self.assertNotIn("onclick=", self.html)

    def test_page_options_follow_the_settings(self):
        settings = Settings(data_file=self.path, default_pages=3, max_pages=4)
        app = create_app(settings, container=build_container(settings, sources={}))
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertRegex(html, r'<option value="3" selected>')
        self.assertIn('<option value="4">4 (máximo', html)
        self.assertNotIn('<option value="5"', html)

    def test_declares_an_icon_so_the_browser_does_not_ask_for_favicon_ico(self):
        self.assertIn('<link rel="icon" href="data:,">', self.html)

    def test_static_assets(self):
        for path in ("/static/js/main.js", "/static/js/filters.js", "/static/css/styles.css"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, path)
            res.close()

    def test_unknown_page_is_a_normal_html_404(self):
        res = self.client.get("/no-existe")
        self.assertEqual(res.status_code, 404)
        self.assertIn("text/html", res.content_type)


class SecurityHeadersTest(WebTestCase):
    def test_every_response_carries_the_security_headers(self):
        for path in ("/", "/api/health", "/no-existe"):
            headers = self.client.get(path).headers
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff", path)
            self.assertEqual(headers["X-Frame-Options"], "DENY", path)
            self.assertEqual(headers["Referrer-Policy"], "no-referrer", path)
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"], path)

    def test_the_policy_forbids_framing_and_plugins(self):
        policy = self.client.get("/").headers["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("object-src 'none'", policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertNotIn("unsafe-eval", policy)
