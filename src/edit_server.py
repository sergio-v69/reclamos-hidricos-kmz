import argparse
from functools import partial
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from apply_location_corrections import apply_corrections
from build_interactive_map import build_map


class EditHandler(SimpleHTTPRequestHandler):
    csv_path = None
    kmz_path = None
    html_path = None

    def do_POST(self):
        if self.path != "/api/apply-corrections":
            self.send_error(404, "No encontrado")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            corrections = payload.get("corrections", [])
            if not isinstance(corrections, list):
                raise ValueError("El campo corrections debe ser una lista.")
            result = apply_corrections(self.csv_path, self.kmz_path, corrections)
            build_map(self.csv_path, self.html_path)
            self.send_json({"ok": True, **result})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def do_OPTIONS(self):
        if self.path != "/api/apply-corrections":
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
    return parser


def main():
    args = build_parser().parse_args()
    serve_dir = Path(args.serve_dir).resolve()
    EditHandler.csv_path = Path(args.csv).resolve()
    EditHandler.kmz_path = Path(args.kmz).resolve()
    EditHandler.html_path = Path(args.html).resolve()

    handler = partial(EditHandler, directory=str(serve_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Mapa editable en http://{args.host}:{args.port}/mapa_reclamos_interactivo.html")
    print(f"CSV: {EditHandler.csv_path}")
    print(f"KMZ: {EditHandler.kmz_path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
