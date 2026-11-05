"""Serve the three-module UI and open it in the browser.

Usage (from the repository root):
  python scripts/serve_ui.py
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"
INBOX = ROOT / "inbox"
RESULT = INBOX / "result.json"
OUTPUT = INBOX / "output.docx"
START = INBOX / "start.json"
KEPT = {".gitkeep", "result.json", "start.json", "output.docx"}
HOST = "127.0.0.1"
FIRST_PORT = 8765
LAST_PORT = 8775
MAX_UPLOAD = 40 * 1024 * 1024


def main() -> int:
    INBOX.mkdir(exist_ok=True)
    running = find_running()
    if running:
        webbrowser.open(running)
        print(running, flush=True)
        return 0
    port = first_free_port()
    url = f"http://{HOST}:{port}/"
    server = ThreadingHTTPServer((HOST, port), Handler)
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


def find_running() -> str | None:
    for port in range(FIRST_PORT, LAST_PORT + 1):
        url = f"http://{HOST}:{port}/api/health"
        try:
            with urlopen(url, timeout=0.4) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            continue
        if body.get("app") == "question-time-complexity":
            return f"http://{HOST}:{port}/"
    return None


def first_free_port() -> int:
    import socket

    for port in range(FIRST_PORT, LAST_PORT + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
            except OSError:
                continue
            return port
    raise SystemExit("8765–8775 都已被占用")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json({"ok": True, "app": "question-time-complexity"})
            return
        if path == "/api/files":
            self._json({"files": list_files()})
            return
        if path == "/api/output":
            if not OUTPUT.is_file():
                self.send_error(404)
                return
            data = OUTPUT.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/result":
            if not RESULT.is_file():
                self.send_error(404)
                return
            data = RESULT.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/start":
            length = int(self.headers.get("Content-Length", "0"))
            START.write_bytes(self.rfile.read(length))
            self._json({"started": True})
            return
        if path != "/api/files":
            self.send_error(404)
            return
        name = self.file_name()
        if name is None:
            self.send_error(400)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD:
            self.send_error(413)
            return
        target = INBOX / name
        target.write_bytes(self.rfile.read(length))
        self._json({"name": name, "size": target.stat().st_size})

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/files":
            self.send_error(404)
            return
        query = parse_qs(urlparse(self.path).query)
        if "name" not in query:
            for item in INBOX.iterdir():
                if item.is_file() and item.name not in KEPT:
                    item.unlink()
            self._json({"cleared": True})
            return
        name = Path(query["name"][0]).name
        target = INBOX / name
        if target.is_file() and target.name != "result.json":
            target.unlink()
        self._json({"removed": name})

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def file_name(self) -> str | None:
        query = parse_qs(urlparse(self.path).query)
        raw = query.get("name", [""])[0]
        name = Path(raw).name
        if not name or name in KEPT or name.startswith("."):
            return None
        return name


def list_files() -> list[dict[str, int | str]]:
    rows = []
    for item in sorted(INBOX.iterdir(), key=lambda path: path.name):
        if item.is_file() and item.name not in KEPT and not item.name.startswith("."):
            rows.append({"name": item.name, "size": item.stat().st_size})
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
