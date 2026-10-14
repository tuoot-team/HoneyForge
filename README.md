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

Канал агента идёт на порт 80, туда же отдаётся обычная страница. Heartbeat на `/v1/metrics` и `/cdn/edge-check`, события на `/api/telemetry/batch`. Без заголовка `X-Agent-Token` эти пути отвечают страницей 404. Операторский API слушает порт 8088.

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

## Пакеты файловой системы (fake shell)

Для SSH shell можно подставить дерево из архива вместо встроенного `ubuntu-22.04`.

| Значение `modules.shell.fs_pack` | Поведение |
|----------------------------------|-----------|
| пусто / `ubuntu-22.04` / `builtin` | встроенное дерево агента |
| `fsp_...` | агент скачивает архив с центра и разворачивает в память |

Оператор загружает `.zip` или `.tar.gz` / `.tgz` (лимит **32 MiB**) через CLI:

- `fs-pack-upload --file PATH [--name N]`
- `fs-pack-list` / `fs-pack-delete TOKEN`
- в мастере `setup` после shell: без FS / создать / взять существующий

Архивы лежат в `source/core-api/fs-packs/` (в git не коммитятся). Агент кэширует рядом с data dir в `.fs_packs/{token}`.

Тестовое дерево: `source/fs/ubuntu-lab/` (готовые `ubuntu-lab.tar.gz` / `ubuntu-lab.zip`).

## План разработки

### Фаза 0 - Каркас
- [x] docker-compose: Postgres, Nginx-заготовка, FastAPI (`domains/`, `api/v1/`)
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
- [x] Постановка агента по SSH через Control API (`POST /api/v1/deploy/agent`); CLI `setup`/`deploy` вызывают тот же эндпоинт
- [x] pair, bind, traps, events, `tail`
- [x] Стоп-критерий: собрать профиль и увидеть атаку без Web UI

### Фаза 4 - Web panel
- [ ] Login, конструктор профилей на Profiles API, pairing/bind, traps, SSE-лента
- [ ] Приоритеты в ленте событий: типы ранжируются (например `shell_command` / auth success выше `banner_grab` / `port_connect`); UI и CLI `tail` показывают уровень, фильтр «только важное»
- [ ] Стоп-критерий: демо-петля без CLI (login → профиль → pair/bind → событие в ленте)
- [ ] API base из `.env` (логин до фазы 4b может быть временным bootstrap)

### Фаза 4b - Аккаунты и роли
- [x] Пользователи центра: создание админом, логин username+password, токен с user id (bootstrap из `OPERATOR_USERNAME`/`OPERATOR_PASSWORD`)
- [x] Встроенные роли admin / operator / viewer и superadmin
- [x] Главный админ создаёт кастомные роли и задаёт набор прав
- [x] Проверка прав на operator-эндпоинтах API; web скрывает действия по `/auth/me` (зона web)
- [x] Аудит write-действий с actor=username
- [x] Стоп-критерий: viewer 403 на write; кастомная роль с урезанными правами

### Фаза 5a - Маскировка канала (сделано)
- [x] Статика снаружи, коллектор в скрытом location
- [x] Operator API (`:8088`) и канал агента (`:80`) на разных портах
- [x] Чужой запрос к коллектору получает страницу 404
- [x] Low = баннер, Medium = вход / shell / HTTP

### Фаза 5b - Anti-detect medium (под пентестеров)
- [ ] Процесс и пути агента без маркеров honeypot/C2; демо-профиль с cover и path_rotation
- [ ] SSH handshake ближе к OpenSSH (KEX/cipher/MAC), `nmap -sV` не показывает Go / голое 2.0
- [ ] Согласованность fake shell (uname/os-release/FS), правдоподобные отказы wget/curl/ldd без выхода в сеть
- [ ] Стоп-критерий: пентест-smoke (nmap, ps, /proc, SSH_CLIENT, strings агента)

### Фаза 5c - Курьер (второй способ сбора логов)
- [ ] Режим `collection_mode=agent|courier`: в courier ловушка не шлёт batch сама
- [ ] Отдельный агент-сборщик на другом хосте: задание с центра → короткий визит на ловушку → забор буфера → чистка своих следов → сдача в ядро
- [ ] CLI: courier create/list/deploy, выбор режима в setup
- [ ] Стоп-критерий: события в центре без исходящего C2 с ловушки, без дублей и без следа визита курьера

### Фаза 5d - Mid-honeynet на одном сервере
- [ ] Не несколько реальных машин, а связка medium-сервисов на одном агенте: общие/связанные креды, bait-файлы и URL на «соседние» порты того же хоста
- [ ] В профиле набор сервисов как мини-парк (SSH + HTTP + БД) с согласованной легендой и honeytoken-переходами
- [ ] Корреляция в центре: сессии с одного source IP по разным портам ловушки видны как цепочка
- [ ] Без netns/VM на этом шаге (настоящий мультихост - зона High 6b)
- [ ] Стоп-критерий: пентестер с SSH находит указание на веб/БД на том же хосте, заходит туда теми же/связанными кредами, в ленте видна цепочка с высоким приоритетом

### Фаза 6a - Honeytokens
- [ ] Токены в профиле (файл / URL / ключ / креды), событие `honeytoken_hit`
- [ ] Раздача через fake FS и HTTP; показ в ленте CLI/web

### Фаза 6b - High: VM с пересобранными образами
- [ ] Полноценные VM (KVM/libvirt) на серверах-ловушках, не контейнер-заглушка
- [ ] Пайплайн пересборки образов без бренда HoneyForge; изоляция от прод-сети
- [ ] Snapshot revert по TTL/команде; запись сессии (I/O, файлы) в центр
- [ ] Телеметрия тем же `agent|courier`; снять запрет `interaction_level=high` когда пайплайн готов
- [ ] Стоп-критерий: boot из своего образа → реальный shell → события в центре → revert

### Фаза 6c - Infra хвост
- [ ] mTLS агент/курьер ↔ центр
- [ ] Алерты по порогам с учётом приоритета события (важное → уведомление раньше шума banner_grab)
- [ ] IoC-экспорт (CSV; STIX по остатку)
- [ ] Personality packs как пресеты
