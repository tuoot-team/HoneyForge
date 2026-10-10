# Web UI (`source/web-panel`)

**Ответственный:** @propastin  
**Стек:** HTML/CSS/JS (+ лёгкий фреймворк по желанию), Chart.js, SSE  
**Стиль:** [`CodeStyle.md`](../../CodeStyle.md) - UI-тексты в отдельном файле, пароль/URL API из `.env`, без длинного тире

Панель - **только клиент** Control API (`source/core-api`). Своей БД и прямой связи с агентами нет.

Контракт API смотреть в http://127.0.0.1:8000/docs (когда поднят core-api) и в корневом README.

---

## Сейчас (пока core-api фаза 1 готова)

Цель на ближайший этап: **ops-dashboard + конструктор**, который ходит в уже живые эндпоинты.

### 1. Каркас приложения
- [ ] Страницы: Login, Dashboard (ловушки), Конструктор профиля, Pairing, Лента событий
- [ ] HTTP-клиент к `PUBLIC_API_BASE` из `.env` (например `http://127.0.0.1:8000`)
- [ ] Хранение Bearer-токена после логина; подстановка в `Authorization`
- [ ] Фиксированные строки UI - отдельный файл (не размазывать по компонентам)

### 2. Auth
- [ ] Форма пароля → `POST /api/v1/auth/login`
- [ ] `GET /api/v1/auth/me` для проверки сессии
- [ ] Logout (забыть токен на клиенте)

### 3. Конструктор профилей (главный экран продукта)
- [ ] Мастер/форма: уровень Low/Medium → services/ports → banners → credentials → logging → **mask**
- [ ] Поля mask минимум: `beacon_interval_sec`, `jitter_pct`, `collector_path_set`, `cover_urls`, `process_name`, `decoy_content_seed`, `service_personality`
- [ ] Подтянуть подсказки из `GET /api/v1/profiles/schema`
- [ ] Create / list / edit / delete: `/api/v1/profiles/`
- [ ] Validate перед save: `POST /api/v1/profiles/validate`

### 4. Pairing + ловушки
- [ ] Экран: оператор вводит `device_code` агента → `POST /api/v1/pairing/confirm` (нужен login)
- [ ] Список ловушек + статусы: `GET /api/v1/traps/`
- [ ] Bind профиля: `POST /api/v1/traps/{id}/bind-profile`

### 5. Лента событий
- [ ] Таблица с фильтрами: `GET /api/v1/events/`
- [ ] Live: SSE `GET /api/v1/events/stream` (тот же Bearer)
- [ ] Простые графики (Chart.js): топ источников / типы событий - можно заглушкой по данным list

### Пока не делать
- Multi-site marketing SaaS, Telegram, роли/инвайты
- Свою бизнес-логику канала агента
- Красивости в ущерб рабочему конструктору и ленте

---

## По итогу (MVP / защита)

Должно быть видно на демо:

1. Логин в панель  
2. **Собрали профиль в конструкторе** (порты + mask) и сохранили  
3. Подтвердили pairing ловушки и привязали профиль  
4. Список ловушек со статусами online/offline  
5. После атаки на honeypot - **событие в ленте near-realtime**  
6. Презентация: что за конструктор, как маскируется канал, честный Low/Mid (без overclaim High)

Опционально к демо: лёгкая статическая «витрина» для Nginx front (маскировка центра) - не отдельный продукт.

**Стоп-критерий Web UI:** оператор может пройти демо-петлю без CLI (login → профиль → pair/bind → лента).
