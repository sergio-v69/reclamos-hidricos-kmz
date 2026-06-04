import csv
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from address_correction_geocoder import write_needs_call_csv, write_unresolved  # noqa: E402


class NeedsCallCsvTest(unittest.TestCase):
    def test_writes_call_csv_and_excludes_from_unresolved(self):
        rows = [
            {
                "ticket": "1001",
                "id": "1",
                "direccion": "Mz 1 Pc 2",
                "lat": "",
                "lng": "",
                "fuente": "No resuelto",
            },
            {
                "ticket": "1002",
                "id": "2",
                "direccion": "Alem 2900",
                "lat": "",
                "lng": "",
                "fuente": "No resuelto",
            },
        ]
        corrections = {
            "1001": {
                "ticket": "1001",
                "note": "Requiere llamada",
                "needsPrecision": True,
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            call_result = write_needs_call_csv(rows, tmp_path / "llamar.csv", corrections)
            unresolved_count = write_unresolved(rows, tmp_path / "pendientes.csv", corrections)

            with (tmp_path / "llamar.csv").open("r", encoding="utf-8", newline="") as file:
                call_rows = list(csv.DictReader(file))
            with (tmp_path / "pendientes.csv").open("r", encoding="utf-8", newline="") as file:
                unresolved_rows = list(csv.DictReader(file))

            self.assertEqual(call_result["call_count"], 1)
            self.assertEqual(call_rows[0]["ticket"], "1001")
            self.assertEqual(call_rows[0]["requiere_llamada_vecino"], "SI")
            self.assertEqual(unresolved_count, 1)
            self.assertEqual(unresolved_rows[0]["ticket"], "1002")


if __name__ == "__main__":
    unittest.main()
