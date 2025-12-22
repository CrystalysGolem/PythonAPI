from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from services.backup import perform_backup
from services.storage import TaskStore


_COMPLETE_RE = re.compile(r"^/tasks/(\d+)/complete$")
_TASK_ID_RE = re.compile(r"^/tasks/(\d+)$")


class TodoHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, store: TaskStore):
        super().__init__(server_address, RequestHandlerClass)
        self.store = store


class TodoRequestHandler(BaseHTTPRequestHandler):
    server: TodoHTTPServer

    def _origin(self) -> Optional[str]:
        try:
            return self.client_address[0]
        except Exception:
            return None

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

    def _read_json_body(self) -> Optional[dict]:
        length_str = self.headers.get("Content-Length")
        if not length_str:
            return None
        try:
            length = int(length_str)
        except ValueError:
            return None
        if length <= 0:
            return None

        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(obj, dict):
            return None
        return obj

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/tasks":
            tasks = self.server.store.list_tasks()
            self._send_json(200, tasks)
            return

        if path == "/admin/logs":
            query = parse_qs(urlparse(self.path).query)
            try:
                limit = int(query.get("limit", ["100"])[0])
            except ValueError:
                limit = 100
            if limit <= 0:
                limit = 1
            logs = self.server.store.get_logs(limit)
            self._send_json(200, logs)
            return

        self._send_empty(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/admin/backup":
            try:
                backup_path = perform_backup(self.server.store.storage_path)
            except FileNotFoundError as e:
                self._send_json(404, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            else:
                self._send_json(200, {"backup": backup_path})
            return

        if path == "/tasks":
            body = self._read_json_body()
            if body is None:
                self._send_json(400, {"error": "Invalid JSON body. Expected object with title and priority."})
                return

            title = body.get("title")
            priority = body.get("priority")

            try:
                created = self.server.store.create_task(title, priority, origin=self._origin())
            except Exception as e:
                self._send_json(400, {"error": str(e)})
                return

            self._send_json(200, created)
            return

        m = _COMPLETE_RE.match(path)
        if m:
            task_id = int(m.group(1))
            ok = self.server.store.complete_task(task_id, origin=self._origin())
            if ok:
                self._send_empty(200)
            else:
                self._send_empty(404)
            return

        self._send_empty(404)

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        m = _TASK_ID_RE.match(path)
        if not m:
            self._send_empty(404)
            return

        task_id = int(m.group(1))
        body = self._read_json_body() or {}

        title = body.get("title") if "title" in body else None
        priority = body.get("priority") if "priority" in body else None

        try:
            updated = self.server.store.update_task(task_id, title, priority, origin=self._origin())
        except Exception as e:
            self._send_json(400, {"error": str(e)})
            return

        if not updated:
            self._send_empty(404)
            return

        task = self.server.store.get_task(task_id)
        self._send_json(200, task)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        m = _TASK_ID_RE.match(path)
        if not m:
            self._send_empty(404)
            return

        task_id = int(m.group(1))
        ok = self.server.store.delete_task(task_id, origin=self._origin())
        if ok:
            self._send_empty(200)
        else:
            self._send_empty(404)

    def log_message(self, format: str, *args) -> None:
        return
