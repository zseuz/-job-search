import unittest

from buscador_empleos.infrastructure.html import attr, html_to_text, paragraphs_of, parse_html, text_of


class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.soup = parse_html(
            '<div id="a" class="x y" data-n="5"><p>Hola   <b>mundo</b></p><p>Segundo</p></div>'
        )

    def test_text_of_collapses_whitespace(self):
        self.assertEqual(text_of(self.soup.select_one("p")), "Hola mundo")

    def test_text_of_missing_node(self):
        self.assertEqual(text_of(None), "")
        self.assertEqual(text_of(self.soup.select_one(".no-existe")), "")

    def test_paragraphs_keep_line_breaks(self):
        self.assertEqual(paragraphs_of(self.soup.select_one("div")), "Hola\nmundo\nSegundo")
        self.assertEqual(paragraphs_of(None), "")

    def test_attr_returns_strings_even_for_multivalued_attributes(self):
        div = self.soup.select_one("div")
        self.assertEqual(attr(div, "data-n"), "5")
        self.assertEqual(attr(div, "class"), "x y")  # bs4 lo entrega como lista
        self.assertEqual(attr(div, "inexistente"), "")
        self.assertEqual(attr(None, "id"), "")


class HtmlToTextTest(unittest.TestCase):
    def test_paragraphs_lists_and_breaks(self):
        html = "<p>Hola<br>mundo</p><ul><li>Uno</li><li>Dos</li></ul><h3>Fin</h3>x"
        self.assertEqual(html_to_text(html), "Hola\nmundo\n• Uno\n• Dos\n\nFin\nx")

    def test_empty_input(self):
        self.assertEqual(html_to_text(""), "")
        self.assertEqual(html_to_text(None), "")

    def test_strips_markup_and_scripts_never_become_text_nodes_of_tags(self):
        self.assertEqual(html_to_text("<p>Con <strong>negrita</strong></p>"), "Con negrita")


if __name__ == "__main__":
    unittest.main()
