import csv
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


def display_value(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value or "")


def placemark(row):
    description = (
        f"<b>Ticket:</b> {escape(display_value(row.get('ticket')))}<br/>"
        f"<b>ID:</b> {escape(display_value(row.get('id')))}<br/>"
        f"<b>Fecha:</b> {escape(display_value(row.get('fecha')))}<br/>"
        f"<b>Estado:</b> {escape(display_value(row.get('estado')))}<br/>"
        f"<b>Problema:</b> {escape(display_value(row.get('problema')))}<br/>"
        f"<b>Direccion:</b> {escape(display_value(row.get('direccion')))}<br/>"
        f"<b>Descripcion del reclamo:</b> {escape(display_value(row.get('descripcion')))}<br/>"
        f"<b>Fuente:</b> {escape(display_value(row.get('fuente')))}"
    )
    name = escape(display_value(row.get("ticket")) or "Sin ticket")
    return f"""
    <Placemark>
      <name>{name}</name>
      <description><![CDATA[{description}]]></description>
      <Point><coordinates>{row['lng']},{row['lat']},0</coordinates></Point>
    </Placemark>"""


def generate_kmz(rows, kmz_path, name="Reclamos Hidricos geolocalizados"):
    mapped = [row for row in rows if row.get("lat") not in ("", None) and row.get("lng") not in ("", None)]
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(name)}</name>
    <description>{len(mapped)} reclamos geolocalizados.</description>
    {''.join(placemark(row) for row in mapped)}
  </Document>
</kml>
"""
    kmz_path = Path(kmz_path)
    kmz_path.parent.mkdir(parents=True, exist_ok=True)
    kml_path = kmz_path.parent / "doc.kml"
    kml_path.write_text(kml, encoding="utf-8")
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as file:
        file.write(kml_path, "doc.kml")
    return len(mapped)


def correction_key(correction):
    return str(correction.get("ticket") or correction.get("id") or "").strip()


def row_key(row):
    return str(row.get("ticket") or row.get("id") or "").strip()


def apply_corrections(csv_path, kmz_path, corrections):
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    correction_by_key = {correction_key(item): item for item in corrections if correction_key(item)}
    updated = 0
    for row in rows:
        correction = correction_by_key.get(row_key(row))
        if not correction:
            continue
        row["lat"] = str(correction["lat"])
        row["lng"] = str(correction["lng"])
        if "fuente" in row:
            row["fuente"] = "Correccion manual"
        updated += 1

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    mapped = generate_kmz(rows, kmz_path)
    return {"updated": updated, "mapped": mapped, "csv": str(csv_path), "kmz": str(kmz_path)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Aplica correcciones manuales de ubicacion al CSV y regenera KMZ.")
    parser.add_argument("csv_path")
    parser.add_argument("kmz_path")
    parser.add_argument("corrections_json")
    args = parser.parse_args()

    corrections = json.loads(Path(args.corrections_json).read_text(encoding="utf-8"))
    print(json.dumps(apply_corrections(args.csv_path, args.kmz_path, corrections), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
