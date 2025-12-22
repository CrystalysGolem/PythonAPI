from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Optional


def perform_backup(storage_path: str, backup_dir: Optional[str] = None) -> str:
    """
    Создает резервную копию файла задач.
    Возвращает путь к созданной копии.
    """
    if not os.path.exists(storage_path):
        raise FileNotFoundError(f"Storage file not found: {storage_path}")

    backup_root = backup_dir or os.path.join(os.path.dirname(storage_path) or ".", "backups")
    os.makedirs(backup_root, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")
    basename = os.path.basename(storage_path)
    name, ext = os.path.splitext(basename)
    backup_name = f"{name}_{timestamp}{ext or '.json'}"
    backup_path = os.path.join(backup_root, backup_name)

    shutil.copy2(storage_path, backup_path)
    return backup_path

