import argparse
from functools import partial
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from address_correction_geocoder import (
    geocode_corrected_addresses,
    refresh_needs_call_csv,
    save_address_corrections,
    test_geocode_address,
)
from apply_location_corrections import apply_corrections
from build_address_normalizer import build_normalizer
from build_interactive_map import build_map


class EditHandler(SimpleHTTPRequestHandler):
    csv_path = None
    kmz_path = None
    html_path = None
    copy_csv_path = None
    copy_kmz_path = None
    copy_html_path = None
    unresolved_csv_path = None
    call_csv_path = None
    address_corrections_path = None
    normalizer_html_path = None
    geocode_cache_path = None

    def do_POST(self):
        if self.path == "/api/apply-corrections":
            self.handle_apply_corrections()
            return
        if self.path == "/api/address-corrections":
            self.handle_address_corrections()
            return
        if self.path == "/api/geocode-corrected-addresses":
            self.handle_geocode_corrected_addresses()
            return
        if self.path == "/api/test-geocode":
            self.handle_test_geocode()
            return
        self.send_error(404, "No encontrado")

    def read_payload(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in content_type:
            form = parse_qs(body)
            return {"corrections": json.loads(form.get("corrections", ["[]"])[0])}, True
        return json.loads(body), False

    def handle_apply_corrections(self):
        try:
            payload, wants_redirect = self.read_payload()
            corrections = payload.get("corrections", [])
            if not isinstance(corrections, list):
                raise ValueError("El campo corrections debe ser una lista.")
            result = apply_corrections(self.csv_path, self.kmz_path, corrections)
            build_map(self.csv_path, self.html_path)
            if wants_redirect:
                self.redirect(f"/mapa_reclamos_interactivo.html?actualizado={result['updated']}")
                return
            self.send_json({"ok": True, **result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def handle_address_corrections(self):
        try:
            payload, wants_redirect = self.read_payload()
            result = save_address_corrections(self.address_corrections_path, payload.get("corrections", []))
            call_result = refresh_needs_call_csv(self.copy_csv_path, self.call_csv_path, self.address_corrections_path)
            build_normalizer(self.unresolved_csv_path, self.address_corrections_path, self.normalizer_html_path)
            if wants_redirect:
                self.redirect(f"/normalizador_direcciones.html?guardadas={result['saved']}")
                return
            self.send_json({"ok": True, **result, **call_result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def handle_geocode_corrected_addresses(self):
        try:
            payload, wants_redirect = self.read_payload()
            save_address_corrections(self.address_corrections_path, payload.get("corrections", []))
            result = geocode_corrected_addresses(
                self.copy_csv_path,
                self.copy_kmz_path,
                self.copy_html_path,
                self.unresolved_csv_path,
                self.call_csv_path,
                self.address_corrections_path,
                self.geocode_cache_path,
            )
            build_normalizer(self.unresolved_csv_path, self.address_corrections_path, self.normalizer_html_path)
            if wants_redirect:
                self.redirect(
                    f"/normalizador_direcciones.html?geolocalizadas={result['updated']}&pendientes={result['unresolved']}"
                )
                return
            self.send_json({"ok": True, **result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def handle_test_geocode(self):
        try:
            payload, _wants_redirect = self.read_payload()
            result = test_geocode_address(payload.get("address", ""), self.geocode_cache_path)
            self.send_json({"ok": True, **result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_OPTIONS(self):
        if self.path not in {
            "/api/apply-corrections",
            "/api/address-corrections",
            "/api/geocode-corrected-addresses",
            "/api/test-geocode",
        }:
            self.send_error(404, "No encontrado")
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser():
    parser = argparse.ArgumentParser(description="Sirve el mapa editable y guarda correcciones en CSV/KMZ.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--serve-dir", default="../outputs")
    parser.add_argument("--csv", default="../outputs/reclamos_hidricos_geolocalizados.csv")
    parser.add_argument("--kmz", default="../outputs/reclamos_hidricos_geolocalizados.kmz")
    parser.add_argument("--html", default="../outputs/mapa_reclamos_interactivo.html")
    parser.add_argument("--copy-csv", default="../outputs/reclamos_hidricos_geolocalizados_copia.csv")
    parser.add_argument("--copy-kmz", default="../outputs/reclamos_hidricos_geolocalizados_copia.kmz")
    parser.add_argument("--copy-html", default="../outputs/mapa_reclamos_interactivo_copia.html")
    parser.add_argument("--unresolved-csv", default="../outputs/reclamos_faltantes_sin_ubicacion.csv")
    parser.add_argument("--call-csv", default="../outputs/reclamos_para_llamar_vecino.csv")
    parser.add_argument("--address-corrections", default="../outputs/direcciones_corregidas_no_geolocalizados.json")
    parser.add_argument("--normalizer-html", default="../outputs/normalizador_direcciones.html")
    parser.add_argument("--geocode-cache", default="../work/geocode_missing_copia_cache.json")
    return parser


def main():
    args = build_parser().parse_args()
    serve_dir = Path(args.serve_dir).resolve()
    EditHandler.csv_path = Path(args.csv).resolve()
    EditHandler.kmz_path = Path(args.kmz).resolve()
    EditHandler.html_path = Path(args.html).resolve()
    EditHandler.copy_csv_path = Path(args.copy_csv).resolve()
    EditHandler.copy_kmz_path = Path(args.copy_kmz).resolve()
    EditHandler.copy_html_path = Path(args.copy_html).resolve()
    EditHandler.unresolved_csv_path = Path(args.unresolved_csv).resolve()
    EditHandler.call_csv_path = Path(args.call_csv).resolve()
    EditHandler.address_corrections_path = Path(args.address_corrections).resolve()
    EditHandler.normalizer_html_path = Path(args.normalizer_html).resolve()
    EditHandler.geocode_cache_path = Path(args.geocode_cache).resolve()

    handler = partial(EditHandler, directory=str(serve_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Mapa editable en http://{args.host}:{args.port}/mapa_reclamos_interactivo.html")
    print(f"CSV: {EditHandler.csv_path}")
    print(f"KMZ: {EditHandler.kmz_path}")
    print(f"Normalizador: http://{args.host}:{args.port}/normalizador_direcciones.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
