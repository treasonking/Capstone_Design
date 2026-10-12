from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
ROUTE_TARGETS = {"/", "/demo.html", "/login", "/signup", "/app", "/admin"}


class RouteFallbackHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/config.js":
            origin = os.getenv("UI_API_ORIGIN", "http://127.0.0.1:8000")
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                self.send_error(500, "Invalid UI_API_ORIGIN")
                return
            body = ("window.ORCA_CONFIG = Object.freeze(" + json.dumps({"apiOrigin": origin.rstrip("/")}) + ");").encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def translate_path(self, path: str) -> str:
        route = path.split("?", 1)[0].rstrip("/") or "/"
        if route in ROUTE_TARGETS:
            return str(ROOT / "demo.html")
        return super().translate_path(path)


if __name__ == "__main__":
    port = int(os.getenv("UI_TEST_PORT", "5500"))
    server = ThreadingHTTPServer(("127.0.0.1", port), RouteFallbackHandler)
    print(f"TEAM ORCA UI: http://127.0.0.1:{port}/login (root: {ROOT})")
    server.serve_forever()
