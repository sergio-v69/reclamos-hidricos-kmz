import csv
import json
import time
from pathlib import Path

from apply_location_corrections import generate_kmz
from build_interactive_map import build_map
from geocode_reclamos import geocode, in_bounds, parse_number


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ticket_key(row):
    value = str(row.get("ticket") or row.get("id") or "").strip()
    return value[:-2] if value.endswith(".0") else value


def normalized_corrections(items):
    corrections = {}
    for item in items or []:
        key = str(item.get("ticket") or item.get("id") or "").strip()
        if key.endswith(".0"):
            key = key[:-2]
        corrected = str(item.get("correctedAddress") or "").strip()
        note = str(item.get("note") or "").strip()
        needs_precision = bool(item.get("needsPrecision"))
        if key and (corrected or note or needs_precision):
            corrections[key] = {
                "ticket": key,
                "id": str(item.get("id") or "").strip(),
                "correctedAddress": corrected,
                "note": note,
                "needsPrecision": needs_precision,
                "updatedAt": str(item.get("updatedAt") or "").strip(),
            }
    return corrections


def save_address_corrections(path, items):
    corrections = normalized_corrections(items)
    save_json(path, corrections)
    return {"saved": len(corrections), "path": str(Path(path))}


def load_address_corrections(path):
    data = load_json(path, {})
    if isinstance(data, list):
        return normalized_corrections(data)
    return data


def is_cached_error(value):
    return isinstance(value, dict) and value.get("error")


def user_facing_geocode_error(error):
    message = str(error)
    if "HTTP Error 503" in message or "Service Unavailable" in message:
        return "El servicio externo de geolocalizacion no esta disponible ahora. Reintente en unos minutos."
    if "HTTP Error 429" in message:
        return "El servicio externo limito las consultas por exceso de uso. Espere unos minutos y reintente."
    return message


def test_geocode_address(address, cache_path, bounds=None):
    bounds = bounds or {
        "lat_min": -27.55,
        "lat_max": -27.30,
        "lng_min": -59.10,
        "lng_max": -58.85,
    }
    address = str(address or "").strip()
    if not address:
        raise ValueError("Ingrese una direccion corregida para probar.")

    cache_path = Path(cache_path)
    cache = load_json(cache_path, {})
    query = f"{address}, Resistencia, Chaco, Argentina"
    if is_cached_error(cache.get(query)):
        cache.pop(query, None)
        save_json(cache_path, cache)
    from_cache = query in cache
    if not from_cache:
        try:
            cache[query] = geocode(query, bounds)
        except Exception as exc:
            return {
                "found": False,
                "query": query,
                "from_cache": False,
                "temporary_error": True,
                "message": user_facing_geocode_error(exc),
            }
        save_json(cache_path, cache)

    cached = cache.get(query)
    if not cached:
        return {"found": False, "query": query, "from_cache": from_cache, "message": "No se encontro una ubicacion."}
    if is_cached_error(cached):
        return {
            "found": False,
            "query": query,
            "from_cache": from_cache,
            "temporary_error": True,
            "message": user_facing_geocode_error(cached["error"]),
        }

    lat = parse_number(cached.get("lat"))
    lng = parse_number(cached.get("lng"))
    if lat is None or lng is None or not in_bounds(lat, lng, bounds):
        return {"found": False, "query": query, "from_cache": from_cache, "message": "La ubicacion queda fuera del area esperada."}

    return {
        "found": True,
        "query": query,
        "from_cache": from_cache,
        "lat": lat,
        "lng": lng,
        "display_name": cached.get("display_name", ""),
        "importance": cached.get("importance"),
    }


def write_unresolved(rows, unresolved_csv, corrections):
    unresolved_csv = Path(unresolved_csv)
    unresolved_csv.parent.mkdir(parents=True, exist_ok=True)
    unresolved = [row for row in rows if not row.get("lat") or not row.get("lng")]
    base_fields = list(rows[0].keys()) if rows else []
    for field in ["direccion_corregida", "nota_correccion", "requiere_llamada_vecino"]:
        if field not in base_fields:
            base_fields.append(field)
    if "consulta_sugerida" not in base_fields:
        base_fields.append("consulta_sugerida")
    with unresolved_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=base_fields)
        writer.writeheader()
        for row in unresolved:
            correction = corrections.get(ticket_key(row), {})
            output = {field: row.get(field, "") for field in base_fields}
            output["direccion_corregida"] = correction.get("correctedAddress", row.get("direccion_corregida", ""))
            output["nota_correccion"] = correction.get("note", row.get("nota_correccion", ""))
            output["requiere_llamada_vecino"] = "SI" if correction.get("needsPrecision") else row.get(
                "requiere_llamada_vecino", ""
            )
            writer.writerow(output)
    return len(unresolved)


def geocode_corrected_addresses(
    csv_path,
    kmz_path,
    map_html_path,
    unresolved_csv,
    corrections_path,
    cache_path,
    delay=1.1,
    bounds=None,
):
    bounds = bounds or {
        "lat_min": -27.55,
        "lat_max": -27.30,
        "lng_min": -59.10,
        "lng_max": -58.85,
    }
    csv_path = Path(csv_path)
    cache_path = Path(cache_path)
    corrections = load_address_corrections(corrections_path)
    cache = load_json(cache_path, {})

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for field in ["direccion_corregida", "nota_correccion"]:
        if field not in fieldnames:
            fieldnames.append(field)

    updated = 0
    attempted = 0
    for row in rows:
        if row.get("lat") and row.get("lng"):
            continue
        correction = corrections.get(ticket_key(row))
        if not correction or not correction.get("correctedAddress"):
            continue
        if correction.get("needsPrecision"):
            continue
        row["direccion_corregida"] = correction.get("correctedAddress", "")
        row["nota_correccion"] = correction.get("note", "")
        query = f"{correction['correctedAddress']}, Resistencia, Chaco, Argentina"
        attempted += 1
        if is_cached_error(cache.get(query)):
            cache.pop(query, None)
            save_json(cache_path, cache)
        if query not in cache:
            try:
                cache[query] = geocode(query, bounds)
            except Exception as exc:
                cache.pop(query, None)
                print(f"No se pudo geolocalizar '{query}': {user_facing_geocode_error(exc)}")
            save_json(cache_path, cache)
            time.sleep(delay)
        cached = cache.get(query)
        if isinstance(cached, dict) and "lat" in cached:
            lat = parse_number(cached.get("lat"))
            lng = parse_number(cached.get("lng"))
            if lat is not None and lng is not None and in_bounds(lat, lng, bounds):
                row["lat"] = str(lat)
                row["lng"] = str(lng)
                row["fuente"] = "Direccion corregida manual"
                updated += 1

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    mapped = generate_kmz(rows, kmz_path)
    build_map(csv_path, map_html_path)
    unresolved = write_unresolved(rows, unresolved_csv, corrections)
    return {
        "attempted": attempted,
        "updated": updated,
        "mapped": mapped,
        "unresolved": unresolved,
        "csv": str(csv_path),
        "kmz": str(Path(kmz_path)),
        "map": str(Path(map_html_path)),
        "unresolved_csv": str(Path(unresolved_csv)),
    }
