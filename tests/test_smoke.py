import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import openpyxl


class SmokeTest(unittest.TestCase):
    def test_generates_kmz_from_embedded_coordinates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            workbook_path = tmp_path / "reclamos.xlsx"
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Reclamos - Hidricos"
            sheet.append(["ID", "Nº", "Estado", "Dirección del Ticket", "Problema", "Descripción", "Lat", "Lng"])
            sheet.append([
                1,
                1001,
                "Pendiente",
                "Roldan 1370",
                "Caños de zanja obstruido",
                "La zanja esta tapada -27.449512300000;-59.009170300000",
                "",
                "",
            ])
            workbook.save(workbook_path)

            output_dir = tmp_path / "outputs"
            cache_path = tmp_path / "cache.json"
            script_path = Path(__file__).resolve().parents[1] / "src" / "geocode_reclamos.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(workbook_path),
                    "--sheet",
                    "Reclamos - Hidricos",
                    "--output-dir",
                    str(output_dir),
                    "--cache",
                    str(cache_path),
                    "--delay",
                    "0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            kmz_path = output_dir / "reclamos_hidricos_geolocalizados.kmz"
            self.assertTrue(kmz_path.exists())
            self.assertIn('"geolocalizados": 1', result.stdout)
            with zipfile.ZipFile(kmz_path) as kmz:
                kml = kmz.read("doc.kml").decode("utf-8")
            self.assertIn("-59.0091703,-27.4495123,0", kml)


if __name__ == "__main__":
    unittest.main()
