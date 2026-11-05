"""Serve the three-module UI and open it in the browser.

Usage (from the repository root):
  python scripts/serve_ui.py
"""

from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
UI = ROOT / "ui"
INBOX = ROOT / "inbox"
RESULT = INBOX / "result.json"
OUTPUT = INBOX / "output.docx"
START = INBOX / "start.json"
PROGRESS = INBOX / "progress.json"
VISION = INBOX / "vision.json"
KEPT = {".gitkeep", "result.json", "start.json", "output.docx", "progress.json", "vision.json"}
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


def _with_pairs(result: dict) -> dict:
    from problem_time.run_paper import lesson_cards

    shown = dict(result)
    source = INBOX / str(result.get("source") or "")
    lessons = result.get("base", {}).get("lessons") or []
    shown["pairs"] = lesson_cards(source, lessons)
    return shown


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
        if path == "/api/vision":
            self._json({"configured": _vision_key() != ""})
            return
        if path == "/api/progress":
            if PROGRESS.is_file():
                self._json(json.loads(PROGRESS.read_text(encoding="utf-8")))
            else:
                self._json({"running": False, "percent": 0, "label": ""})
            return
        if path == "/api/result":
            if not RESULT.is_file():
                self.send_error(404)
                return
            self._result(json.loads(RESULT.read_text(encoding="utf-8")))
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/review":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = json.loads(RESULT.read_text(encoding="utf-8"))
            level = payload.get("level") or ""
            if level not in {"", "B", "A", "AA", "AAA", "S"}:
                self.send_error(400)
                return
            result["review"][int(payload["index"])]["level"] = level
            result["released"] = False
            RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            self._result(result)
            return
        if path == "/api/reorder-stars":
            if not RESULT.is_file():
                self._json({"ok": False, "message": "还没有开始"})
                return
            payload = self._body()
            result = json.loads(RESULT.read_text(encoding="utf-8"))
            from problem_time.arrange_docx import order_lesson_stars

            try:
                order_lesson_stars(result, list(payload.get("order") or []))
            except (TypeError, ValueError) as exc:
                self._json({"ok": False, "message": str(exc) or "这份排序和正课对不上"})
                return
            result["released"] = False
            if OUTPUT.is_file():
                OUTPUT.unlink()
            RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            self._result(result)
            return
        if path == "/api/submit":
            if not RESULT.is_file():
                self._json({"ok": False, "message": "还没有开始"})
                return
            result = json.loads(RESULT.read_text(encoding="utf-8"))
            if any(not item.get("level") for item in result.get("review") or []):
                self._json({"ok": False, "message": "还有题目没选班型"})
                return
            from problem_time.arrange_docx import apply_review_levels

            apply_review_levels(INBOX, result)
            result["released"] = True
            RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            PROGRESS.write_text(
                json.dumps({"running": False, "percent": 100, "label": "完成"}, ensure_ascii=False),
                encoding="utf-8",
            )
            shown = _with_pairs(result)
            self._json({"ok": True, "result": shown})
            return
        if path == "/api/vision":
            payload = self._body()
            _save_vision_key(str(payload.get("apiKey") or ""))
            self._json({"configured": _vision_key() != ""})
            return
        if path == "/api/start":
            payload = self._body()
            if payload.get("apiKey"):
                _save_vision_key(str(payload["apiKey"]))
            START.write_text(
                json.dumps({"files": payload.get("files") or []}, ensure_ascii=False),
                encoding="utf-8",
            )
            if _JOB.acquire(blocking=False):
                PROGRESS.write_text(
                    json.dumps({"running": True, "percent": 5, "label": "已开始"}, ensure_ascii=False),
                    encoding="utf-8",
                )
                threading.Thread(target=_run_job, daemon=True).start()
                self._json({"started": True})
            else:
                self._json({"started": False})
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
        _clear_previous_output()
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
        _clear_previous_output()
        self._json({"removed": name})

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _result(self, result: dict) -> None:
        data = json.dumps(_with_pairs(result), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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


_JOB = threading.Lock()


def _vision_key() -> str:
    if not VISION.is_file():
        return ""
    payload = json.loads(VISION.read_text(encoding="utf-8"))
    return str(payload.get("api_key") or "").strip()


def _save_vision_key(api_key: str) -> None:
    key = api_key.strip()
    if not key:
        if VISION.is_file():
            VISION.unlink()
        return
    VISION.write_text(json.dumps({"api_key": key}, ensure_ascii=False), encoding="utf-8")


def _clear_previous_output() -> None:
    for path in (RESULT, OUTPUT):
        if path.is_file():
            path.unlink()
    PROGRESS.write_text(
        json.dumps({"running": False, "percent": 0, "label": ""}, ensure_ascii=False),
        encoding="utf-8",
    )


def _run_job() -> None:
    try:
        from problem_time.run_paper import run_started

        run_started(INBOX)
    except Exception:
        return
    finally:
        _JOB.release()


def list_files() -> list[dict[str, int | str]]:
    rows = []
    for item in sorted(INBOX.iterdir(), key=lambda path: path.name):
        if item.is_file() and item.name not in KEPT and not item.name.startswith("."):
            rows.append({"name": item.name, "size": item.stat().st_size})
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
