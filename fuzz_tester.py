from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _request(base: str, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    url = base.rstrip("/") + path
    data_bytes = None
    headers = {}
    if body is not None:
        data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=data_bytes, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            parsed = json.loads(content.decode("utf-8")) if content else None
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
            parsed = json.loads(detail) if detail else None
        except Exception:
            parsed = None
        return e.code, parsed
    except Exception as e:
        return -1, {"error": str(e)}


def random_title() -> Any:
    samples = [
        "Buy milk",
        "Do HW",
        "Call mom",
        "Read book",
        "Fix bug",
        "Plan trip",
        "",
        "   ",
        None,
    ]
    return random.choice(samples)


def random_priority() -> Any:
    samples: List[Any] = ["low", "normal", "high", "urgent", "", None, 123]
    return random.choice(samples)


def _log_line(logfile: Optional[str], entry: Dict[str, Any]) -> None:
    if not logfile:
        return
    os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_scenario(base: str, steps: int, rng: random.Random, logfile: Optional[str] = None) -> Dict[str, int]:
    known_ids: List[int] = []
    stats: Dict[str, int] = {"ok": 0, "fail": 0}

    for i in range(steps):
        action = rng.choice(["create", "update", "delete", "complete"])
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "step": i + 1,
            "action": action,
        }
        if action == "create":
            title = random_title()
            priority = random_priority()
            entry["request"] = {"path": "/tasks", "body": {"title": title, "priority": priority}}
            status, body = _request(base, "POST", "/tasks", {"title": title, "priority": priority})
            entry["response"] = {"status": status, "body": body}
            if status == 200 and isinstance(body, dict) and "id" in body:
                known_ids.append(int(body["id"]))
            _record(stats, status)
        elif action == "update":
            task_id = _pick_id(known_ids, rng)
            title = random_title()
            priority = random_priority()
            entry["request"] = {"path": f"/tasks/{task_id}", "body": {"title": title, "priority": priority}}
            status, body = _request(base, "PUT", f"/tasks/{task_id}", {"title": title, "priority": priority})
            entry["response"] = {"status": status, "body": body}
            _record(stats, status)
        elif action == "complete":
            task_id = _pick_id(known_ids, rng)
            entry["request"] = {"path": f"/tasks/{task_id}/complete", "body": None}
            status, body = _request(base, "POST", f"/tasks/{task_id}/complete")
            entry["response"] = {"status": status, "body": body}
            _record(stats, status)
        elif action == "delete":
            task_id = _pick_id(known_ids, rng)
            entry["request"] = {"path": f"/tasks/{task_id}", "body": None}
            status, body = _request(base, "DELETE", f"/tasks/{task_id}")
            entry["response"] = {"status": status, "body": body}
            if status == 200 and task_id in known_ids:
                known_ids.remove(task_id)
            _record(stats, status)

        entry["result"] = "ok" if entry.get("response", {}).get("status", 0) in range(200, 300) else "fail"
        _log_line(logfile, entry)

    print("Fuzzing finished.")
    print(f"Total steps: {steps}")
    print(f"OK (2xx): {stats['ok']}, Fail (!2xx): {stats['fail']}")
    summary_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": {"steps": steps, "ok": stats["ok"], "fail": stats["fail"]},
    }
    _log_line(logfile, summary_entry)
    return stats


def _pick_id(ids: List[int], rng: random.Random) -> int:
    if ids and rng.random() < 0.7:
        return rng.choice(ids)
    return rng.randint(1, max(ids) + 5 if ids else 5)


def _record(stats: Dict[str, int], status: int) -> None:
    if 200 <= status < 300:
        stats["ok"] += 1
    else:
        stats["fail"] += 1


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Random action tester for Todo HTTP API.")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL of the Todo server")
    parser.add_argument("--steps", type=int, default=30, help="How many random actions to run")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (optional)")
    parser.add_argument("--logfile", default="fuzz_results.log", help="Where to store fuzz results (JSONL)")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    run_scenario(args.base, args.steps, rng, logfile=args.logfile)


if __name__ == "__main__":
    main()

