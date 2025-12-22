from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ActionRecord:
    timestamp: str
    action: str
    task_id: Optional[int]
    status: str
    origin: Optional[str]
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ActionLogger:
    """
    Потокобезопасный логгер действий. Хранит события в JSONL файле.
    Каждое событие — одна строка JSON с полями ActionRecord.
    """

    def __init__(self, path: str = "logs.txt") -> None:
        self._path = path
        self._lock = threading.Lock()

    def log(
        self,
        action: str,
        task_id: Optional[int],
        status: str,
        origin: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ActionRecord:
        record = ActionRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            action=action,
            task_id=task_id,
            status=status,
            origin=origin,
            details=details or {},
        )
        line = json.dumps(record.to_dict(), ensure_ascii=False)

        with self._lock:
            # гарантируем существование директории
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        return record

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Возвращает последние limit записей (с конца файла).
        """
        if limit <= 0:
            return []

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return []

        result: List[Dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

