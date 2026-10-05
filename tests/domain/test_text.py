import unittest

from buscador_empleos.domain.text import clean, clean_text, slug, strip_accents


class CleanTest(unittest.TestCase):
    def test_collapses_any_whitespace(self):
        self.assertEqual(clean("  Hola \n\n  mundo\t!  "), "Hola mundo !")

    def test_handles_none(self):
        self.assertEqual(clean(None), "")

    def test_clean_text_keeps_paragraphs(self):
        self.assertEqual(clean_text("Uno  dos\r\n\r\n\r\n\r\nTres \n  cuatro"), "Uno dos\n\nTres\ncuatro")

    def test_clean_text_replaces_non_breaking_space(self):
        self.assertEqual(clean_text("a\xa0b"), "a b")


class AccentsAndSlugTest(unittest.TestCase):
    def test_strip_accents(self):
        self.assertEqual(strip_accents("Canción de año, ¿qué tal? ü"), "Cancion de ano, ¿que tal? u")

    def test_slug(self):
        self.assertEqual(slug("Analista de Datos"), "analista-de-datos")
        self.assertEqual(slug("Ingeniería  de Sistemas!"), "ingenieria-de-sistemas")
        self.assertEqual(slug("Diseñador"), "disenador")
        self.assertEqual(slug("  --C# / .NET--  "), "c-net")

    def test_slug_of_nothing(self):
        self.assertEqual(slug("¡¿?!"), "")


if __name__ == "__main__":
    unittest.main()
