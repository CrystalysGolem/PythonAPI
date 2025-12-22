from __future__ import annotations

import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, List

# Гарантируем, что корень проекта в sys.path для импортов tests/* при запуске как скрипта.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _request(base: str, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            if not content:
                return {"status": resp.status, "body": None}
            return {"status": resp.status, "body": json.loads(content.decode("utf-8"))}
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8")
            parsed = json.loads(detail) if detail else None
        except Exception:
            parsed = None
        return {"status": e.code, "body": parsed}
    except Exception as e:
        return {"status": -1, "body": {"error": str(e)}}


def cmd_list(args: argparse.Namespace) -> None:
    res = _request(args.base, "GET", "/tasks")
    if args.limit and isinstance(res.get("body"), list):
        res["body"] = res["body"][: args.limit]
    _print_response(res)


def cmd_logs(args: argparse.Namespace) -> None:
    path = f"/admin/logs?limit={args.limit}"
    res = _request(args.base, "GET", path)
    _print_response(res)


def cmd_create(args: argparse.Namespace) -> None:
    body = {"title": args.title, "priority": args.priority}
    res = _request(args.base, "POST", "/tasks", body)
    _print_response(res)


def cmd_update(args: argparse.Namespace) -> None:
    body: Dict[str, Any] = {}
    if args.title is not None:
        body["title"] = args.title
    if args.priority is not None:
        body["priority"] = args.priority
    res = _request(args.base, "PUT", f"/tasks/{args.id}", body)
    _print_response(res)


def cmd_delete(args: argparse.Namespace) -> None:
    res = _request(args.base, "DELETE", f"/tasks/{args.id}")
    _print_response(res)


def cmd_complete(args: argparse.Namespace) -> None:
    res = _request(args.base, "POST", f"/tasks/{args.id}/complete")
    _print_response(res)


def cmd_backup(args: argparse.Namespace) -> None:
    res = _request(args.base, "POST", "/admin/backup")
    _print_response(res)


def cmd_tests(args: argparse.Namespace) -> None:
    from tests.test_runner import run_suite

    summary = run_suite(args.base, args.logfile)
    print("Test suite finished:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def cmd_fuzz_run(args: argparse.Namespace) -> None:
    from tests.fuzz_tester import run_scenario

    rng = random.Random(args.seed)
    stats = run_scenario(args.base, args.steps, rng, logfile=args.logfile)
    print(json.dumps({"summary": stats, "logfile": args.logfile}, ensure_ascii=False, indent=2))


PRESET_TITLES = [
    "Buy milk",
    "Call mom",
    "Finish report",
    "Read book",
    "Clean desk",
    "Plan trip",
    "Water plants",
    "Pay bills",
    "Workout",
    "Learn Python",
]


def cmd_random(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    created = 0
    for _ in range(args.count):
        title = rng.choice(PRESET_TITLES)
        priority = rng.choice(["low", "normal", "high"])
        res = _request(args.base, "POST", "/tasks", {"title": title, "priority": priority})
        if 200 <= res.get("status", 0) < 300:
            created += 1
        _print_response(res)
    print(f"Created {created} of {args.count} requested.")


def cmd_menu(args: argparse.Namespace) -> None:
    """
    Простой интерактивный режим для удобства администратора.
    """
    base = args.base
    _show_menu_banner()
    actions = {
        "1": ("Показать задачи", lambda: cmd_list(_wrap(args, limit=None))),
        "2": ("Создать задачу", lambda: _menu_create(base)),
        "3": ("Создать рандомные задачи", lambda: _menu_random(base)),
        "4": ("Запустить тесты API", lambda: _menu_tests(base)),
        "5": ("Запустить фузз-тест", lambda: _menu_fuzz(base)),
        "6": ("Обновить задачу", lambda: _menu_update(base)),
        "7": ("Завершить задачу", lambda: _menu_complete(base)),
        "8": ("Удалить задачу", lambda: _menu_delete(base)),
        "9": ("Показать логи", lambda: _menu_logs(base)),
        "10": ("Сделать бэкап", lambda: _print_response(_request(base, "POST", "/admin/backup"))),
        "0": ("Выход", None),
    }

    while True:
        print("\n=== Admin Menu ===")
        for key, (title, _) in actions.items():
            print(f"{key}. {title}")
        choice = input("Выберите опцию: ").strip()
        if choice == "0":
            print("Выход.")
            break
        action = actions.get(choice)
        if not action:
            print("Неверный выбор, повторите.")
            continue
        try:
            action[1]()  # type: ignore
        except KeyboardInterrupt:
            print("\nПрервано пользователем.")
        except Exception as e:
            print(f"Ошибка: {e}")


_MENU_WELCOME_SHOWN = False


def _show_menu_banner() -> None:
    global _MENU_WELCOME_SHOWN
    if _MENU_WELCOME_SHOWN:
        return
    _MENU_WELCOME_SHOWN = True
    art = r"""
 /\_/\
( o.o )  PYYYTHON
 > ^ <
"""
    print(art)


def _menu_create(base: str) -> None:
    title = input("Title: ").strip()
    priority = input("Priority (low|normal|high): ").strip()
    _print_response(_request(base, "POST", "/tasks", {"title": title, "priority": priority}))


def _menu_random(base: str) -> None:
    count_raw = input("Сколько задач создать (по умолчанию 3): ").strip()
    seed_raw = input("Seed (пусто — случайный): ").strip()
    try:
        count = int(count_raw) if count_raw else 3
    except ValueError:
        print("Некорректное число, используем 3.")
        count = 3
    seed = int(seed_raw) if seed_raw else None
    args = argparse.Namespace(base=base, count=count, seed=seed)
    cmd_random(args)


def _menu_tests(base: str) -> None:
    logfile = input("Файл для лога тестов (по умолчанию test_results.log): ").strip() or "test_results.log"
    args = argparse.Namespace(base=base, logfile=logfile)
    cmd_tests(args)


def _menu_fuzz(base: str) -> None:
    steps_raw = input("Количество шагов (по умолчанию 30): ").strip()
    seed_raw = input("Seed (пусто — случайный): ").strip()
    logfile = input("Файл для лога фузз-теста (по умолчанию fuzz_results.log): ").strip() or "fuzz_results.log"
    try:
        steps = int(steps_raw) if steps_raw else 30
    except ValueError:
        print("Некорректное число, используем 30.")
        steps = 30
    seed = int(seed_raw) if seed_raw else None
    args = argparse.Namespace(base=base, steps=steps, seed=seed, logfile=logfile)
    cmd_fuzz_run(args)


def _menu_update(base: str) -> None:
    task_id = input("Task id: ").strip()
    title = input("New title (пусто — без изменений): ").strip()
    priority = input("New priority (low|normal|high, пусто — без изменений): ").strip()
    body: Dict[str, Any] = {}
    if title:
        body["title"] = title
    if priority:
        body["priority"] = priority
    _print_response(_request(base, "PUT", f"/tasks/{task_id}", body))


def _menu_complete(base: str) -> None:
    task_id = input("Task id: ").strip()
    _print_response(_request(base, "POST", f"/tasks/{task_id}/complete"))


def _menu_delete(base: str) -> None:
    task_id = input("Task id: ").strip()
    _print_response(_request(base, "DELETE", f"/tasks/{task_id}"))


def _menu_logs(base: str) -> None:
    limit = input("Сколько последних логов показать (по умолчанию 20): ").strip()
    limit_val = int(limit) if limit else 20
    _print_response(_request(base, "GET", f"/admin/logs?limit={limit_val}"))


def _wrap(args: argparse.Namespace, **updates: Any) -> argparse.Namespace:
    """
    Удобный способ переиспользовать функции CLI в меню,
    создавая Namespace с нужными полями.
    """
    merged = vars(args).copy()
    merged.update(updates)
    return argparse.Namespace(**merged)


def _print_response(res: Dict[str, Any]) -> None:
    print(f"Status: {res.get('status')}")
    body = res.get("body")
    if body is not None:
        print(json.dumps(body, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Admin CLI for Todo HTTP server (stdlib only). Use subcommands or 'menu' for an interactive mode.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="Base URL of the Todo server")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List all tasks")
    p_list.add_argument("--limit", type=int, help="Limit number of tasks shown (client-side)")
    p_list.set_defaults(func=cmd_list)

    p_logs = sub.add_parser("logs", help="Show recent action logs")
    p_logs.add_argument("--limit", type=int, default=20, help="How many log entries to show")
    p_logs.set_defaults(func=cmd_logs)

    p_create = sub.add_parser("create", help="Create a task")
    p_create.add_argument("title")
    p_create.add_argument("priority", choices=["low", "normal", "high"])
    p_create.set_defaults(func=cmd_create)

    p_update = sub.add_parser("update", help="Update a task")
    p_update.add_argument("id", type=int)
    p_update.add_argument("--title")
    p_update.add_argument("--priority", choices=["low", "normal", "high"])
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="Delete a task")
    p_delete.add_argument("id", type=int)
    p_delete.set_defaults(func=cmd_delete)

    p_complete = sub.add_parser("complete", help="Mark a task complete")
    p_complete.add_argument("id", type=int)
    p_complete.set_defaults(func=cmd_complete)

    p_backup = sub.add_parser("backup", help="Trigger server-side backup of tasks")
    p_backup.set_defaults(func=cmd_backup)

    p_rand = sub.add_parser("random", help="Create random tasks from presets")
    p_rand.add_argument("--count", type=int, default=3, help="How many tasks to create")
    p_rand.add_argument("--seed", type=int, default=None, help="Random seed (optional)")
    p_rand.set_defaults(func=cmd_random)

    p_tests = sub.add_parser("tests", help="Run deterministic API test suite and log results")
    p_tests.add_argument("--logfile", default="test_results.log", help="Where to store test results (JSONL)")
    p_tests.set_defaults(func=cmd_tests)

    p_fuzz = sub.add_parser("fuzz", help="Run fuzz tester with logging")
    p_fuzz.add_argument("--steps", type=int, default=30, help="How many random actions to run")
    p_fuzz.add_argument("--seed", type=int, default=None, help="Random seed (optional)")
    p_fuzz.add_argument("--logfile", default="fuzz_results.log", help="Where to store fuzz results (JSONL)")
    p_fuzz.set_defaults(func=cmd_fuzz_run)

    p_menu = sub.add_parser("menu", help="Interactive menu to perform common actions")
    p_menu.set_defaults(func=cmd_menu)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

