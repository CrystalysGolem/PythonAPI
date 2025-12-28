import json
import os
import threading
from typing import Dict, List, Optional

from models import Task


ALLOWED_PRIORITIES = {"low", "normal", "high"}


class TaskStore:
    def __init__(self, path: str = "tasks.txt") -> None:
        self._path = path
        self._lock = threading.Lock()
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1

    def load(self) -> None:
        if not os.path.exists(self._path):
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if not raw:
                return
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(data, list):
            return

        tasks: Dict[int, Task] = {}
        max_id = 0

        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                task = Task.from_dict(item)
            except (KeyError, ValueError, TypeError):
                continue
            tasks[task.id] = task
            if task.id > max_id:
                max_id = task.id

        with self._lock:
            self._tasks = tasks
            self._next_id = max_id + 1

    def save(self) -> None:
        with self._lock:
            data = [t.to_dict() for t in sorted(self._tasks.values(), key=lambda x: x.id)]

        tmp_path = self._path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        os.replace(tmp_path, self._path)

    def list_tasks(self) -> List[dict]:
        with self._lock:
            return [t.to_dict() for t in sorted(self._tasks.values(), key=lambda x: x.id)]

    def create_task(self, title: object, priority: object) -> dict:
        if not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if not isinstance(priority, str):
            raise ValueError("priority must be one of: low, normal, high")

        title = title.strip()
        priority = priority.strip()

        if not title:
            raise ValueError("title must be a non-empty string")
        if priority not in ALLOWED_PRIORITIES:
            raise ValueError("priority must be one of: low, normal, high")

        with self._lock:
            task_id = self._next_id
            self._next_id += 1
            task = Task(id=task_id, title=title, priority=priority, is_done=False)
            self._tasks[task_id] = task

        self.save()
        return task.to_dict()

    def complete_task(self, task_id: int) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.is_done:
                return True
            task.is_done = True

        self.save()
        return True
