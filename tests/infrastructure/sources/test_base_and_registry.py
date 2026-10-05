import unittest

from buscador_empleos.domain.job import Job
from buscador_empleos.infrastructure.http import ChromeClient, RequestsClient
from buscador_empleos.infrastructure.sources import build_sources
from buscador_empleos.infrastructure.sources.base import JobSource, is_open_to_colombia, random_pause
from tests.support import FakeHttpClient, no_pause


class IsOpenToColombiaTest(unittest.TestCase):
    def test_without_restrictions(self):
        self.assertTrue(is_open_to_colombia(None))
        self.assertTrue(is_open_to_colombia([]))
        self.assertTrue(is_open_to_colombia(""))

    def test_restrictions_that_include_colombia_or_the_region(self):
        for restriction in (
            ["LATAM", "USA"],
            "Remoto: México, Colombia",
            ["Worldwide"],
            "Anywhere in the World",
        ):
            self.assertTrue(is_open_to_colombia(restriction), restriction)

    def test_restrictions_that_exclude_it(self):
        self.assertFalse(is_open_to_colombia(["United States"]))
        self.assertFalse(is_open_to_colombia("Remoto: Estados Unidos"))


class JobSourceContractTest(unittest.TestCase):
    def test_a_source_cannot_be_built_without_implementing_search(self):
        class Incomplete(JobSource):
            name = "Incompleta"

        with self.assertRaises(TypeError):
            Incomplete(FakeHttpClient())  # type: ignore[abstract]

    def test_a_minimal_source_works_and_logs_by_default(self):
        class Minimal(JobSource):
            name = "Mínima"

            def search(self, query, pages, log=print):
                return [Job.create(source=self.name, source_id="1", title=query)]

        self.assertEqual(Minimal(FakeHttpClient()).search("dev", 1)[0].id, "Mínima:1")

    def test_helpers_raise_on_http_errors_and_return_good_responses(self):
        from buscador_empleos.infrastructure.http import HttpStatusError

        http = FakeHttpClient().when("/ok", text="bien").when("/mal", status=503)

        class Probe(JobSource):
            name = "Probe"

            def search(self, query, pages, log=print):
                return []

        probe = Probe(http, pause=no_pause)
        self.assertEqual(probe._get("https://x/ok").text, "bien")
        with self.assertRaises(HttpStatusError):
            probe._get("https://x/mal")
        with self.assertRaises(HttpStatusError):
            probe._post_json("https://x/mal", {})

    def test_map_parallel_keeps_the_order(self):
        self.assertEqual(JobSource._map_parallel(lambda n: n * 2, range(6)), [0, 2, 4, 6, 8, 10])

    def test_random_pause_sleeps_within_the_range(self):
        from unittest import mock

        with mock.patch("time.sleep") as sleep:
            random_pause(0.5, 0.6)
        self.assertTrue(0.5 <= sleep.call_args.args[0] <= 0.6)


class BuildSourcesTest(unittest.TestCase):
    def test_builds_every_source_in_display_order(self):
        sources = build_sources(http=FakeHttpClient(), chrome=FakeHttpClient())
        self.assertEqual(
            list(sources),
            ["Computrabajo", "elempleo", "Hireline", "Get on Board", "Torre", "LinkedIn", "Indeed"],
        )
        self.assertTrue(all(name == source.name for name, source in sources.items()))

    def test_default_clients_are_created_when_none_are_given(self):
        sources = build_sources()
        self.assertIsInstance(sources["Computrabajo"]._http, RequestsClient)
        self.assertIsInstance(sources["Indeed"]._http, ChromeClient)
        self.assertIsInstance(sources["Hireline"]._http, ChromeClient)

    def test_cloudflare_protected_sources_use_the_browser_client(self):
        plain, chrome = FakeHttpClient(), FakeHttpClient()
        sources = build_sources(http=plain, chrome=chrome)
        self.assertIs(sources["Indeed"]._http, chrome)
        self.assertIs(sources["Hireline"]._http, chrome)
        self.assertIs(sources["Torre"]._http, plain)

    def test_rates_and_pause_reach_the_sources(self):
        rates = {"USD": 1}
        sources = build_sources(http=FakeHttpClient(), chrome=FakeHttpClient(), rates=rates, pause=no_pause)
        self.assertTrue(all(s._rates is rates and s._pause is no_pause for s in sources.values()))


if __name__ == "__main__":
    unittest.main()
