import contextlib
import io
import unittest
from unittest import mock

from buscador_empleos import __version__, cli
from buscador_empleos.bootstrap import build_container
from buscador_empleos.infrastructure.persistence.json_repository import JsonJobRepository
from buscador_empleos.settings import Settings
from tests.services.test_search_service import FakeSource
from tests.support import temp_data_file


class CliTest(unittest.TestCase):
    def run_main(self, argv, env=None):
        """Ejecuta main() sin arrancar el servidor; devuelve (settings usados, código de salida)."""
        with (
            mock.patch.dict("os.environ", env or {}, clear=False),
            mock.patch.object(cli, "create_app") as create_app,
            mock.patch.object(cli, "configure_logging"),
        ):
            code = cli.main(argv)
        return create_app.call_args.args[0], create_app.return_value.run, code

    def test_starts_the_server_with_the_defaults(self):
        settings, run, code = self.run_main([])
        self.assertEqual(code, 0)
        run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False, threaded=True)
        self.assertEqual(settings, Settings())

    def test_command_line_options_override_the_environment(self):
        settings, run, _ = self.run_main(
            ["--host", "0.0.0.0", "--port", "8000", "--data-file", "x.json", "--debug"],
            env={"BUSCADOR_PORT": "7000"},
        )
        self.assertEqual(
            (settings.host, settings.port, str(settings.data_file), settings.debug),
            ("0.0.0.0", 8000, "x.json", True),
        )
        self.assertEqual(run.call_args.kwargs["port"], 8000)

    def test_environment_is_used_when_no_option_is_given(self):
        settings, _, _ = self.run_main([], env={"BUSCADOR_PORT": "7000"})
        self.assertEqual(settings.port, 7000)

    def test_invalid_configuration_exits_with_code_2_and_a_clear_message(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            self.run_main(["--port", "99999"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("puerto", stderr.getvalue())

    def test_invalid_environment_also_exits_with_code_2(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.run_main([], env={"BUSCADOR_MAX_PAGES": "muchas"})
        self.assertEqual(caught.exception.code, 2)

    def test_version(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as caught:
            cli.main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn(__version__, stdout.getvalue())

    def test_logging_configuration(self):
        import logging

        with mock.patch("logging.basicConfig") as basic:
            cli.configure_logging(debug=True)
        self.assertEqual(basic.call_args.kwargs["level"], logging.DEBUG)
        with mock.patch("logging.basicConfig") as basic:
            cli.configure_logging(debug=False)
        self.assertEqual(basic.call_args.kwargs["level"], logging.INFO)


class BootstrapTest(unittest.TestCase):
    def test_wires_the_services_with_the_given_sources(self):
        with temp_data_file() as path:
            sources = {"X": FakeSource("X")}
            container = build_container(Settings(data_file=path), sources=sources)
            self.assertIsInstance(container.repository, JsonJobRepository)
            self.assertEqual(container.search_service.source_names, ["X"])
            self.assertEqual(container.job_service.list_jobs().items, [])

    def test_builds_the_real_sources_by_default_with_the_configured_rates(self):
        with temp_data_file() as path:
            container = build_container(Settings(data_file=path, fx_rates={"USD": 1}))
            self.assertEqual(container.search_service.source_names[0], "Computrabajo")
            self.assertEqual(len(container.search_service.source_names), 7)

    def test_accepts_a_custom_repository(self):
        repository = mock.Mock()
        container = build_container(Settings(), repository=repository, sources={})
        self.assertIs(container.repository, repository)


if __name__ == "__main__":
    unittest.main()
