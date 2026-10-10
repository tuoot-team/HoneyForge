# HoneyForge

Централизованная платформа управления honeypot-ловушками (кейс UmirHack / Мадригал): профили, развёртывание, скрытый канал центр↔агент, телеметрия, dashboard.

**Цель MVP:** конструктор профилей + центр + агент (Low и Medium) + маскировка канала + realtime-лента + демо «собрал профиль → атака → событие».

Стиль кода: [`CodeStyle.md`](CodeStyle.md) (табы, дефис вместо длинного тире, debug через `.env`, UI-тексты в отдельном файле, имена вида `getOrCreate_InviteToken`).

## Оглавление

1. [Команда](#команда)
2. [Архитектура](#архитектура)
3. [Конструктор ловушек](#конструктор-ловушек)
4. [Маскировка канала (MASK / beacon)](#маскировка-канала-mask--beacon)
5. [Анти-фингерпринт ловушки](#анти-фингерпринт-ловушки)
6. [Стек](#стек)
7. [Структура репозитория](#структура-репозитория)
8. [Модули](#модули)
   - [core-api](#core-api)
   - [CLI](#cli)
   - [Web UI](#web-ui)
   - [Ханипоты](#ханипоты)
9. [Канал агента (принятые паттерны)](#канал-агента-принятые-паттерны)
10. [Must / Bonus](#must--bonus)
11. [План разработки](#план-разработки)
12. [Минимальный контракт API](#минимальный-контракт-api-якорь-cli--ui)
13. [Критерии готовности MVP](#критерии-готовности-mvp)

---

## Команда

| Участник | Зона ответственности |
|----------|----------------------|
| @potjoke | Ядро (`core-api`) + CLI |
| @propastin | Frontend (`web-panel`) + презентация |
| @SoulProtocol | Ханипоты (`honeypots`, Low/Mid/High) + агент на стороне ловушки |

---

## Архитектура

```
CLI / Web UI ──HTTP + SSE──► Control API (FastAPI) ──► PostgreSQL
                                    │                      ▲
                     config/commands│                      │ events (batch)
                                    ▼                      │
                         Агент + honeypot (Low/Mid) ───────┘
                                    ▲
              скрытый канал: TLS, front-сайт + скрытый collector, mgmt-сеть
              агент: pull + буфер + jitter/burst (+ редкий wake, без вечного WS)
```

---

## Конструктор ловушек


| Блок профиля | Содержание |
|--------------|------------|
| Уровень | Low / Medium (/ High - bonus); честный gradient без overclaim |
| Сервисы и порты | SSH, HTTP, БД… |
| Personality | не только banner: ошибки, задержки, headers/cipher hints (`service_personality`) |
| Приманки | учётки; honeytokens в «скучных» путях (bonus) |
| Логирование | credentials / payloads / source meta; timing realism |
| Маскировка / beacon | см. поля `mask` ниже |

**Поля блока `mask` (конструктор → агент):**

| Поле | Назначение |
|------|------------|
| `beacon_interval_sec` + `jitter_pct` | интервал + рандом (не фиксированные 30с) |
| `collector_path_set` | набор/ротация путей коллектора (`/v1/metrics`, `/cdn/edge-check`, …) |
| `user_agent` / `tls_fingerprint_profile` | mimicry клиента |
| `cover_urls[]` | обязательный шум: GET favicon/robots между beacon |
| `process_name` | скрытность процесса на хосте |
| `decoy_content_seed` | асимметрия инстансов при одном профиле |
| `service_personality` | ссылка/ключ personality pack (не одна строка баннера) |

**Ответственность:** схема/API - `@potjoke`; UI конструктора - `@propastin`; применение на хосте - `@SoulProtocol`.

---

## Маскировка канала (MASK / beacon)

| # | Приём | Приоритет |
|---|--------|-----------|
| 1 | Mimicry: пути вроде `/v1/metrics`, `/cdn/edge-check`, `/api/telemetry/batch`; JSON с шумовыми полями; фон - публичный «сайт» центра | Must (демо) |
| 2 | Reverse-proxy front: Nginx отдаёт статику; collector - скрытый `location`; не светить голый IP без контента | Must-ish (фаза 5) |
| 3 | Adaptive jitter + burst batching из локального буфера | Must |
| 4 | Cover traffic между beacon (`cover_urls`) | High ROI bonus / желательно к демо |
| 5 | mTLS / pinned cert; без клиентского cert → 404 или статика (fail-closed) | Bonus |
| 6 | Редкий wake / long-poll вместо **вечного** agent WebSocket | Must (дизайн) |
| 7 | Разделение plane: operator `/api/` ≠ collector; разные vhost/порт/ACL (mgmt) | Must к демо; :80 на всё - только каркас |
---

## Анти-фингерпринт ловушки

| # | Приём | Приоритет |
|---|--------|-----------|
| 1 | Protocol personality из профиля (banner + errors + delays + header/cipher hints) | Must для убедительного Mid |
| 2 | Personality packs / пресеты (`ubuntu-22.04-ssh`, `nginx-1.24-corp`, …) | Bonus (фаза 6) |
| 3 | Честный deception gradient: Low = listen/banner; Mid = ограниченный граф; High = sandbox | Must (подача) |
| 4 | Honeytokens как вторичный сигнал (`.env.bak`, CI cache), не `passwords.txt` на рабочем столе | Bonus |
| 5 | Canary asymmetry: `decoy_content_seed` → разные hostname/uptime/пакеты при одном профиле | Желательно |
| 6 | Living neighborhood: соседи, rDNS, TLS SAN на стенде | Стенд/защита, не ядро |
| 7 | Timing realism: auth delay, I/O pause, редкие 502 | High ROI для Mid |

---

## Стек

| Слой | Технологии |
|------|------------|
| Control API | Python 3.11+, FastAPI, доменная нарезка (`domains/` + `api/v1/`) |
| Realtime | оператор: **SSE**; агент: pull + редкий wake/long-poll (без вечного WS) |
| БД | PostgreSQL (+ Redis: очередь/лимиты/pubsub по необходимости) |
| Web UI | HTML/CSS/JS (+ лёгкий фреймворк), Chart.js |
| Прокси | Nginx (TLS, reverse-proxy, маскировка mgmt/collector, раздача артефактов) |
| Агент / honeypot | Python; тонкий агент (HTTP + опц. WS); honeypots Low/Mid |
| Доставка агента | install-скрипт / бинарь под Nginx `/downloads/` (не только SSH) |
| Инфра | Docker / docker-compose (центр); агент - на хосте ловушки |
| CLI | Python, HTTP-клиент API (первый операторский фронт) |

---

## Структура репозитория

```
HoneyForge/
├── README.md
├── CodeStyle.md
├── build_win.ps1 / build_linux.ps1
├── build/
└── source/
    ├── core-api/          # FastAPI: auth, конструктор профилей (API), traps, agent, events, SSE
    ├── cli/               # pair / profile build / traps / events tail → API
    ├── web-panel/         # dashboard + UI конструктора профилей
    └── honeypots/
        ├── low/
        ├── mid/
        └── high/          # bonus
```
---

## Модули

### core-api

| | |
|-|-|
| **Ответственный** | @potjoke |
| **Путь** | `source/core-api/` |
| **Стек** | FastAPI, PostgreSQL, Redis (опц.), SSE, WS wake для агента, Nginx, compose; `.env` + `DEBUG` |

**Реализовать:** cookie/token auth; **модель профиля + CRUD**; валидация блоков вкл. расширенный `mask` / personality; pairing → `agent_token`; bind; heartbeat; `get config` / claim; batch events; **SSE**; пути коллектора под mimicry; OpenAPI; (bonus) оркестратор, алерты, IoC, mTLS fail-closed.

### CLI

| | |
|-|-|
| **Ответственный** | @potjoke |
| **Путь** | `source/cli/` |
| **Стек** | Python; только HTTP/SSE к API |

**Реализовать:** login; **конструктор в CLI** (`profile create/edit/show` - уровень, сервисы, баннеры, креды); `pair` / confirm; bind profile; traps; `events` + `tail`; заготовка deploy. Без своей БД и без прямой связи с агентами.

### Web UI

| | |
|-|-|
| **Ответственный** | @propastin |
| **Путь** | `source/web-panel/` |
| **Стек** | HTML/CSS/JS (+ лёгкий фреймворк), Chart.js, SSE; пароль из `.env` |

**Реализовать:** login; **UI конструктора** (уровень → сервисы → personality/баннеры → креды → logging/`mask` вкл. jitter, cover_urls, path_set → save); pairing; dashboard + bind; SSE-лента; графики; UI-тексты отдельно; **презентация** (конструктор + маскировка канала). Один ops-dashboard; лёгкая «маркетинг»-статика на front Nginx - для маскировки, не multi-site SaaS.

### Ханипоты

| | |
|-|-|
| **Ответственный** | @SoulProtocol |
| **Путь** | `source/honeypots/` |
| **Стек** | Python; тонкий агент; Docker/изоляция |

**Реализовать:** агент применяет профиль (сервисы + `mask`: jitter/burst, cover traffic, path rotation); **буфер** + досылка; скрытный `process_name`; Low + Mid с personality/timing; `decoy_content_seed`; install-артефакт. (bonus) High-sandbox, honeytokens в скучных путях, пресеты personality packs.

---

## Канал агента (принятые паттерны)

Что **берём в реализацию** (адаптируем под honeypot, не копируем чужой домен):

| Паттерн | Зачем нам |
|---------|-----------|
| Device-code pairing → `agent_token` | Удобный enrollment без ручного копирования секретов; демо «добавить ловушку» |
| Heartbeat + stale → last-seen | Статусы online/offline в CLI/UI |
| Pull/claim + редкий wake | Центр→агент без вечного WS |
| Batch events + burst | Телеметрия пачками из буфера |
| Mimicry paths + шумный JSON | Канал как CDN/API telemetry |
| SSE оператору | CLI `tail` и Web UI; агенту браузерный WS не нужен |
| Front Nginx (статика + скрытый location) | Collector не голый IP |
| Split plane operator ≠ collector | К демо маскировки |
| Тонкий агент | asyncio/HTTP; проще маскировать |
| Compose + TLS + `/downloads/` | Воспроизводимый центр |
| Демо-петля 5 шагов | Профиль → атака → событие |

Что **не тащим** в MVP:

- Свободный remote-shell / OS-diagnostics как суть продукта
- Telegram и multi-site marketing-SaaS
- Вечный agent WebSocket
- Очевидные `/api/honeypot` / голый `/agent/*`
- Always-online без буфера
- High без sandbox; overclaim Mid как High
- Полноценный CDN domain-fronting (дорого, мало ROI)

---

## Must / Bonus

**Must:** конструктор (порты **и** `mask`/personality); pairing + bind; конфиг↔телеметрия; события + фильтры; auth; Low+Mid по профилю (честный gradient); буфер + jitter/burst; mimicry paths; без вечного agent WS; split plane к демо; CLI/UI лента; демо «профиль → атака → событие».

**Bonus:** cover traffic; personality packs; `decoy_content_seed` asymmetry; honeytokens в скучных путях; mTLS fail-closed; High-sandbox; SSH/Docker оркестратор; алерты/IoC; living neighborhood на стенде.

---

## План разработки

### Фаза 0 - Каркас
- [x] docker-compose: Postgres (+ Redis), Nginx-заготовка, FastAPI skeleton (`domains/`, `api/v1/`) - `source/core-api/`
- [x] `.env` + `DEBUG`; таблицы: **profiles** (JSON/блоки конструктора), traps/agents, pairing, events, audit
- [x] OpenAPI: profiles schema + остальной контракт CLI/UI (stubs `501` до фазы 1)

### Фаза 1 - Control API (+ бэкенд конструктора)
- [x] Auth оператора (Bearer HMAC, пароль из `.env`)
- [x] **Схема профиля** + расширенный `mask` / logging / personality + validate
- [x] CRUD профилей; version/hash конфига
- [x] Pairing (start/confirm/complete) + **bind profile**
- [x] `get config`; claim commands (`reload_config`)
- [x] Heartbeat; batch events; фильтры; SSE `/events/stream`
- [x] Mimicry-пути: `/v1/metrics`, `/cdn/edge-check`, `/api/telemetry/batch`
- Локально без Docker: `USE_SQLITE=true` + `python scripts/smoke_phase1.py`

### Фаза 2 - Агент + honeypots (применение профиля)
- [ ] Агент: pair, pull, **буфер + jitter/burst**, досылка, `process_name`
- [ ] Cover traffic по `cover_urls` (если успеем)
- [ ] Low/Mid: порты + personality/timing + seed асимметрии → события
- [ ] Reload профиля без переустановки
- [ ] Install → `/downloads/`; E2E профиль → событие

### Фаза 3 - CLI (конструктор + ops)
- [ ] login; **`profile create/edit/list/show`**
- [ ] pair, bind, traps, events, `tail`
- [ ] Стоп-критерий: собрать профиль и увидеть атаку без Web UI

### Фаза 4 - Web panel (UI конструктора)
- [ ] **Мастер/форма конструктора** на том же Profiles API
- [ ] Dashboard, pairing, bind профиля, SSE-лента
- [ ] Пароль из `.env`

### Фаза 5 - Маскировка и демо
- [ ] Front-статика + скрытый collector location; JSON с шумом
- [ ] Split plane: operator API ≠ collector (vhost/порт/ACL)
- [ ] Fail-closed на чужой доступ к collector (404/статика)
- [ ] Сценарий: профиль (порты + mask) → атака → событие; гайд 5 шагов
- [ ] Презентация: конструктор + «канал как CDN/API», честный Low/Mid

### Фаза 6 - Bonus
- [ ] Personality packs; cover traffic (если не в фазе 2); honeytokens «скучные»
- [ ] mTLS / pin; SSH/Docker оркестратор; алерты/IoC
- [ ] High-sandbox; living neighborhood на стенде

---

## Минимальный контракт API (якорь CLI = UI)

| Область | Операции |
|---------|----------|
| Auth | login / logout / me |
| Profiles (конструктор) | CRUD; get schema/blocks; validate; list; (bonus) presets |
| Pairing / Traps | start, confirm, complete; list; status; **bind profile** |
| Agent / collector | heartbeat/beacon; **get config**; claim/pull; post events (batch); редкий wake (не вечный WS) |
| Events | list + filters; **SSE subscribe** |
| Artifacts | download agent install; (bonus) remote deploy |

Пути коллектора - mimicry (`/v1/metrics`, `/cdn/edge-check`, …), без `honeypot` / явного `c2`. Operator API и collector разведены к демо.

---

## Критерии готовности MVP

1. `docker-compose up` поднимает центр  
2. В конструкторе (CLI или Web) собран и сохранён профиль  
3. Агент проходит pairing и получает профиль (`get config`)  
4. ≥2 ловушки (Low + Medium) по профилю шлют телеметрию  
5. Событие атаки видно в CLI/UI near-realtime (SSE)  
6. Канал похож на легитимный HTTPS (mimicry / front), не на явный C2  
7. Потеря связи не теряет события (буфер + burst)  
8. На защите честно обозначен уровень Low/Mid (без overclaim High)

---
