"""
Core HTTP server framework for ThreatNova CyberLabs.

Zero external dependencies - built entirely on the Python standard library.
Provides a tiny routing layer, Request/Response abstractions, cookie handling,
and static file serving on top of http.server.
"""
from __future__ import annotations

import os
import re
import json
import traceback
import mimetypes
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")


# --------------------------------------------------------------------------- #
# Request / Response
# --------------------------------------------------------------------------- #
class Request:
    def __init__(self, method, path, query, headers, body, params=None):
        self.method = method
        self.path = path
        self.query = query            # dict[str, str]
        self.headers = headers
        self.body = body              # raw bytes
        self.params = params or {}    # path params
        self._form = None
        self._cookies = None
        self.user = None              # populated by auth middleware
        self.session = None

    @property
    def form(self):
        if self._form is None:
            self._form = {}
            ctype = self.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in ctype:
                parsed = parse_qs(self.body.decode("utf-8", "replace"), keep_blank_values=True)
                self._form = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            elif "application/json" in ctype:
                try:
                    self._form = json.loads(self.body.decode("utf-8", "replace") or "{}")
                except Exception:
                    self._form = {}
        return self._form

    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = {}
            raw = self.headers.get("Cookie")
            if raw:
                c = SimpleCookie()
                c.load(raw)
                self._cookies = {k: v.value for k, v in c.items()}
        return self._cookies

    def get(self, key, default=None):
        """Look up a value in form first, then query string."""
        if key in self.form:
            return self.form[key]
        return self.query.get(key, default)


class Response:
    def __init__(self, body="", status=200, content_type="text/html; charset=utf-8", headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = headers or {}
        self._cookies = []

    def set_cookie(self, name, value, max_age=None, http_only=True, path="/", same_site="Lax"):
        parts = [f"{name}={value}", f"Path={path}", f"SameSite={same_site}"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        if http_only:
            parts.append("HttpOnly")
        self._cookies.append("; ".join(parts))
        return self

    def delete_cookie(self, name, path="/"):
        self._cookies.append(f"{name}=; Path={path}; Max-Age=0")
        return self


def html(body, status=200):
    return Response(body, status=status)


def redirect(location, status=302):
    return Response("", status=status, headers={"Location": location})


def json_response(data, status=200):
    return Response(json.dumps(data), status=status, content_type="application/json")


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
class Route:
    def __init__(self, method, pattern, handler):
        self.method = method
        self.handler = handler
        # convert "/courses/<slug>" -> regex
        regex = re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", pattern)
        self.regex = re.compile(f"^{regex}$")


class App:
    def __init__(self):
        self.routes = []
        self.middlewares = []  # callables(req) -> None, may set req.user etc.
        self.error_handlers = {}

    def route(self, pattern, methods=("GET",)):
        def decorator(fn):
            for m in methods:
                self.routes.append(Route(m.upper(), pattern, fn))
            return fn
        return decorator

    def get(self, pattern):
        return self.route(pattern, methods=("GET",))

    def post(self, pattern):
        return self.route(pattern, methods=("POST",))

    def use(self, fn):
        self.middlewares.append(fn)
        return fn

    def error_handler(self, status):
        def decorator(fn):
            self.error_handlers[status] = fn
            return fn
        return decorator

    def dispatch(self, req):
        # run middlewares
        for mw in self.middlewares:
            result = mw(req)
            if isinstance(result, Response):
                return result

        matched_path = False
        for route in self.routes:
            m = route.regex.match(req.path)
            if m:
                matched_path = True
                if route.method == req.method:
                    req.params = m.groupdict()
                    result = route.handler(req)
                    if isinstance(result, Response):
                        return result
                    if isinstance(result, (dict, list)):
                        return json_response(result)
                    return html(result if result is not None else "")

        if matched_path:
            return self._error(req, 405, "Method Not Allowed")
        return self._error(req, 404, "Not Found")

    def _error(self, req, status, message):
        handler = self.error_handlers.get(status)
        if handler:
            res = handler(req)
            res.status = status
            return res
        return Response(f"<h1>{status}</h1><p>{message}</p>", status=status)


# --------------------------------------------------------------------------- #
# HTTP handler wiring
# --------------------------------------------------------------------------- #
def _serve_static(path):
    rel = path[len("/static/"):]
    # prevent path traversal
    safe = os.path.normpath(os.path.join(STATIC_DIR, rel))
    if not safe.startswith(STATIC_DIR) or not os.path.isfile(safe):
        return Response("Not Found", status=404, content_type="text/plain")
    ctype, _ = mimetypes.guess_type(safe)
    with open(safe, "rb") as f:
        data = f.read()
    return Response(data, content_type=ctype or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=3600"})


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ThreatNovaCyberLabs/1.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            print(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

        def _handle(self, method):
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                if path != "/" and path.endswith("/"):
                    path = path.rstrip("/")

                if path.startswith("/static/"):
                    res = _serve_static(path)
                    return self._send(res)

                query = {k: v[0] if len(v) == 1 else v
                         for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length) if length else b""
                req = Request(method, path, query, self.headers, body)
                res = app.dispatch(req)
                self._send(res)
            except Exception:
                traceback.print_exc()
                self._send(Response("<h1>500</h1><p>Internal Server Error</p>", status=500))

        def _send(self, res):
            self.send_response(res.status)
            self.send_header("Content-Type", res.content_type)
            self.send_header("Content-Length", str(len(res.body)))
            for k, v in res.headers.items():
                self.send_header(k, v)
            for c in res._cookies:
                self.send_header("Set-Cookie", c)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(res.body)

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_HEAD(self):
            self._handle("GET")

    return Handler


def run(app, host="0.0.0.0", port=8000):
    handler = make_handler(app)
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"ThreatNova CyberLabs running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.shutdown()
