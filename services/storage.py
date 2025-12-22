from __future__ import annotations

import json
import os
import threading
from typing import Dict, List, Optional

from services.models import Task
from services.action_log import ActionLogger


ALLOWED_PRIORITIES = {"low", "normal", "high"}


class TaskStore:
    """
    Хранит задачи в памяти и синхронизирует их с файлом tasks.txt (JSON-массив).
    """

    def __init__(self, storage_path: str = "tasks.txt", logger: Optional[ActionLogger] = None) -> None:
        self._storage_path = storage_path
        self._lock = threading.Lock()
        self._tasks: Dict[int, Task] = {}
        self._next_id: int = 1
        self._logger = logger

    @property
    def storage_path(self) -> str:
        return self._storage_path

    def _log(self, action: str, task_id: Optional[int], status: str, origin: Optional[str], details: Optional[dict] = None) -> None:
        if self._logger:
            self._logger.log(action=action, task_id=task_id, status=status, origin=origin, details=details)

    def load(self) -> None:
        """
        При старте: если tasks.txt существует — восстановить задачи из файла.
        """
        if not os.path.exists(self._storage_path):
            return

        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
                if not raw:
                    return
                data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            # Если файл поврежден — стартуем с пустого состояния
            return

        if not isinstance(data, list):
            return

        tasks: Dict[int, Task] = {}
        max_id = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                t = Task.from_dict(item)
            except (KeyError, ValueError, TypeError):
                continue
            tasks[t.id] = t
            if t.id > max_id:
                max_id = t.id

        with self._lock:
            self._tasks = tasks
            self._next_id = max_id + 1

    def save(self) -> None:
        """
        Сохранить текущее состояние в tasks.txt.
        Пишем атомарно: во временный файл -> replace.
        """
        with self._lock:
            data = [t.to_dict() for t in sorted(self._tasks.values(), key=lambda x: x.id)]

        tmp_path = self._storage_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        os.replace(tmp_path, self._storage_path)

    def list_tasks(self) -> List[dict]:
        with self._lock:
            return [t.to_dict() for t in sorted(self._tasks.values(), key=lambda x: x.id)]

    def get_task(self, task_id: int) -> Optional[dict]:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.to_dict() if task else None

    def get_logs(self, limit: int = 100) -> List[dict]:
        if not self._logger:
            return []
        return self._logger.tail(limit)

    def create_task(self, title: object, priority: object, origin: Optional[str] = None) -> dict:
        """
        Создает задачу и сохраняет состояние. Проверяет входные данные.
        """
        if not isinstance(title, str):
            raise ValueError("Field 'title' must be a non-empty string.")
        if not isinstance(priority, str):
            raise ValueError("Field 'priority' must be one of: low, normal, high.")

        title = title.strip()
        priority = priority.strip()

        if not title:
            raise ValueError("Field 'title' must be a non-empty string.")
        if priority not in ALLOWED_PRIORITIES:
            raise ValueError("Field 'priority' must be one of: low, normal, high.")

        with self._lock:
            task_id = self._next_id
            self._next_id += 1
            task = Task(id=task_id, title=title, priority=priority, is_done=False)
            self._tasks[task_id] = task

        self.save()
        self._log("create", task_id, "success", origin, {"title": title, "priority": priority})
        return task.to_dict()

    def update_task(self, task_id: int, title: Optional[object], priority: Optional[object], origin: Optional[str] = None) -> bool:
        """
        Обновляет существующую задачу. Пустые поля не трогаем.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                self._log("update", task_id, "not_found", origin, {})
                return False

            if title is not None:
                if not isinstance(title, str):
                    raise ValueError("Field 'title' must be a non-empty string.")
                title = title.strip()
                if not title:
                    raise ValueError("Field 'title' must be a non-empty string.")
                task.title = title

            if priority is not None:
                if not isinstance(priority, str):
                    raise ValueError("Field 'priority' must be one of: low, normal, high.")
                priority = priority.strip()
                if priority not in ALLOWED_PRIORITIES:
                    raise ValueError("Field 'priority' must be one of: low, normal, high.")
                task.priority = priority

        self.save()
        self._log("update", task_id, "success", origin, {"title": title, "priority": priority})
        return True

    def complete_task(self, task_id: int, origin: Optional[str] = None) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                self._log("complete", task_id, "not_found", origin, {})
                return False
            task.is_done = True

        self.save()
        self._log("complete", task_id, "success", origin, {})
        return True

    def delete_task(self, task_id: int, origin: Optional[str] = None) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                self._log("delete", task_id, "not_found", origin, {})
                return False
            self._tasks.pop(task_id)

        self.save()
        self._log("delete", task_id, "success", origin, {})
        return True
