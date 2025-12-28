# HTTP Server (stdlib only)

HTTP-сервер для управления списком дел.

## Формат задачи

- title: (str)
- priority: "low" | "normal" | "high" (str)
- isDone: выполнено ли дело (bool)
- id: (int)

## API

- GET /tasks
  - Возвращает список задач в JSON.

- POST /tasks
  - Тело: {"title": "...", "priority": "low|normal|high"}
  - Возвращает созданную задачу в JSON.

- POST /tasks/<id>/complete
  - Отмечает задачу выполненной.
  - Возвращает пустое тело и код 200 при успехе, 404 если задачи нет.

## Хранение

- После каждого запроса, который меняет список задач, данные сохраняются в файл tasks.txt.
- При старте сервер читает tasks.txt, если файл существует.

Файл tasks.txt хранит JSON-массив задач.

## Запуск

python main.py --host 127.0.0.1 --port 8000 --storage tasks.txt

## Примеры запросов

Создать задачу:
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Gym\",\"priority\":\"low\"}"

Список задач:
curl http://127.0.0.1:8000/tasks

Завершить задачу:
curl -X POST http://127.0.0.1:8000/tasks/1/complete
