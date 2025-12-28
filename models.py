from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Task:
    id: int
    title: str
    priority: str
    is_done: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "id": self.id,
            "priority": self.priority,
            "isDone": self.is_done,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Task":
        return Task(
            id=int(data["id"]),
            title=str(data["title"]),
            priority=str(data["priority"]),
            is_done=bool(data["isDone"]),
        )
