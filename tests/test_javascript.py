"""Ejecuta las pruebas de JavaScript (tests/js) con el ejecutor de Node, si Node está instalado."""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js no está instalado: se omiten las pruebas de JavaScript")
class JavascriptTest(unittest.TestCase):
    def test_node_test_runner_passes(self):
        files = sorted(str(path) for path in (ROOT / "tests" / "js").glob("*.test.mjs"))
        self.assertTrue(files, "no se encontraron pruebas de JavaScript")
        result = subprocess.run(
            ["node", "--test", *files],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
