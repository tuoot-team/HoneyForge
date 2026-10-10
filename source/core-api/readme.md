# core-api

**Ответственный:** @potjoke  
**Стек:** Python 3.12 (Docker) / 3.14 локально, FastAPI, PostgreSQL или SQLite, Redis, Nginx

## Фаза 1 (готово)

- Auth: `POST /api/v1/auth/login` → Bearer token
- CRUD профилей конструктора + `config_version` / `config_hash`
- Pairing: start → list → confirm → complete → `agent_token`
- Agent: heartbeat, config, events batch, claim commands
- Events: list/filters + SSE `/api/v1/events/stream`
- Mimicry collector: `/v1/metrics`, `/cdn/edge-check`, `/api/telemetry/batch`

## Без Docker (SQLite)

```powershell
cd source/core-api
copy .env.example .env
# в .env: USE_SQLITE=true
python -m pip install -r requirements.txt
python scripts/smoke_phase1.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: http://127.0.0.1:8000/docs

### Как авторизоваться в Swagger (/docs)

1. Вызвать `POST /api/v1/auth/login`, body: `{"password": "<OPERATOR_PASSWORD из .env>"}`.
2. Из ответа скопировать только значение `access_token` (длинная строка вида `1739....xxxxx`).
3. Нажать **Authorize** (замок), вставить токен **без** префикса `Bearer `.
4. Confirm → дальше `POST /api/v1/profiles/` и остальные операторские методы.

Важно:
- Агентский `agent_token` / `X-Agent-Token` для профилей не подходит - нужен операторский после login.
- Если в Authorize вставить уже с `Bearer `, получится двойной префикс и 401.
- Ответ `нужна авторизация` = заголовок не ушёл или без Bearer.  
  Ответ `недействительный токен` = токен битый/просрочен или сменился `OPERATOR_TOKEN_SECRET` (перелогинься).

Пример вручную (curl):

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"change-me\"}" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://127.0.0.1:8000/api/v1/profiles/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"mid-ssh\",\"interaction_level\":\"medium\",\"blocks\":{\"services\":[{\"name\":\"ssh\",\"port\":22}]}}"
```

## С Docker (Postgres)

В `.env`: `USE_SQLITE=false`. Compose сам выставит хост БД.

```bash
docker compose up --build
```

## Дальше

Фаза 2: агент + honeypots (применение профиля, буфер, jitter).  
Фаза 3: CLI.
