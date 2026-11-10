# -*- coding: utf-8 -*-
"""本地交互式 Web UI：起终点 + seed + Generate + Canvas。

只监听 127.0.0.1；零第三方依赖（stdlib http.server）。
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..humanize import Humanizer

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _parse_xy(v, default):
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return float(v[0]), float(v[1])
    if isinstance(v, dict) and "x" in v and "y" in v:
        return float(v["x"]), float(v["y"])
    return default


class Handler(BaseHTTPRequestHandler):
    server_version = "touch-humanization-web"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            return self._serve("index.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])
        if path == "/api/health":
            return self._send(200, _json_bytes({"ok": True}), "application/json")
        return self._send(404, _json_bytes({"ok": False, "error": "not found"}),
                          "application/json")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/gesture":
            return self._send(404, _json_bytes({"ok": False, "error": "not found"}),
                              "application/json")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n > 0 else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            return self._send(400, _json_bytes({"ok": False, "error": str(e)}),
                              "application/json")
        try:
            start = _parse_xy(body.get("start"), (100, 1800))
            end = _parse_xy(body.get("end"), (900, 400))
            seed = body.get("seed")
            seed = int(seed) if seed not in (None, "") else None
            for_slider = bool(body.get("for_slider", False))
            exact_end = bool(body.get("exact_end", True))
            h = Humanizer(seed=seed)
            g = h.gesture(start, end, for_slider=for_slider, exact_end=exact_end)
            return self._send(200, _json_bytes({"ok": True, "gesture": g.as_dict()}),
                              "application/json")
        except Exception as e:
            return self._send(500, _json_bytes({"ok": False, "error": str(e)}),
                              "application/json")

    def _serve(self, name: str, ctype: str) -> None:
        p = os.path.join(STATIC_DIR, name)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError as e:
            return self._send(500, str(e).encode("utf-8"), "text/plain; charset=utf-8")
        return self._send(200, data, ctype)

    def _serve_static(self, rel: str) -> None:
        rel = posixpath.normpath(urllib.parse.unquote(rel))
        if rel.startswith("..") or os.path.isabs(rel):
            return self._send(403, b"forbidden", "text/plain; charset=utf-8")
        full = os.path.realpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(os.path.realpath(STATIC_DIR) + os.sep):
            return self._send(403, b"forbidden", "text/plain; charset=utf-8")
        if not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1].lower()
        ctype = {".html": "text/html; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8"}.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            return self._send(200, f.read(), ctype)


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    httpd = _Server((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="touch-humanization Web UI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    httpd = make_server(args.host, args.port)
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{port}/"
    print(f"touch-humanization Web UI: {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
