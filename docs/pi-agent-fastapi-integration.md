# FastAPI + pi-coding-agent (RPC) — краткий гайд

## 1. Установка и запуск в FastAPI
1) Установить пакет:
   ```bash
   npm install -g @mariozechner/pi-coding-agent
   ```
2) Настроить ключи провайдера и окружение (пример):
   ```bash
   export ANTHROPIC_API_KEY=...
   ```
3) Запустить FastAPI (ключи должны быть видны воркерам):
   ```bash
   uvicorn app:app --workers 4 --host 0.0.0.0 --port 8000
   ```
4) В коде FastAPI стартовать `pi` как subprocess:
   - `asyncio.create_subprocess_exec("pi", "--mode", "rpc", "--session-dir", "...")`
   - писать JSON‑команды в stdin
   - читать JSON‑события из stdout

## 2. Как работает RPC
- `pi --mode rpc` читает JSON-команды из stdin и пишет JSON-события в stdout.
- `prompt` запускает агента.
- Ответ читается как поток `message_update` с `text_delta`.
- По завершении приходит `agent_end`.

## 3. Базовая интеграция (одиночный запрос)
- Поднимаете процесс `pi` через `asyncio.create_subprocess_exec`.
- Отправляете `{"type":"prompt","message":"..."}`.
- Собираете `text_delta` до `agent_end`.

## 4. Сессии (например, Telegram)
- Держите `chat_id -> session_path` в Redis/БД.
- При каждом запросе:
  - если сессия уже есть → `switch_session`
  - если нет → `new_session`, затем `get_state` и сохранить `sessionFile`
- Сессии сохраняются на диск через `--session-dir`.

## 5. Процессы и воркеры FastAPI
### Лучший старт
- 1 процесс `pi` на воркер FastAPI.
- Все запросы внутри воркера сериализуются (очередь).

### Если чатов сотни
- Не поднимать процесс на каждый чат.
- Использовать пул процессов (5–20) + `switch_session`.
- Воркеры FastAPI не делят память — пул лучше вынести в отдельный сервис.

## 6. Рекомендованная архитектура
### Минимальная
FastAPI (n воркеров) → 1 `pi` процесс внутри каждого воркера.

### Масштабируемая
FastAPI → отдельный agent-service → пул `pi` процессов.

## Итог
- RPC — JSON протокол поверх stdin/stdout.
- Сессии обязательны для чат-ботов: `switch_session` на каждый запрос.
- При нескольких воркерах FastAPI не дублируйте большие пулы внутри каждого.
- Начните с 1 `pi` на воркер, при росте нагрузки вынесите в отдельный сервис.
