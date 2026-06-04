import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AddressNormalizerTest(unittest.TestCase):
    def test_builds_manual_address_normalizer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            csv_path = tmp_path / "pendientes.csv"
            corrections_path = tmp_path / "correcciones.json"
            html_path = tmp_path / "normalizador.html"

            with csv_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "id",
                        "ticket",
                        "fecha",
                        "estado",
                        "direccion",
                        "problema",
                        "descripcion",
                        "lat",
                        "lng",
                        "fuente",
                        "consulta_sugerida",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "1",
                        "ticket": "1001",
                        "fecha": "2026-04-15 15:15",
                        "estado": "Pendiente",
                        "direccion": "Mz 12 Pc 3 Leandro N Alem y C21",
                        "problema": "Reclamo hidrico",
                        "descripcion": "Referencia frente a plaza",
                        "lat": "",
                        "lng": "",
                        "fuente": "",
                        "consulta_sugerida": "Leandro N Alem 2900, Resistencia, Chaco, Argentina",
                    }
                )

            corrections_path.write_text(
                json.dumps(
                    {
                        "1001": {
                            "ticket": "1001",
                            "correctedAddress": "Leandro N Alem 2900",
                            "note": "Normalizada manualmente",
                        }
                    }
                ),
                encoding="utf-8",
            )

            script_path = Path(__file__).resolve().parents[1] / "src" / "build_address_normalizer.py"
            result = subprocess.run(
                [sys.executable, str(script_path), str(csv_path), str(corrections_path), str(html_path)],
                check=True,
                capture_output=True,
                text=True,
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn('"tickets": 1', result.stdout)
            self.assertIn("Normalizar direcciones pendientes", html)
            self.assertIn("Editar ticket", html)
            self.assertIn("Probar geolocalizacion", html)
            self.assertIn("testMap", html)
            self.assertIn("openstreetmap.org/export/embed.html", html)
            self.assertIn("Llamar al vecino", html)
            self.assertIn("Guardar correcciones", html)
            self.assertIn("Geolocalizar corregidas", html)
            self.assertIn("/api/address-corrections", html)
            self.assertIn("/api/geocode-corrected-addresses", html)
            self.assertIn("/api/test-geocode", html)
            self.assertIn("Leandro N Alem 2900", html)
            self.assertIn("Referencia frente a plaza", html)


if __name__ == "__main__":
    unittest.main()
