# Todo HTTP Server (stdlib-only)

HTTP ToDo-сервер без внешних зависимостей. Поддерживает хранение задач, отметку выполнения, обновление/удаление, логи действий, резервные копии, админ-CLI, тест-раннер и фузз-тестер.

## Запуск сервера
```bash
python main.py --host 127.0.0.1 --port 8000 --storage tasks.txt --logfile logs.txt
```
При старте восстанавливает задачи из `tasks.txt`, после каждой изменяющей операции сохраняет обратно. Логи действий пишутся в `logs.txt`.

## API эндпоинты
- `GET /tasks` — список задач.
- `POST /tasks` — создать `{ "title": "...", "priority": "low|normal|high" }`.
- `PUT /tasks/<id>` — обновить title/priority (любые поля можно опустить).
- `POST /tasks/<id>/complete` — отметить выполненной.
- `DELETE /tasks/<id>` — удалить.
- `GET /admin/logs?limit=N` — последние N записей действий.
- `POST /admin/backup` — резервная копия `tasks.txt` в `backups/` с таймстампом.

## Админ-CLI
Запуск интерактивного меню:
```bash
python cli/admin_cli.py menu
```
Основные подкоманды (без меню):
- `list [--limit N]`
- `create "Title" priority`
- `update ID [--title ...] [--priority ...]`
- `complete ID`
- `delete ID`
- `logs [--limit N]`
- `backup`
- `random --count N [--seed S]` — создать задачи из пресетов.
- `tests [--logfile test_results.log]` — прогон детерминированных API тестов.
- `fuzz [--steps N --seed S --logfile fuzz_results.log]` — фузз-тестирование.

## Тесты и фузз
- Детерминированный раннер: `python tests/test_runner.py --base http://127.0.0.1:8000 --logfile test_results.log`
- Фузз: `python tests/fuzz_tester.py --base http://127.0.0.1:8000 --steps 30 --seed 42 --logfile fuzz_results.log`
Оба пишут отдельные JSONL-логи, действия параллельно отражаются в `logs.txt`.

## Логи и бэкапы
- `logs.txt` — action-лог (create/update/delete/complete).
- `test_results.log`, `fuzz_results.log` — результаты тестов/фузза.
- `backups/` — копии `tasks.txt` c таймстампом.

## Соответствие ТЗ
- Только стандартная библиотека Python.
- CRUD и complete для задач, выдача списка, сохранение в файл, восстановление при старте.
- Дополнительно: обновление и удаление, логи действий с origin, админ-CLI, бэкап, тест-раннер и фузз-генератор.

