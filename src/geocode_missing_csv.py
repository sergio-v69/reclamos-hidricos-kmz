import argparse
import csv
import json
import re
import shutil
import time
from pathlib import Path

try:
    from apply_location_corrections import generate_kmz
    from geocode_reclamos import clean_address, extract_coords, geocode, in_bounds, parse_number
except ModuleNotFoundError:
    from src.apply_location_corrections import generate_kmz
    from src.geocode_reclamos import clean_address, extract_coords, geocode, in_bounds, parse_number


def load_cache(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(path, cache):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def row_has_coords(row):
    return parse_number(row.get("lat")) is not None and parse_number(row.get("lng")) is not None


def strip_block_lot_data(text):
    text = re.sub(r"\b(?:mz|mza|manzana|m)\s*\.?\s*\d+[a-z]?\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:pc|parcela|p)\s*\.?\s*\d+[a-z]?\b", " ", text, flags=re.I)
    text = re.sub(r"\b(?:casa|cs)\s*\.?\s*\d+[a-z]?\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" .,-")


def normalize_street_name(text):
    text = strip_block_lot_data(text)
    text = re.sub(r"\b(?:calle|avda?|avenida|pje|pasaje)\b\.?", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,-")


def numbered_cross_street_candidates(text):
    clean = strip_block_lot_data(clean_address(text, ""))
    pattern = re.compile(
        r"(?P<street>.+?)\s+(?:y|esquina|entre)\s+(?:calle\s+|c\s*)?(?P<number>\d{1,2})\b",
        flags=re.I,
    )
    match = pattern.search(clean)
    if not match:
        return []
    street = normalize_street_name(match.group("street"))
    if not street or street.lower().startswith(("calle ", "c ")):
        return []
    number = int(match.group("number"))
    height = number * 100 + 800
    return [f"{street} {height}", f"{street} al {height}"]


def intersection_candidates(text):
    clean = strip_block_lot_data(clean_address(text, ""))
    parts = re.split(r"\s+(?:y|esquina|intersecci[oó]n(?:\s+calles)?|entre)\s+", clean, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return []
    first = normalize_street_name(parts[0])
    second = normalize_street_name(re.split(r"\s+(?:hasta|entre|,|\.)\s*", parts[1], maxsplit=1, flags=re.I)[0])
    if not first or not second:
        return []
    return [f"{first} y {second}", f"{first} esquina {second}", first, second]


def expanded_address_values(row):
    values = [
        clean_address(row.get("direccion"), row.get("descripcion")),
        clean_address(row.get("direccion", ""), ""),
        clean_address(row.get("descripcion"), ""),
    ]
    expanded = []
    for value in values:
        if not value:
            continue
        expanded.extend(numbered_cross_street_candidates(value))
        expanded.extend(intersection_candidates(value))
        cleaned = strip_block_lot_data(value)
        expanded.append(cleaned)
    return expanded


def candidate_queries(row, args):
    candidates = []
    for value in expanded_address_values(row):
        value = clean_address(value, "")
        if not value:
            continue
        candidates.extend(
            [
                f"{value}, {args.city}, {args.province}, {args.country}",
                f"{value}, {args.province}, {args.country}",
            ]
        )
    seen = set()
    unique = []
    for item in candidates:
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[: args.max_candidates]


def geocode_row(row, args, bounds, cache, network_state):
    lat, lng = extract_coords(row.get("direccion"), row.get("descripcion"), bounds=bounds)
    if lat is not None and lng is not None:
        return lat, lng, "Coordenadas en descripcion", "coordenadas_en_texto"

    for query in candidate_queries(row, args):
        if query not in cache:
            if args.no_network:
                continue
            if args.max_network_queries and network_state["queries"] >= args.max_network_queries:
                network_state["limit_reached"] = True
                break
            try:
                cache[query] = geocode(query, bounds)
            except Exception as exc:
                cache[query] = {"error": str(exc)}
            save_cache(args.cache, cache)
            network_state["queries"] += 1
            time.sleep(args.delay)
        cached = cache.get(query)
        if isinstance(cached, dict) and "lat" in cached:
            lat = parse_number(cached.get("lat"))
            lng = parse_number(cached.get("lng"))
            if lat is not None and lng is not None and in_bounds(lat, lng, bounds):
                return lat, lng, "Nominatim/OSM copia", query
    return None, None, "", ""


def process(args):
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if input_csv.resolve() != output_csv.resolve():
        shutil.copy2(input_csv, output_csv)

    bounds = {
        "lat_min": args.lat_min,
        "lat_max": args.lat_max,
        "lng_min": args.lng_min,
        "lng_max": args.lng_max,
    }
    cache = load_cache(args.cache)

    with output_csv.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    total_missing_before = sum(1 for row in rows if not row_has_coords(row))
    resolved = []
    unresolved = []
    network_state = {"queries": 0, "limit_reached": False}

    for row in rows:
        if row_has_coords(row):
            continue
        lat, lng, source, query = geocode_row(row, args, bounds, cache, network_state)
        if lat is not None and lng is not None:
            row["lat"] = str(lat)
            row["lng"] = str(lng)
            row["fuente"] = source
            resolved.append({**row, "consulta": query})
        else:
            unresolved.append(row)
        if network_state["limit_reached"]:
            break

    if network_state["limit_reached"]:
        seen_keys = {str(row.get("ticket") or row.get("id") or "") for row in resolved + unresolved}
        for row in rows:
            if row_has_coords(row):
                continue
            key = str(row.get("ticket") or row.get("id") or "")
            if key not in seen_keys:
                unresolved.append(row)

    with output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    unresolved_path = Path(args.unresolved_csv)
    unresolved_path.parent.mkdir(parents=True, exist_ok=True)
    unresolved_fields = fieldnames + ["consulta_sugerida"]
    with unresolved_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=unresolved_fields)
        writer.writeheader()
        for row in unresolved:
            writer.writerow({**row, "consulta_sugerida": " | ".join(candidate_queries(row, args)[:3])})

    mapped = generate_kmz(rows, args.output_kmz)
    result = {
        "total": len(rows),
        "faltantes_antes": total_missing_before,
        "nuevos_geolocalizados": len(resolved),
        "faltantes_despues": len(unresolved),
        "con_coordenadas": mapped,
        "consultas_realizadas": network_state["queries"],
        "limite_consultas_alcanzado": network_state["limit_reached"],
        "csv_copia": str(output_csv),
        "kmz_copia": str(Path(args.output_kmz)),
        "sin_ubicacion": str(unresolved_path),
        "cache": str(Path(args.cache)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Copia un CSV geolocalizado y consulta uno por uno los tickets sin coordenadas.")
    parser.add_argument("input_csv")
    parser.add_argument("output_csv")
    parser.add_argument("--output-kmz", required=True)
    parser.add_argument("--unresolved-csv", required=True)
    parser.add_argument("--cache", default="../work/geocode_missing_copia_cache.json")
    parser.add_argument("--city", default="Resistencia")
    parser.add_argument("--province", default="Chaco")
    parser.add_argument("--country", default="Argentina")
    parser.add_argument("--delay", type=float, default=1.1)
    parser.add_argument("--max-candidates", type=int, default=2)
    parser.add_argument("--max-network-queries", type=int, default=0)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--lat-min", type=float, default=-27.55)
    parser.add_argument("--lat-max", type=float, default=-27.30)
    parser.add_argument("--lng-min", type=float, default=-59.10)
    parser.add_argument("--lng-max", type=float, default=-58.85)
    return parser


if __name__ == "__main__":
    process(build_parser().parse_args())
