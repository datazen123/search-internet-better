"""Zero-dependency HTTP server (Python 3.10+ standard library only).

Run:  python3 -m server.app   then open http://localhost:8000
API:  GET  /api/search?q=...&lens=<id>&depth=50
      POST /api/search  {"q": "...", "lens": {...lens json...}, "depth": 50}
      GET  /api/lenses    GET /api/status    GET /api/index (own-index transparency stats)
Nothing is written to disk: results live only for the request (vendor terms; privacy).
"""
from __future__ import annotations
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from .lens import Lens, load_lens, list_lenses
from .pipeline import search
from .adapters import adapter_status

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_DEPTH = 200


def _load_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, fmt, *args):  # no query logging by default (privacy principle)
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=list).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlsplit(self.path)
        if u.path == "/api/search":
            p = parse_qs(u.query)
            q = (p.get("q") or [""])[0].strip()
            if not q:
                return self._json({"error": "Add a search query with ?q="}, 400)
            depth = min(MAX_DEPTH, int((p.get("depth") or ["50"])[0]))
            return self._json(search(q, load_lens((p.get("lens") or ["default"])[0]), depth))
        if u.path == "/api/lenses":
            return self._json({"lenses": list_lenses()})
        if u.path.startswith("/api/lenses/"):
            return self._json(load_lens(u.path.rsplit("/", 1)[-1]).to_dict())
        if u.path == "/api/status":
            return self._json({"adapters": adapter_status()})
        if u.path == "/api/index":
            from .adapters.local import LocalIndexAdapter
            idx = LocalIndexAdapter._open()
            return self._json({"stats": idx.stats() if idx else None,
                               "note": None if idx else "No own index yet: python3 -m server.index --help"})
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/search":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 200_000:
            return self._json({"error": "request too large"}, 413)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            lens = Lens.from_dict(body.get("lens") or {})
        except (ValueError, TypeError) as e:
            return self._json({"error": f"Could not read the lens: {e}"}, 400)
        q = str(body.get("q", "")).strip()
        if not q:
            return self._json({"error": "Add a search query"}, 400)
        return self._json(search(q, lens, min(MAX_DEPTH, int(body.get("depth", 50)))))


def main():
    _load_env()
    port = int(os.environ.get("PORT", "8000"))
    print(f"experimental-search on http://localhost:{port}  adapters: {adapter_status()}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
