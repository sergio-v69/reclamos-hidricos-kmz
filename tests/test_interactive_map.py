import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InteractiveMapTest(unittest.TestCase):
    def test_builds_interactive_map_html(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            csv_path = tmp_path / "reclamos.csv"
            html_path = tmp_path / "mapa.html"
            with csv_path.open("w", newline="", encoding="utf-8") as file:
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
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "id": "1",
                        "ticket": "1001",
                        "fecha": "2026-04-15 15:15",
                        "estado": "Pendiente",
                        "direccion": "Roldan 1370",
                        "problema": "Caños de zanja obstruido",
                        "descripcion": "La zanja esta tapada",
                        "lat": "-27.4495123",
                        "lng": "-59.0091703",
                        "fuente": "Coordenadas en descripcion",
                    }
                )

            script_path = Path(__file__).resolve().parents[1] / "src" / "build_interactive_map.py"
            result = subprocess.run(
                [sys.executable, str(script_path), str(csv_path), str(html_path)],
                check=True,
                capture_output=True,
                text=True,
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn('"tickets": 1', result.stdout)
            self.assertIn("Mapa de Reclamos Hidricos", html)
            self.assertIn('"ticket": "1001"', html)
            self.assertIn('"fecha": "2026-04-15 15:15"', html)
            self.assertIn("dateFrom", html)
            self.assertIn("dateTo", html)
            self.assertIn("La zanja esta tapada", html)
            self.assertIn("leaflet@1.9.4", html)
            self.assertIn("Editar ubicaciones", html)
            self.assertIn("Actualizar CSV/KMZ", html)
            self.assertIn("draggable: editMode", html)
            self.assertIn("/api/apply-corrections", html)
            self.assertIn("APPLY_ENDPOINT", html)
            self.assertIn("http://127.0.0.1:8765", html)
            self.assertIn("XMLHttpRequest", html)
            self.assertIn("correcciones_ubicacion_reclamos.csv", html)
            self.assertNotIn('/[",\n', html)
            self.assertIn('lines.join("\\n")', html)


if __name__ == "__main__":
    unittest.main()
