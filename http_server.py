import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlparse

from storage import TaskStore


_COMPLETE_RE = re.compile(r"^/tasks/(\d+)/complete$")


class TodoHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_cls, store: TaskStore):
        super().__init__(server_address, handler_cls)
        self.store = store


class TodoRequestHandler(BaseHTTPRequestHandler):
    server: TodoHTTPServer

    def _send_json(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json_object(self) -> Optional[dict]:
        length_raw = self.headers.get("Content-Length")
        if not length_raw:
            return None
        try:
            length = int(length_raw)
        except ValueError:
            return None
        if length <= 0:
            return None

        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        return obj if isinstance(obj, dict) else None

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/tasks":
            self._send_json(200, self.server.store.list_tasks())
            return

        self._send_empty(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/tasks":
            body = self._read_json_object()
            if body is None:
                self._send_json(400, {"error": "invalid JSON body"})
                return

            try:
                created = self.server.store.create_task(body.get("title"), body.get("priority"))
            except ValueError as e:
                self._send_json(400, {"error": str(e)})
                return

            self._send_json(200, created)
            return

        m = _COMPLETE_RE.match(path)
        if m:
            task_id = int(m.group(1))
            ok = self.server.store.complete_task(task_id)
            if ok:
                self._send_empty(200)
            else:
                self._send_empty(404)
            return

        self._send_empty(404)

    def log_message(self, format: str, *args) -> None:
        return
