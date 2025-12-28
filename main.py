import argparse

from http_server import TodoHTTPServer, TodoRequestHandler
from storage import TaskStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Todo HTTP server (stdlib only)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--storage", default="tasks.txt")
    args = parser.parse_args()

    store = TaskStore(args.storage)
    store.load()

    server = TodoHTTPServer((args.host, args.port), TodoRequestHandler, store)

    print(f"Server started: http://{args.host}:{args.port}")
    print("Endpoints:")
    print("  GET  /tasks")
    print('  POST /tasks              JSON: {"title":"...","priority":"low|normal|high"}')
    print("  POST /tasks/<id>/complete")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
