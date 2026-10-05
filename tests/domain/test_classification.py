import unittest

from buscador_empleos.domain.classification import (
    classify_roles,
    expand_queries,
    extract_techs,
    title_matches_query,
)


class ClassifyRolesTest(unittest.TestCase):
    def test_developer_titles(self):
        for title in (
            "Desarrollador Java Senior",
            "Software Engineer",
            "Programador PHP",
            "Desarrollador Full Stack",
            "Ingeniero de Sistemas",
            "Backend Developer",
        ):
            self.assertEqual(classify_roles(title), ["Desarrollador"], title)

    def test_data_titles(self):
        for title in (
            "Analista de Datos",
            "Data Analyst",
            "Analista BI",
            "Científico de datos",
            "Business Intelligence Lead",
        ):
            self.assertEqual(classify_roles(title), ["Analista de datos"], title)

    def test_mixed_title_counts_in_both(self):
        self.assertEqual(set(classify_roles("Data Developer")), {"Analista de datos", "Desarrollador"})

    def test_everything_else_is_other(self):
        for title in ("Analista Comercial", "Auxiliar Contable", "Analista de Talento Humano"):
            self.assertEqual(classify_roles(title), ["Otros"], title)


class ExtractTechsTest(unittest.TestCase):
    def test_detects_common_technologies(self):
        found = extract_techs("Experiencia en Java, Angular y SQL Server con Docker")
        self.assertTrue({"Java", "Angular", "SQL Server", "SQL", "Docker"} <= set(found))

    def test_word_boundaries(self):
        self.assertNotIn("Java", extract_techs("Experiencia en JavaScript"))
        self.assertNotIn("SQL", extract_techs("Conocimiento de NoSQL"))
        self.assertNotIn("R", extract_techs("Trabajo en equipo y comunicación"))

    def test_symbols_in_names(self):
        found = extract_techs("Stack: C#, .NET, Node.js y C++")
        self.assertTrue({"C#", ".NET", "Node.js", "C++"} <= set(found))

    def test_long_names_ignore_case(self):
        found = extract_techs("conocimientos de python y power bi")
        self.assertTrue({"Python", "Power BI"} <= set(found))

    def test_short_names_respect_case(self):
        self.assertIn("R", extract_techs("Manejo de R y Python"))
        self.assertNotIn("R", extract_techs("manejo de r minuscula"))

    def test_nothing_found(self):
        self.assertEqual(extract_techs("Buscamos una persona proactiva"), [])


class QueryMatchingTest(unittest.TestCase):
    def test_known_role_matches_in_english_or_spanish(self):
        self.assertTrue(title_matches_query("Senior Software Engineer", "desarrollador de software"))
        self.assertTrue(title_matches_query("Data Analyst III", "analista de datos"))
        self.assertFalse(title_matches_query("Sales Manager", "desarrollador de software"))

    def test_unknown_role_requires_every_keyword(self):
        self.assertTrue(title_matches_query("Enfermera jefe de urgencias", "enfermera urgencias"))
        self.assertFalse(title_matches_query("Enfermera de quirófano", "enfermera urgencias"))
        self.assertFalse(title_matches_query("Cualquier cosa", ""))

    def test_extra_text_also_counts_for_unknown_roles(self):
        self.assertTrue(title_matches_query("Enfermera", "enfermera urgencias", extra="Urgencias"))


class ExpandQueriesTest(unittest.TestCase):
    def test_adds_related_roles_without_duplicates(self):
        out = expand_queries(["desarrollador de software", "analista de datos"])
        self.assertEqual(out[0], "desarrollador de software")
        self.assertIn("programador", out)
        self.assertIn("data analyst", out)
        self.assertEqual(len(out), len({q.lower() for q in out}))

    def test_unknown_roles_are_left_alone(self):
        self.assertEqual(expand_queries(["contador"]), ["contador"])

    def test_a_term_already_given_is_not_repeated(self):
        out = expand_queries(["desarrollador de software", "Programador"])
        self.assertEqual(len([q for q in out if q.lower() == "programador"]), 1)

    def test_empty(self):
        self.assertEqual(expand_queries([]), [])


if __name__ == "__main__":
    unittest.main()
