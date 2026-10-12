from __future__ import annotations

from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
from urllib.error import HTTPError

import pytest

from frontend.dev_server import ROOT, RouteFallbackHandler


def test_frontend_routes_are_cwd_independent_and_api_is_not_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UI_API_ORIGIN", "http://127.0.0.1:8123")
    server = ThreadingHTTPServer(("127.0.0.1", 0), RouteFallbackHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for route in ("/", "/demo.html", "/login", "/signup", "/app", "/admin"):
            for suffix in ("", "?test=1", "/?test=1"):
                with urlopen(base + route + suffix) as response:
                    assert response.status == 200
                    assert response.read() == (ROOT / "demo.html").read_bytes()
        with urlopen(base + "/config.js") as response:
            assert b"http://127.0.0.1:8123" in response.read()
            assert response.headers["Cache-Control"] == "no-store"
        for missing in ("/missing.js", "/auth/signup", "/proxy/chat", "/unknown"):
            with pytest.raises(HTTPError) as exc:
                urlopen(base + missing)
            assert exc.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
