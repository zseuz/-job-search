"""Reglas de arquitectura: las capas solo pueden depender de las que están por debajo.

    web  ->  services  ->  domain  <-  infrastructure

* ``domain`` no importa nada del proyecto fuera de sí mismo ni bibliotecas de terceros.
* ``services`` conoce el dominio y los puertos, pero no Flask ni los detalles de la web.
* ``infrastructure`` implementa los puertos; no conoce ``services`` ni ``web``.
* ``web`` es la única capa que importa Flask.
"""

import ast
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "buscador_empleos"
ROOT = "buscador_empleos"

# capa -> prefijos de módulos internos que PUEDE importar (además de sí misma)
ALLOWED_INTERNAL = {
    "domain": set(),
    "infrastructure": {"domain"},
    "services": {"domain", "infrastructure.sources"},  # recibe las fuentes por inyección; solo su interfaz
    "web": {"domain", "services", "settings", "bootstrap"},
}
FORBIDDEN_THIRD_PARTY = {
    "domain": {"flask", "requests", "bs4", "curl_cffi", "werkzeug", "jinja2"},
    "services": {"flask", "requests", "bs4", "curl_cffi", "werkzeug", "jinja2"},
    "infrastructure": {"flask", "werkzeug", "jinja2"},
}
STDLIB = sys.stdlib_module_names


def imports_of(path):
    """Módulos importados por un archivo, como nombres completos ('buscador_empleos.domain.job')."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module)
    return found


def modules_in(layer):
    return sorted((PACKAGE / layer).rglob("*.py"))


class LayerDependenciesTest(unittest.TestCase):
    def test_each_layer_only_imports_what_it_is_allowed_to(self):
        violations = []
        for layer, allowed in ALLOWED_INTERNAL.items():
            for path in modules_in(layer):
                for module in imports_of(path):
                    if not module.startswith(ROOT + "."):
                        continue
                    inner = module[len(ROOT) + 1 :]
                    own_layer = inner.split(".")[0] == layer
                    if not own_layer and not any(inner == a or inner.startswith(a + ".") for a in allowed):
                        violations.append(f"{path.relative_to(PACKAGE)} importa {module}")
        self.assertEqual(violations, [], "\n".join(violations))

    def test_layers_do_not_use_forbidden_third_party_libraries(self):
        violations = []
        for layer, forbidden in FORBIDDEN_THIRD_PARTY.items():
            for path in modules_in(layer):
                for module in imports_of(path):
                    if module.split(".")[0] in forbidden:
                        violations.append(f"{path.relative_to(PACKAGE)} importa {module}")
        self.assertEqual(violations, [], "\n".join(violations))

    def test_the_domain_uses_only_the_standard_library(self):
        violations = []
        for path in modules_in("domain"):
            for module in imports_of(path):
                top = module.split(".")[0]
                if top != ROOT and top not in STDLIB and top != "__future__":
                    violations.append(f"{path.relative_to(PACKAGE)} importa {module}")
        self.assertEqual(violations, [], "\n".join(violations))

    def test_only_the_web_layer_imports_flask(self):
        offenders = [
            str(path.relative_to(PACKAGE))
            for path in PACKAGE.rglob("*.py")
            if "web" not in path.relative_to(PACKAGE).parts
            and any(m.split(".")[0] == "flask" for m in imports_of(path))
        ]
        self.assertEqual(offenders, [])

    def test_no_module_prints_to_the_console(self):
        """Los mensajes pasan por ``logging`` o por el registro que ve el usuario, nunca por print()."""
        offenders = []
        for path in PACKAGE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                    offenders.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
