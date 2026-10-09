# HoneyForge

Централизованная платформа управления honeypot-ловушками (кейс UmirHack / Мадригал): профили, развёртывание, скрытый канал центр↔агент, телеметрия, dashboard.

**Цель MVP:** конструктор профилей + центр + агент (Low и Medium) + маскировка канала + realtime-лента + демо «собрал профиль → атака → событие».

Стиль кода: [`CodeStyle.md`](CodeStyle.md) (табы, дефис вместо длинного тире, debug через `.env`, UI-тексты в отдельном файле, имена вида `getOrCreate_InviteToken`).

## Оглавление

1. [Команда](#команда)
2. [Архитектура](#архитектура)
3. [Конструктор ловушек](#конструктор-ловушек)
4. [Стек](#стек)
5. [Структура репозитория](#структура-репозитория)
6. [Модули](#модули)
   - [core-api](#core-api)
   - [CLI](#cli)
   - [Web UI](#web-ui)
   - [Ханипоты](#ханипоты)
7. [Канал агента (принятые паттерны)](#канал-агента-принятые-паттерны)
8. [Must / Bonus](#must--bonus)
9. [План разработки](#план-разработки)
10. [Минимальный контракт API](#минимальный-контракт-api-якорь-cli--ui)
11. [Критерии готовности MVP](#критерии-готовности-mvp)

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
              скрытый канал: TLS, неприметные пути, mgmt-сеть
              агент: heartbeat + pull (+ WS wake) + локальный буфер
```

Три контура: **центр** | **парк ловушек (DMZ)** | **канал управления**.

**Клиенты:** CLI и Web UI - тонкие оболочки одного API. Логика канала только в `core-api`.

**Демо-петля (must):** конструктор (собрать профиль) → pairing агента → bind профиля → атака на ловушку → событие в CLI/UI.

---

## Конструктор ловушек

Редактор **профилей** (шаблонов), не генератор кода. Оператор собирает конфиг из блоков; эмуляторы Low/Mid уже реализованы в `honeypots` и **параметризуются** профилем.

| Блок профиля | Содержание |
|--------------|------------|
| Уровень | Low / Medium (/ High - bonus) |
| Сервисы и порты | SSH, HTTP, БД… |
| Внешний вид | баннеры, версии, тексты ответов/ошибок |
| Приманки | учётки, файлы, honeytokens (bonus) |
| Логирование | что писать в события |
| Маскировка / beacon | интервалы, параметры канала для агента |

**Поток:** создать/править профиль (CLI или Web) → сохранить в PG → bind к ловушке → агент `get config` → поднять/обновить сервисы → телеметрия идёт в центр.

**Не входит в MVP:** drag-and-drop карты сети; генерация произвольного Python; замена самих эмуляторов конструктором.

**Ответственность:** схема и API профилей - `@potjoke` (`core-api` + CLI); UI конструктора - `@propastin`; применение конфига на хосте - `@SoulProtocol`.

---

## Стек

| Слой | Технологии |
|------|------------|
| Control API | Python 3.11+, FastAPI, доменная нарезка (`domains/` + `api/v1/`) |
| Realtime | агент: WebSocket wake; оператор: **SSE** лента событий (+ polling в CLI) |
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

Артефакты агента (install.sh / пакет) отдаются через Nginx (каталог downloads в compose-стеке центра).

---

## Модули

### core-api

| | |
|-|-|
| **Ответственный** | @potjoke |
| **Путь** | `source/core-api/` |
| **Стек** | FastAPI, PostgreSQL, Redis (опц.), SSE, WS wake для агента, Nginx, compose; `.env` + `DEBUG` |

**Реализовать:** cookie/token auth; **модель профиля + CRUD (бэкенд конструктора)**; валидация блоков (уровень, сервисы, порты, баннеры, креды, logging, mask); **device-code pairing** → `agent_token`; bind profile → trap; heartbeat → last-seen; `get config` / claim commands; batch events; фильтры; **SSE**; неприметные пути; OpenAPI; (bonus) оркестратор, алерты, IoC.

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

**Реализовать:** login; **UI конструктора** (форма/мастер профиля: уровень → сервисы/порты → баннеры → креды → logging/mask → save); pairing (код/QR); dashboard ловушек + bind профиля; realtime-лента; графики; UI-тексты отдельно; **презентация**. Один ops-dashboard, без marketing multi-site.

### Ханипоты

| | |
|-|-|
| **Ответственный** | @SoulProtocol |
| **Путь** | `source/honeypots/` |
| **Стек** | Python; тонкий агент; Docker/изоляция |

**Реализовать:** агент применяет **скачанный профиль** (какие порты/сервисы поднять, баннеры, креды); pairing, heartbeat, config pull, **буфер**, досылка, скрытность; Low + Medium как параметризуемые эмуляторы; install-артефакт. (bonus) High, honeytokens, jitter, анти-фингерпринт.

---

## Канал агента (принятые паттерны)

Что **берём в реализацию** (адаптируем под honeypot, не копируем чужой домен):

| Паттерн | Зачем нам |
|---------|-----------|
| Device-code pairing → `agent_token` | Удобный enrollment без ручного копирования секретов; демо «добавить ловушку» |
| Heartbeat + stale → last-seen | Статусы online/offline в CLI/UI |
| Pull/claim команд + опц. WS wake | Центр→агент: конфиг, start/stop, ротация; без постоянного push-only |
| Batch post events | Ловушка→центр: телеметрия атак |
| SSE лента оператору | Один поток для CLI `tail` и Web UI; агенту WS не обязателен в браузере |
| Тонкий агент | Мало модулей, asyncio/HTTP; проще маскировать и сопровождать |
| Compose + Nginx TLS + `/downloads/` | Воспроизводимый центр + понятная установка агента |
| Домены FastAPI (`domains/` + versioned API) | Чистый контракт для CLI и UI |
| Демо-петля в README запуска | 5 шагов до «атака → событие», не только схемы |

Что **не тащим** в MVP:

- Свободный remote-shell / OS-diagnostics как суть продукта
- Telegram и multi-site marketing-портал
- Community, рейтинги, diff отчётов «для галочки»
- Очевидные пути вида `/api/honeypot` или голый `/agent/*` без маскировки
- Ожидание always-online без буфера (буфер - наш Must)

---

## Must / Bonus

**Must:** **конструктор профилей** (API + CLI + Web); pairing + статусы; bind профиля; конфиг↔телеметрия; события в PG с фильтрами; auth; Low+Medium по профилю; буфер агента; MASK; CLI/UI лента; демо «профиль → атака → событие».

**Bonus:** деплой SSH/Docker одной кнопкой; алерты/IoC; High; honeytokens в конструкторе; jitter; mTLS; анти-фингерпринт; пресеты профилей «из коробки».

---

## План разработки

### Фаза 0 - Каркас
- [ ] docker-compose: Postgres (+ Redis), Nginx-заготовка, FastAPI skeleton (`domains/`, `api/v1/`)
- [ ] `.env` + `DEBUG`; таблицы: **profiles** (JSON/блоки конструктора), traps/agents, pairing, events, audit
- [ ] OpenAPI: profiles schema + остальной контракт CLI/UI

### Фаза 1 - Control API (+ бэкенд конструктора)
- [ ] Auth оператора
- [ ] **Схема профиля** (уровень, services[], banners, credentials, logging, mask) + валидация
- [ ] CRUD профилей; версия/hash конфига для агента
- [ ] Pairing (start → confirm → complete → token) + **bind profile**
- [ ] `get config` отдаёт собранный профиль; claim commands (reload/rotate)
- [ ] Heartbeat; batch events; фильтры; SSE
- [ ] Неприметные пути; TLS за Nginx

### Фаза 2 - Агент + honeypots (применение профиля)
- [ ] Агент: pair, heartbeat, pull профиля, буфер, досылка, скрытность
- [ ] Low/Mid читают профиль (порты, баннеры, креды) → события
- [ ] Смена профиля без переустановки агента (reload config)
- [ ] Install-артефакт → `/downloads/`
- [ ] E2E: профиль → агент → событие

### Фаза 3 - CLI (конструктор + ops)
- [ ] login; **`profile create/edit/list/show`**
- [ ] pair, bind, traps, events, `tail`
- [ ] Стоп-критерий: собрать профиль и увидеть атаку без Web UI

### Фаза 4 - Web panel (UI конструктора)
- [ ] **Мастер/форма конструктора** на том же Profiles API
- [ ] Dashboard, pairing, bind профиля, SSE-лента
- [ ] Пароль из `.env`

### Фаза 5 - Маскировка и демо
- [ ] MASK-1..4
- [ ] Сценарий: **собрали профиль в конструкторе** → атака → событие; гайд на 5 шагов
- [ ] Схема архитектуры/БД; презентация (акцент на конструктор)

### Фаза 6 - Bonus
- [ ] Пресеты профилей; honeytokens в конструкторе
- [ ] SSH/Docker оркестратор
- [ ] High, алерты, IoC, jitter, mTLS

---

## Минимальный контракт API (якорь CLI = UI)

| Область | Операции |
|---------|----------|
| Auth | login / logout / me |
| Profiles (конструктор) | CRUD; get schema/blocks; validate; list; (bonus) presets |
| Pairing / Traps | start, confirm, complete; list; status; **bind profile** |
| Agent | heartbeat; **get config** (профиль); claim/pull commands; post events (batch); опц. WS control |
| Events | list + filters; **SSE subscribe** |
| Artifacts | (must-ish) download agent install; (bonus) remote deploy |

Публичные пути коллектора - замаскированы (не содержать `honeypot` / явный `c2`).

---

## Критерии готовности MVP

1. `docker-compose up` поднимает центр  
2. В конструкторе (CLI или Web) собран и сохранён профиль  
3. Агент проходит pairing и получает профиль (`get config`)  
4. ≥2 ловушки (Low + Medium) по профилю шлют телеметрию  
5. Событие атаки видно в CLI/UI near-realtime (SSE)  
6. Канал не выглядит как явный honeypot-C2  
7. Потеря связи не теряет события (буфер агента)

---
