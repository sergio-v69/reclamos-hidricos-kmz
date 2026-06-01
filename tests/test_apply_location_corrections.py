import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.apply_location_corrections import apply_corrections


class ApplyLocationCorrectionsTest(unittest.TestCase):
    def test_updates_csv_and_regenerates_kmz(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            csv_path = tmp_path / "reclamos.csv"
            kmz_path = tmp_path / "reclamos.kmz"
            with csv_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "id",
                        "ticket",
                        "estado",
                        "direccion",
                        "problema",
                        "descripcion",
                        "lat",
                        "lng",
                        "fuente",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "1",
                        "ticket": "1001",
                        "estado": "Pendiente",
                        "direccion": "Roldan 1370",
                        "problema": "Otros",
                        "descripcion": "Descripcion",
                        "lat": "-27.44",
                        "lng": "-59.00",
                        "fuente": "Nominatim/OSM",
                    }
                )

            result = apply_corrections(
                csv_path,
                kmz_path,
                [{"ticket": "1001", "lat": -27.4495123, "lng": -59.0091703}],
            )

            with csv_path.open("r", encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(result["updated"], 1)
            self.assertEqual(rows[0]["lat"], "-27.4495123")
            self.assertEqual(rows[0]["lng"], "-59.0091703")
            self.assertEqual(rows[0]["fuente"], "Correccion manual")
            with zipfile.ZipFile(kmz_path) as kmz:
                kml = kmz.read("doc.kml").decode("utf-8")
            self.assertIn("<name>1001</name>", kml)
            self.assertIn("-59.0091703,-27.4495123,0", kml)


if __name__ == "__main__":
    unittest.main()
