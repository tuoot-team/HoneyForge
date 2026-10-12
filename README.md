# HoneyForge

Центр управления honeypot-ловушками: профиль задаёт сервисы и маскировку канала, агент применяет его на хосте и шлёт события обратно.

Оператор работает через CLI или web-панель. Агент сам ходит в центр (heartbeat, конфиг, пачка событий), держит буфер и не держит постоянный WebSocket.

## Команда

| Участник | Зона |
|----------|------|
| @potjoke | `source/core-api`, `source/cli` |
| @propastin | `source/web-panel` |
| @SoulProtocol | `source/honeypots` |

## Как устроено

```
CLI / Web  --HTTP + SSE-->  Control API  -->  PostgreSQL
                                |                  ^
                         config / commands         | events
                                v                  |
                         Агент + honeypot  --------+
```

Канал агента маскируется под обычный HTTPS: heartbeat на `/v1/metrics` и `/cdn/edge-check`, события на `/api/telemetry/batch`. Операторский API живёт отдельно, под `/api/`.

## Профиль

Уровень считается из включённых модулей и должен совпасть с `interaction_level`.

| Уровень | Когда |
|---------|--------|
| Low | только баннер (SSH без auth и shell, либо TCP banner) |
| Medium | auth, shell или HTTP |
| High | emulation. Схема такой профиль отклоняет |

| Блок | Содержание |
|------|------------|
| Сервисы | SSH, HTTP, TCP banner. У каждого свои слоты |
| Модули | SSH: banner, auth, shell. HTTP: personality, auth, routes. TCP: banner |
| Учётки | общий пул с `id`. Auth ссылается на него через `credential_ids` |
| Логирование | credentials, payloads, source meta. Задержка входа живёт в `modules.auth` |
| `mask` | способы сокрытия канала, каждый со своим `enabled` |

Режимы auth: `allow_all`, `allow_listed`, `second_attempt_sticky`.

`second_attempt_sticky` отклоняет первую подходящую попытку с IP. Со второй пускает и запоминает эту пару логин/пароль. Дальше с этого IP проходит только она, пока не истечёт TTL. Если `credential_ids` задан, подходит только пароль из пула. Пустой список на sticky означает любой пароль со второй попытки. Shell без auth недопустим.

| Способ `mask` | Назначение |
|---------------|------------|
| `jitter` | интервал beacon и процент разброса. Выключен - пауза ровная |
| `cover` | лишние GET между beacon |
| `path_rotation` | heartbeat по очереди на `/v1/metrics` и `/cdn/edge-check` |
| `mimicry` | User-Agent и профиль TLS |
| `process_mask` | имя процесса на хосте ловушки |
| `decoy_content_seed` | разные мелочи контента при одном профиле |
| `service_personality` | ключ personality pack |

Старый плоский `mask` (`jitter_pct`, `cover_urls` и остальные поля) при чтении раскладывается по этим способам.

Пример: `source/honeypots/examples/medium-ssh-http.json`.

## План разработки

### Фаза 0 - Каркас
- [x] docker-compose: Postgres (+ Redis), Nginx-заготовка, FastAPI (`domains/`, `api/v1/`)
- [x] `.env` + `DEBUG`; таблицы profiles, traps, pairing, events, audit
- [x] OpenAPI

### Фаза 1 - Control API
- [x] Auth оператора (Bearer, пароль из `.env`)
- [x] Схема профиля, валидация блоков, CRUD, version/hash
- [x] Pairing и bind profile
- [x] `get config`, claim `reload_config`
- [x] Heartbeat, batch events, фильтры, SSE `/events/stream`
- [x] Mimicry-пути: `/v1/metrics`, `/cdn/edge-check`, `/api/telemetry/batch`
- Локально без Docker: `USE_SQLITE=true` и `python scripts/smoke_phase1.py`

### Фаза 2 - Агент и ловушки
- [x] Агент: pair, pull, буфер, jitter, досылка, `process_mask`
- [x] Способы `mask`: jitter, cover, path_rotation, mimicry
- [x] Low/Mid по слотам профиля, timing, `decoy_content_seed`
- [x] Reload профиля без переустановки
- [x] Бинарь и `install.sh` в `/downloads/`. 

### Фаза 3 - CLI
- [x] login, profile create/edit/list/show, мастер `setup`
- [x] Постановка агента по SSH из `setup` и `deploy`: IP, логин, пароль, порт
- [x] pair, bind, traps, events, `tail`
- [x] Стоп-критерий: собрать профиль и увидеть атаку без Web UI

### Фаза 4 - Web panel
- [ ] Мастер конструктора на том же Profiles API
- [ ] Dashboard, pairing, bind профиля, SSE-лента
- [ ] Пароль из `.env`

### Фаза 5 - Маскировка и демо
- [ ] Статика снаружи, коллектор в скрытом location
- [ ] Operator API и collector на разных vhost/портах
- [ ] Чужой запрос к коллектору получает 404 или страницу
- [ ] Гайд: профиль, атака, событие. Честный Low/Mid

### Фаза 6 - Bonus
- [ ] Personality packs, honeytokens
- [ ] mTLS, SSH/Docker оркестратор, алерты и IoC
- [ ] High-sandbox
