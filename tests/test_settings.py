import unittest
from pathlib import Path

from buscador_empleos.domain.salary import DEFAULT_RATES
from buscador_empleos.settings import ConfigError, Settings


class SettingsDefaultsTest(unittest.TestCase):
    def test_defaults(self):
        settings = Settings()
        self.assertEqual(
            (settings.host, settings.port, settings.default_pages, settings.max_pages),
            ("127.0.0.1", 5000, 2, 5),
        )
        self.assertEqual(settings.data_file, Path("data") / "jobs.json")
        self.assertEqual(dict(settings.fx_rates), dict(DEFAULT_RATES))

    def test_is_immutable(self):
        with self.assertRaises(AttributeError):
            Settings().port = 1  # type: ignore[misc]

    def test_default_rates_are_not_shared_between_instances(self):
        first, second = Settings(), Settings()
        first.fx_rates["USD"] = 1  # type: ignore[index]
        self.assertEqual(second.fx_rates["USD"], DEFAULT_RATES["USD"])


class SettingsValidationTest(unittest.TestCase):
    def test_port_range(self):
        for port in (0, 70000, -1):
            with self.assertRaises(ConfigError):
                Settings(port=port)

    def test_pages(self):
        with self.assertRaises(ConfigError):
            Settings(max_pages=0)
        with self.assertRaises(ConfigError):
            Settings(default_pages=0)
        with self.assertRaises(ConfigError):
            Settings(default_pages=6, max_pages=5)

    def test_timeout(self):
        with self.assertRaises(ConfigError):
            Settings(http_timeout=0)


class SettingsFromEnvTest(unittest.TestCase):
    def test_empty_environment_gives_the_defaults(self):
        self.assertEqual(Settings.from_env({}), Settings())

    def test_reads_every_variable(self):
        settings = Settings.from_env(
            {
                "BUSCADOR_HOST": "0.0.0.0",
                "BUSCADOR_PORT": "8080",
                "BUSCADOR_DATA_FILE": "otra/ruta.json",
                "BUSCADOR_DEFAULT_PAGES": "3",
                "BUSCADOR_MAX_PAGES": "8",
                "BUSCADOR_HTTP_TIMEOUT": "12.5",
            }
        )
        self.assertEqual(
            (settings.host, settings.port, settings.default_pages, settings.max_pages, settings.http_timeout),
            ("0.0.0.0", 8080, 3, 8, 12.5),
        )
        self.assertEqual(settings.data_file, Path("otra/ruta.json"))

    def test_blank_values_are_ignored(self):
        self.assertEqual(Settings.from_env({"BUSCADOR_PORT": "  ", "BUSCADOR_HOST": ""}), Settings())

    def test_exchange_rates_override_only_the_given_currencies(self):
        rates = Settings.from_env({"BUSCADOR_FX": "usd=3900, EUR=4300"}).fx_rates
        self.assertEqual((rates["USD"], rates["EUR"], rates["MXN"]), (3900.0, 4300.0, DEFAULT_RATES["MXN"]))

    def test_invalid_numbers_are_reported_with_the_variable_name(self):
        with self.assertRaisesRegex(ConfigError, "BUSCADOR_PORT"):
            Settings.from_env({"BUSCADOR_PORT": "abc"})
        with self.assertRaisesRegex(ConfigError, "BUSCADOR_HTTP_TIMEOUT"):
            Settings.from_env({"BUSCADOR_HTTP_TIMEOUT": "rápido"})

    def test_invalid_exchange_rates(self):
        for raw in ("USD", "USD=abc", "=5"):
            with self.assertRaisesRegex(ConfigError, "BUSCADOR_FX"):
                Settings.from_env({"BUSCADOR_FX": raw})

    def test_values_are_validated_after_reading(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"BUSCADOR_PORT": "99999"})

    def test_reads_the_real_environment_by_default(self):
        from unittest import mock

        with mock.patch.dict("os.environ", {"BUSCADOR_PORT": "6001"}):
            self.assertEqual(Settings.from_env().port, 6001)


if __name__ == "__main__":
    unittest.main()
