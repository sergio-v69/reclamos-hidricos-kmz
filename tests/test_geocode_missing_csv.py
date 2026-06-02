import argparse
import unittest

from src.geocode_missing_csv import candidate_queries


class GeocodeMissingCsvTest(unittest.TestCase):
    def args(self):
        return argparse.Namespace(
            city="Resistencia",
            province="Chaco",
            country="Argentina",
            max_candidates=10,
        )

    def test_numbered_cross_street_becomes_height(self):
        queries = candidate_queries({"direccion": "Leandro N Alem y C21", "descripcion": ""}, self.args())
        self.assertIn("Leandro N Alem 2900, Resistencia, Chaco, Argentina", queries)

    def test_block_and_lot_data_is_removed(self):
        queries = candidate_queries(
            {"direccion": "Mz 37 pc2- fortín los pozos entre calle 22 y 23", "descripcion": ""},
            self.args(),
        )
        self.assertIn("fortín los pozos 3000, Resistencia, Chaco, Argentina", queries)
        self.assertNotIn("Mz 37", " ".join(queries))
        self.assertNotIn("pc2", " ".join(queries))

    def test_named_intersection_is_preserved(self):
        queries = candidate_queries({"direccion": "Hermanos Pinzon y calle 1 de mayo", "descripcion": ""}, self.args())
        self.assertIn("Hermanos Pinzon y 1 de mayo, Resistencia, Chaco, Argentina", queries)


if __name__ == "__main__":
    unittest.main()
