
from __future__ import annotations

import argparse

from services.action_log import ActionLogger
from api.http_server import TodoHTTPServer, TodoRequestHandler
from services.storage import TaskStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Todo HTTP server (stdlib-only).")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--storage", default="tasks.txt", help="Path to tasks file (default: tasks.txt)")
    parser.add_argument("--logfile", default="logs.txt", help="Path to action log file (default: logs.txt)")
    args = parser.parse_args()

    logger = ActionLogger(args.logfile)
    store = TaskStore(args.storage, logger=logger)
    store.load()  # восстановление при старте :contentReference[oaicite:10]{index=10}

    server = TodoHTTPServer((args.host, args.port), TodoRequestHandler, store)
    print(f"Server started: http://{args.host}:{args.port}")
    print("Endpoints:")
    print("  GET  /tasks")
    print("  POST /tasks              JSON: {\"title\":\"...\",\"priority\":\"low|normal|high\"}")
    print("  POST /tasks/<id>/complete")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
