from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error, request


def _http_json(base: str, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    url = base.rstrip("/") + path
    data_bytes = None
    headers = {}
    if body is not None:
        data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(url, data=data_bytes, method=method, headers=headers)
    try:
        with request.urlopen(req) as resp:
            content = resp.read()
            parsed = json.loads(content.decode("utf-8")) if content else None
            return resp.status, parsed
    except error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
            parsed = json.loads(detail) if detail else None
        except Exception:
            parsed = None
        return e.code, parsed
    except Exception as e:
        return -1, {"error": str(e)}


@dataclass
class TestResult:
    name: str
    expected: Any
    actual: Any
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "name": self.name,
            "expected": self.expected,
            "actual": self.actual,
            "status": self.status,
        }


def _log(logfile: str, result: TestResult) -> None:
    os.makedirs(os.path.dirname(logfile) or ".", exist_ok=True)
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def run_suite(base: str, logfile: str) -> Dict[str, Any]:
    results: List[TestResult] = []
    created_ids: List[int] = []

    def record(name: str, expected: Any, actual: Any, ok: bool) -> None:
        res = TestResult(name=name, expected=expected, actual=actual, status="pass" if ok else "fail")
        results.append(res)
        _log(logfile, res)

    # 1) create
    status, body = _http_json(base, "POST", "/tasks", {"title": "TestCase", "priority": "normal"})
    ok = status == 200 and isinstance(body, dict) and {"id", "title", "priority", "isDone"} <= set(body.keys())
    if ok:
        created_ids.append(int(body["id"]))
    record("create", {"status": 200, "fields": ["id", "title", "priority", "isDone"]}, {"status": status, "body": body}, ok)

    # 2) list contains created
    status, body = _http_json(base, "GET", "/tasks")
    ok = status == 200 and isinstance(body, list) and any(t.get("id") in created_ids for t in body)
    record("list_after_create", {"status": 200, "contains_created": True}, {"status": status, "body": body}, ok)

    # 3) update
    task_id = created_ids[0] if created_ids else 1
    status, body = _http_json(base, "PUT", f"/tasks/{task_id}", {"title": "Updated", "priority": "high"})
    ok = status == 200 and isinstance(body, dict) and body.get("title") == "Updated" and body.get("priority") == "high"
    record("update", {"status": 200, "title": "Updated", "priority": "high"}, {"status": status, "body": body}, ok)

    # 4) complete
    status, _body = _http_json(base, "POST", f"/tasks/{task_id}/complete")
    ok = status == 200
    record("complete", {"status": 200}, {"status": status}, ok)

    # 5) list reflects completion
    status, body = _http_json(base, "GET", "/tasks")
    ok = status == 200 and isinstance(body, list) and any(t.get("id") == task_id and t.get("isDone") for t in body)
    record("list_after_complete", {"status": 200, "isDone": True}, {"status": status, "body": body}, ok)

    # 6) delete
    status, _body = _http_json(base, "DELETE", f"/tasks/{task_id}")
    ok = status == 200
    record("delete", {"status": 200}, {"status": status}, ok)

    # 7) list after delete
    status, body = _http_json(base, "GET", "/tasks")
    ok = status == 200 and isinstance(body, list) and all(t.get("id") != task_id for t in body)
    record("list_after_delete", {"status": 200, "deleted_absent": True}, {"status": status, "body": body}, ok)

    # 8) complete missing
    status, _body = _http_json(base, "POST", "/tasks/999999/complete")
    ok = status == 404
    record("complete_missing", {"status": 404}, {"status": status}, ok)

    # 9) backup endpoint
    status, body = _http_json(base, "POST", "/admin/backup")
    ok = status == 200 and isinstance(body, dict) and "backup" in body
    record("backup", {"status": 200, "path_present": True}, {"status": status, "body": body}, ok)

    # 10) logs endpoint
    status, body = _http_json(base, "GET", "/admin/logs?limit=5")
    ok = status == 200 and isinstance(body, list)
    record("logs", {"status": 200, "is_list": True}, {"status": status, "body": body}, ok)

    # summary
    passed = sum(1 for r in results if r.status == "pass")
    summary = {"total": len(results), "passed": passed, "failed": len(results) - passed, "logfile": logfile}
    _log(logfile, TestResult(name="summary", expected=None, actual=summary, status="summary"))
    return summary


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Simple HTTP API test runner (stdlib only).")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL of the Todo server")
    parser.add_argument("--logfile", default="test_results.log", help="Where to store test results (JSONL)")
    args = parser.parse_args(argv)
    summary = run_suite(args.base, args.logfile)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

