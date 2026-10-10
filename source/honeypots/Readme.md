# Ханипоты (`source/honeypots`)

**Ответственный:** @SoulProtocol  
**Стек:** Python; тонкий агент; эмуляторы Low/Mid; Docker/изоляция по возможности  
**Стиль:** [`CodeStyle.md`](../../CodeStyle.md) - комментарии на русском, табы, debug через `.env`

Хост ловушки = **агент + сервисы-приманки**. Центр уже умеет pairing / config / events (core-api фаза 1). Ваша зона - то, что крутится на стороне приманки.

Контракт агента (ядро):
- Pairing: `POST /api/v1/pairing/start` → confirm у оператора → `POST .../complete` → сохранить `agent_token`
- Заголовок: `X-Agent-Token: ...`
- Heartbeat: `POST /api/v1/agent/heartbeat` (или mimicry `/v1/metrics`)
- Конфиг: `GET /api/v1/agent/config`
- События: `POST /api/v1/agent/events` (batch)
- Команды: `POST /api/v1/agent/commands/claim` (`reload_config`)

---

## Сейчас (фаза 2 - ближайшие задачи)

### 1. Тонкий агент (общий для Low/Mid)
- [ ] CLI/процесс: `pair` (device_code на экран) → poll complete → сохранить token локально
- [ ] Цикл: heartbeat + `get config` по интервалу из `profile.blocks.mask`
- [ ] **Локальный буфер** событий (файл/sqlite) + досылка batch при восстановлении сети
- [ ] Jitter: `beacon_interval_sec` + `jitter_pct` (не ровно каждые N секунд)
- [ ] Burst: копить события и слать пачкой
- [ ] Cover traffic (по возможности): GET из `mask.cover_urls`
- [ ] Скрытность: имя процесса/пути из `mask.process_name` (без строк `honeypot` в коде/логах прод-режима)
- [ ] Обработка `reload_config` из claim
- [ ] Переменные: URL центра, token, `DEBUG` - из `.env`

### 2. Low (`low/`)
- [ ] Слушать порты из `blocks.services`
- [ ] Отдавать banner из `blocks.banners` (или дефолт)
- [ ] На connect/scan → событие (`event_type` вроде `port_connect` / `banner_grab`) с `source_ip`, портом, timestamp
- [ ] Без реальной логики сервиса

### 3. Medium (`mid/`) - минимум один сервис для демо
- [ ] fake-SSH **или** fake-HTTP (лучше оба, must - хотя бы один)
- [ ] Креды/баннеры из профиля; попытки логина → событие `auth_attempt` (username/password в payload)
- [ ] Для HTTP: запросы/пути → событие; ограниченный «граф» ответов
- [ ] Timing: задержки из `blocks.logging.auth_delay_ms_*` (не мгновенный ответ)
- [ ] `decoy_content_seed` - лёгкая асимметрия (hostname/uptime hint), не клоны 1-в-1

### 4. Стыковка
- [ ] Профиль сменился на центре → агент подтянул config → сервисы перечитались без переустановки
- [ ] README: как запустить агент + Low/Mid против локального core-api
- [ ] (Желательно) простой install-скрипт под `/downloads/` позже

### Пока не делать (bonus / фаза 6)
- High sandbox / настоящая ОС
- honeytokens в скучных путях (можно заложить интерфейс)
- mTLS, полноценные personality packs
- Вечный WebSocket на центр

---

## По итогу (MVP / защита)

На демо должно работать:

1. Агент проходит **pairing**, появляется в центре  
2. Получает профиль из конструктора (`get config`)  
3. Подняты **Low и Medium** (два уровня) по профилю  
4. Атака (скан / ssh-login / http) → события уходят в центр (видно в CLI/UI)  
5. Обрыв сети: события **не теряются** (буфер → досылка)  
6. Канал не орёт «honeypot»: mimicry-пути, jitter, скрытное имя процесса  
7. Честно: Low = баннеры; Mid = ограниченная эмуляция (не High)

**Стоп-критерий honeypots:** `профиль → агент → атака → событие в центре` без ручной записи в БД.

Структура (ориентир):

```
honeypots/
├── Readme.md          # этот файл
├── agent/             # pairing, beacon, buffer, claim
├── low/               # port/banner listeners
├── mid/               # fake-ssh / fake-http
└── high/              # bonus позже
```
