import sys
import types
import unittest
from unittest import mock

from buscador_empleos.infrastructure.http import (
    DEFAULT_HEADERS,
    JSON_HEADERS,
    ChromeClient,
    HttpStatusError,
    RequestsClient,
    ensure_ok,
)
from tests.support import FakeResponse


class EnsureOkTest(unittest.TestCase):
    def test_passes_good_responses_through(self):
        response = FakeResponse("ok", 200)
        self.assertIs(ensure_ok(response, "https://x"), response)

    def test_raises_with_status_and_url_on_4xx_and_5xx(self):
        for status in (400, 403, 404, 429, 500):
            with self.assertRaises(HttpStatusError) as caught:
                ensure_ok(FakeResponse("", status), "https://x/y")
            self.assertEqual(caught.exception.status_code, status)
            self.assertIn("https://x/y", str(caught.exception))


class RequestsClientTest(unittest.TestCase):
    def test_get_merges_default_and_given_headers_and_uses_the_timeout(self):
        with mock.patch("requests.get", return_value=FakeResponse("hola")) as get:
            response = RequestsClient(timeout=7).get(
                "https://x", params={"a": 1}, headers={"Accept": "application/json"}
            )
        self.assertEqual(response.text, "hola")
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(kwargs["params"], {"a": 1})
        self.assertEqual(kwargs["headers"]["Accept"], "application/json")
        self.assertEqual(kwargs["headers"]["User-Agent"], DEFAULT_HEADERS["User-Agent"])

    def test_post_json_sends_the_body_as_json(self):
        with mock.patch("requests.post", return_value=FakeResponse("{}")) as post:
            RequestsClient().post_json("https://x", {"q": 1}, params={"size": 5})
        self.assertEqual(post.call_args.kwargs["json"], {"q": 1})
        self.assertEqual(post.call_args.kwargs["params"], {"size": 5})

    def test_json_headers_ask_for_json(self):
        self.assertEqual(JSON_HEADERS["Accept"], "application/json")
        self.assertIn("User-Agent", JSON_HEADERS)


class ChromeClientTest(unittest.TestCase):
    """curl_cffi se sustituye por un módulo falso: no hace falta tenerlo instalado para probar."""

    def setUp(self):
        self.curl = types.SimpleNamespace(
            get=mock.Mock(return_value=FakeResponse("ok")), post=mock.Mock(return_value=FakeResponse("ok"))
        )
        package = types.ModuleType("curl_cffi")
        package.requests = self.curl  # type: ignore[attr-defined]
        patcher = mock.patch.dict(sys.modules, {"curl_cffi": package, "curl_cffi.requests": self.curl})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_impersonates_chrome(self):
        ChromeClient(timeout=9).get("https://x", params={"q": "a"})
        kwargs = self.curl.get.call_args.kwargs
        self.assertEqual(
            (kwargs["impersonate"], kwargs["timeout"], kwargs["params"]), ("chrome", 9, {"q": "a"})
        )

    def test_post_json_impersonates_chrome(self):
        ChromeClient().post_json("https://x", {"a": 1})
        kwargs = self.curl.post.call_args.kwargs
        self.assertEqual((kwargs["impersonate"], kwargs["json"]), ("chrome", {"a": 1}))


if __name__ == "__main__":
    unittest.main()
