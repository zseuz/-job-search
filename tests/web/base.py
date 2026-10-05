"""Base de las pruebas web: una aplicación completa con fuentes y almacenamiento de mentira."""

import unittest

from buscador_empleos.bootstrap import build_container
from buscador_empleos.settings import Settings
from buscador_empleos.web import create_app
from tests.services.test_search_service import FakeSource
from tests.support import temp_data_file


class WebTestCase(unittest.TestCase):
    sources = None  # las subclases pueden definir otras fuentes de mentira

    def setUp(self):
        tmp = temp_data_file()
        self.path = tmp.__enter__()
        self.addCleanup(tmp.__exit__, None, None, None)
        self.settings = Settings(data_file=self.path)
        sources = (
            self.sources
            if self.sources is not None
            else {"Falsa": FakeSource("Falsa"), "Otra": FakeSource("Otra")}
        )
        self.container = build_container(self.settings, sources=sources)
        self.app = create_app(self.settings, container=self.container)
        self.client = self.app.test_client()
        self.repo = self.container.repository
        self.search_service = self.container.search_service
