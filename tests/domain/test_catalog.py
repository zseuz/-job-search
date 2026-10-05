"""Consistencia del catálogo: los datos que alimentan a la página no pueden contradecirse."""

import unittest

from buscador_empleos.domain.catalog import (
    RELATED_QUERIES,
    ROLE_PATTERNS,
    TECH_GROUPS,
    TECH_PATTERNS,
    TECHS,
)


class CatalogConsistencyTest(unittest.TestCase):
    def test_no_duplicate_technologies(self):
        self.assertEqual(len(TECHS), len(set(TECHS)))

    def test_every_technology_has_a_pattern(self):
        self.assertEqual(set(TECH_PATTERNS), set(TECHS))

    def test_every_technology_belongs_to_exactly_one_group(self):
        grouped = [tech for techs in TECH_GROUPS.values() for tech in techs]
        self.assertEqual(sorted(grouped), sorted(TECHS))

    def test_related_queries_exist_only_for_known_roles(self):
        self.assertTrue(set(RELATED_QUERIES) <= set(ROLE_PATTERNS))


if __name__ == "__main__":
    unittest.main()
