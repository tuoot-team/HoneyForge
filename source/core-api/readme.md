# core-api

**Ответственный:** @potjoke  
**Стек:** Python 3.12 (Docker) / 3.14 локально, FastAPI, PostgreSQL или SQLite, Redis, Nginx

## Фаза 1 (готово)

- Auth: `POST /api/v1/auth/login` → Bearer token
- CRUD профилей конструктора + `config_version` / `config_hash`
- Pairing: start → confirm → complete → `agent_token`
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

## С Docker (Postgres)

В `.env`: `USE_SQLITE=false`. Compose сам выставит хост БД.

```bash
docker compose up --build
```

## Дальше

Фаза 2: агент + honeypots (применение профиля, буфер, jitter).  
Фаза 3: CLI.
