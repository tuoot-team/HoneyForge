# core-api

**Ответственный:** @potjoke  
**Стек:** Python 3.11+, FastAPI, PostgreSQL, SSE / WS wake, Nginx, docker-compose

Ядро: Control API, **бэкенд конструктора профилей**, коллектор, realtime.

**Конструктор (API):** схема блоков профиля (уровень, services/ports, banners, credentials, logging, mask) → CRUD → validate → hash/version → bind к ловушке → `get config` агенту.

**Также:** auth; pairing → token; heartbeat/last-seen; claim commands; batch events; фильтры; SSE; маскировка путей; OpenAPI. Bonus: SSH/Docker deploy, алерты, IoC, пресеты.
