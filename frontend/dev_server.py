from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUTE_TARGETS = {"/login", "/signup", "/app", "/admin"}


class RouteFallbackHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        route = path.split("?", 1)[0].rstrip("/") or "/"
        if route in ROUTE_TARGETS:
            return str(ROOT / "demo.html")
        return super().translate_path(path)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), RouteFallbackHandler)
    print("TEAM ORCA UI: http://127.0.0.1:5500/login")
    server.serve_forever()
