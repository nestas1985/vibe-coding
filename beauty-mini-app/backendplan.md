# backendplan.md — Beauty Platform Backend

> Архитектурный план для разработки. Только то, что реально нужно для 50 мастеров.  
> Обновляется по мере разработки.

---

## 1. Что строим

**SaaS-платформа** для мастеров красоты на базе Telegram Mini App.

```
Один бот платформы (@nogti_cool_bot или другой)
    │
    ├── Мастер А (Анна, slug: anna) ──→ Mini App: platform.com/app/anna
    ├── Мастер Б (Лена, slug: lena) ──→ Mini App: platform.com/app/lena
    └── Мастер В ...
```

- Клиент открывает Mini App конкретного мастера через глубокую ссылку
- Бот знает к какому мастеру относится клиент по стартовому параметру
- Все данные на сервере — localStorage только как кэш

---

## 2. Технический стек

### Сервер (Beget VPS, ~800 руб/мес)
```
OS: Ubuntu 22.04
RAM: 2–4 GB (хватит до 50 мастеров с запасом)
```

| Слой | Технология | Зачем |
|------|-----------|-------|
| API | Python + FastAPI | Быстро, async, автодокументация |
| Бот | aiogram 3.x | Лучший Python-фреймворк для Telegram |
| БД | PostgreSQL 15 | Реляционные данные, надёжно |
| Кэш / очереди | Redis | Сессии, задачи на уведомления |
| Файлы | Beget Object Storage (S3-совместимый) | Фото мастеров и портфолио |
| Планировщик | APScheduler (в Python) | Напоминания за 24ч и 2ч |
| Веб-сервер | Nginx | Реверс-прокси + SSL |
| HTTPS | Let's Encrypt | Обязательно для Mini App |

### Домен
```
platform.com (или nogtimaster.ru — под брендом)
├── platform.com/app/{slug}     ← Mini App клиента
├── platform.com/panel          ← Панель управления мастера
├── platform.com/api/           ← REST API
└── platform.com/bot/webhook    ← Telegram webhook
```

---

## 3. База данных

### Таблица: `masters` — мастера платформы
```sql
id              SERIAL PRIMARY KEY
telegram_id     BIGINT UNIQUE NOT NULL     -- tg user id мастера
username        VARCHAR(64)                -- @username в telegram
slug            VARCHAR(64) UNIQUE NOT NULL -- anna, lena (для URL)
name            VARCHAR(128) NOT NULL       -- имя для клиентов
specialty       VARCHAR(128)               -- "Мастер ногтевого сервиса"
phone           VARCHAR(32)
avatar_url      TEXT                       -- S3 ссылка
bio             TEXT
address         TEXT
rating          DECIMAL(2,1) DEFAULT 0
reviews_count   INT DEFAULT 0
plan            VARCHAR(16) DEFAULT 'free' -- 'free' | 'pro'
plan_expires_at TIMESTAMPTZ
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMPTZ DEFAULT NOW()
```

### Таблица: `master_settings` — настройки мастера
```sql
master_id       INT REFERENCES masters(id) PRIMARY KEY
work_days       INT[] DEFAULT '{1,2,3,4,5}' -- 1=Пн..7=Вс
work_start      TIME DEFAULT '09:00'
work_end        TIME DEFAULT '20:00'
slot_duration   INT DEFAULT 30              -- минут
lunch_start     TIME                        -- перерыв
lunch_end       TIME
deposit_percent INT DEFAULT 0              -- % предоплаты (0 = выключена)
yokassa_shop_id VARCHAR(64)                 -- ЮKassa, только pro-план
yokassa_key     TEXT                        -- зашифрован в БД
gcal_token      TEXT                        -- Google OAuth refresh_token
gcal_calendar_id VARCHAR(256)              -- id календаря для синхронизации
theme_id        VARCHAR(32) DEFAULT 'dark-gold' -- см. раздел 8
accent_color    VARCHAR(7)                 -- HEX цвет, например #D4AF37
logo_url        TEXT                       -- S3 ссылка на логотип
updated_at      TIMESTAMPTZ DEFAULT NOW()
```

### Таблица: `services` — услуги мастера
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
category        VARCHAR(64)                -- "Маникюр", "Педикюр"
name            VARCHAR(128) NOT NULL
price           INT NOT NULL               -- в рублях
duration        INT NOT NULL               -- в минутах
emoji           VARCHAR(8)
sort_order      INT DEFAULT 0
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMPTZ DEFAULT NOW()
```
> ⚠️ Бизнес-правило: на free-плане не более 5 активных услуг (is_active = TRUE).

### Таблица: `portfolio_photos` — портфолио
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
photo_url       TEXT NOT NULL              -- S3
label           VARCHAR(64)               -- "Гель-лак"
sort_order      INT DEFAULT 0
created_at      TIMESTAMPTZ DEFAULT NOW()
```

### Таблица: `clients` — клиенты мастера
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
telegram_id     BIGINT                     -- если пришёл через Telegram
name            VARCHAR(128) NOT NULL
phone           VARCHAR(32)
notes           TEXT                       -- заметки мастера (аллергии и т.д.)
is_blocked      BOOLEAN DEFAULT FALSE
visits_count    INT DEFAULT 0
last_visit_at   TIMESTAMPTZ
created_at      TIMESTAMPTZ DEFAULT NOW()

UNIQUE (master_id, telegram_id)            -- один клиент ≠ одна запись на всей платформе
```

### Таблица: `bookings` — записи
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
client_id       INT REFERENCES clients(id)
service_id      INT REFERENCES services(id)
date            DATE NOT NULL
time            TIME NOT NULL
status          VARCHAR(16) DEFAULT 'active'
                -- 'active' | 'done' | 'cancelled' | 'no_show'
deposit_amount  INT DEFAULT 0
deposit_paid    BOOLEAN DEFAULT FALSE
payment_id      VARCHAR(128)               -- id платежа в ЮKassa
gcal_event_id   VARCHAR(256)               -- id события в Google Calendar
remind_24_sent  BOOLEAN DEFAULT FALSE
remind_2_sent   BOOLEAN DEFAULT FALSE
cancel_reason   TEXT
created_at      TIMESTAMPTZ DEFAULT NOW()

UNIQUE (master_id, date, time)             -- нельзя два клиента в одно время
```

### Таблица: `blocked_slots` — ручные блокировки времени
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
date            DATE NOT NULL
time_start      TIME NOT NULL
time_end        TIME NOT NULL
reason          VARCHAR(128)               -- "Обед", "Личное"
gcal_event_id   VARCHAR(256)
```

### Таблица: `subscriptions` — история подписок
```sql
id              SERIAL PRIMARY KEY
master_id       INT REFERENCES masters(id)
plan            VARCHAR(16) NOT NULL       -- 'pro'
amount          INT NOT NULL               -- в копейках
period_start    TIMESTAMPTZ
period_end      TIMESTAMPTZ
payment_id      VARCHAR(128)               -- id в ЮKassa
status          VARCHAR(16)               -- 'paid' | 'pending' | 'failed'
created_at      TIMESTAMPTZ DEFAULT NOW()
```

---

## 4. API-эндпоинты

### 4.1 Публичные (Mini App клиента, без авторизации)

```
GET  /api/app/{slug}                    Профиль мастера: имя, фото, тема, услуги, портфолио
GET  /api/app/{slug}/slots?date=YYYY-MM-DD   Свободные слоты на дату
POST /api/app/{slug}/bookings           Создать запись
     Body: { service_id, date, time, client_name, client_phone, telegram_id }

GET  /api/app/client/{telegram_id}/bookings?master_slug=  Мои записи (для конкретного мастера)
DELETE /api/app/bookings/{id}           Отменить запись (только своя, только будущая)
POST /api/app/payments/deposit          Создать платёж предоплаты (→ ЮKassa)
```

### 4.2 Панель мастера (авторизация через Telegram WebApp initData)

```
GET    /api/panel/me                    Свой профиль
PATCH  /api/panel/profile               Обновить имя, специальность, адрес, телефон
POST   /api/panel/avatar                Загрузить фото (multipart)

GET    /api/panel/services              Список услуг
POST   /api/panel/services              Добавить услугу
PATCH  /api/panel/services/{id}         Обновить
DELETE /api/panel/services/{id}         Удалить

GET    /api/panel/portfolio             Фото портфолио
POST   /api/panel/portfolio             Загрузить фото (multipart)
DELETE /api/panel/portfolio/{id}
PATCH  /api/panel/portfolio/reorder     Поменять порядок

GET    /api/panel/settings              Часы, выходные, тема, ЮKassa
PATCH  /api/panel/settings              Обновить

GET    /api/panel/bookings?date=        Записи на дату
GET    /api/panel/bookings/upcoming     Ближайшие 10 записей
PATCH  /api/panel/bookings/{id}/status  Отметить done / no_show

GET    /api/panel/clients               Список клиентов
GET    /api/panel/clients/{id}          Карточка клиента + история
PATCH  /api/panel/clients/{id}/notes    Сохранить заметки
PATCH  /api/panel/clients/{id}/block    Заблокировать

POST   /api/panel/blocked-slots         Заблокировать время вручную
DELETE /api/panel/blocked-slots/{id}

GET    /api/panel/analytics             Выручка/месяц, top-услуги, no-show%  ← pro only

GET    /api/panel/calendar/auth         Начать OAuth с Google
GET    /api/panel/calendar/callback     Коллбэк от Google
DELETE /api/panel/calendar/disconnect   Отключить Google Calendar
```

### 4.3 Платформенные (внутренние)

```
POST /bot/webhook                       Telegram webhook (aiogram)
POST /api/payments/webhook              ЮKassa колбэк

POST /api/platform/register             Регистрация мастера (из бота)
GET  /api/platform/masters              Список всех мастеров (только superadmin)
```

---

## 5. Авторизация

### Кто и как авторизуется

| Роль | Способ | Что видит |
|------|--------|-----------|
| Клиент | Telegram WebApp initData (telegram_id) | Профиль мастера, своих записей |
| Мастер | Telegram WebApp initData (telegram_id) | Свои данные, своих клиентов |
| Superadmin | JWT-токен в заголовке | Всё |

### Telegram initData (как работает)
```
Mini App при открытии передаёт window.Telegram.WebApp.initData
Сервер проверяет HMAC-подпись через BOT_TOKEN
Из неё берём user.id — это и есть идентификатор мастера или клиента
Подделать нельзя — подпись проверяется на сервере
```

### Разграничение данных (multi-tenancy)
```
Мастер А не видит данные мастера Б — всегда фильтруем WHERE master_id = ?
Клиент X у мастера А — отдельная строка clients
Тот же человек у мастера Б — другая строка clients (независимые записи)
```

---

## 6. Онбординг мастера

### Флоу через бота платформы

```
Шаг 1: Мастер пишет /start боту
         Бот отвечает: «Привет! Ты мастер или клиент?»

Шаг 2: Мастер нажимает «Я мастер»
         Бот: «Введи своё имя (как тебя видят клиенты)»

Шаг 3: Мастер вводит имя
         Бот: «Введи свою специализацию (например: мастер ногтевого сервиса)»

Шаг 4: Бот создаёт запись в masters, генерирует slug (anna-smirnova)
         Бот: «Готово! Твоя ссылка: t.me/botname?start=anna-smirnova
               Поделись ей с клиентами — они откроют твоё приложение»

Шаг 5: Бот предлагает «Открыть панель управления» → Mini App панели
         Там мастер добавляет: фото, услуги, часы работы, портфолио
```

### Как клиент находит конкретного мастера
```
Мастер делится ссылкой: t.me/nogti_cool_bot?start=anna-smirnova
Клиент нажимает Start → бот запоминает к какому мастеру клиент привязан
Бот открывает кнопку «Записаться» → Mini App platform.com/app/anna-smirnova
```

---

## 7. Google Calendar — двусторонняя синхронизация

### Подключение
```
1. Мастер в настройках нажимает «Подключить Google Calendar»
2. Редирект на Google OAuth (scope: calendar.events)
3. После согласия — сохраняем refresh_token в master_settings.gcal_token
4. Мастер выбирает какой календарь использовать (может быть несколько)
```

### Новая запись → Google Calendar
```
POST /app/{slug}/bookings
  → Создаём booking в БД
  → Создаём событие в Google Calendar (Google Calendar API)
  → Сохраняем gcal_event_id в booking
  → Событие называется: "💅 Мария Петрова — Гель-лак"
```

### Google Calendar → блокировка слотов
```
Каждые 15 минут (APScheduler):
  → Читаем события из Google Calendar мастера на ближайшие 7 дней
  → Событие БЕЗ нашего тега = личное дело мастера = слот занят
  → Событие С нашим тегом = наша запись = не трогаем
  → Сравниваем с blocked_slots, добавляем/удаляем
```

### Отмена записи → удаление из Calendar
```
DELETE /app/bookings/{id}
  → booking.status = 'cancelled'
  → Если gcal_event_id есть → удаляем событие из Google Calendar
```

---

## 8. Тарифы (бизнес-логика)

### Free
| Параметр | Лимит |
|----------|-------|
| Услуги (активных) | 5 |
| Портфолио фото | 6 |
| Записей в месяц | Без лимита |
| Напоминания клиентам | ❌ |
| Предоплата от клиентов | ❌ |
| Тема | 1 (дефолтная) |
| Своё лого | ❌ |
| Google Calendar | ❌ |
| Аналитика | ❌ |
| Рассылки | ❌ |

### Pro (490 ₽/мес)
| Параметр | Лимит |
|----------|-------|
| Услуги | Без лимита |
| Портфолио фото | 30 |
| Напоминания клиентам (24ч + 2ч) | ✅ |
| Предоплата через ЮKassa мастера | ✅ |
| Все темы + свой цвет + лого | ✅ |
| Google Calendar (двустороннее) | ✅ |
| Аналитика | ✅ |
| Рассылки по базе клиентов | ✅ |
| Чёрный список | ✅ |

### Оплата подписки
```
1. Мастер в боте нажимает «Оплатить Pro» → переходит по ссылке
2. Ссылка ведёт на страницу оплаты ЮKassa платформы (не мастера)
3. После оплаты: ЮKassa отправляет webhook на /api/payments/webhook
4. Webhook: обновляем masters.plan = 'pro', plan_expires_at = now + 30 дней
5. За 3 дня до окончания — бот напоминает о продлении
```

---

## 9. White-Label темы

### Хранение
```json
// master_settings.theme_id + accent_color + logo_url
{
  "theme_id": "dark-purple",
  "accent_color": "#9B59B6",
  "logo_url": "https://storage.../master/123/logo.png"
}
```

### Встроенные темы
| ID | Название | Фон | Акцент |
|----|----------|-----|--------|
| dark-gold | Золото (дефолт) | #0D0D0D | #D4AF37 |
| dark-purple | Фиолетовый | #0D0B14 | #9B59B6 |
| dark-pink | Розовый | #1A0D12 | #E91E8C |
| dark-black | Чёрный минимализм | #111111 | #FFFFFF |
| light-nude | Нюд (светлая) | #FAF5F0 | #C19A6B |

### Как применяется в Mini App
```javascript
// GET /api/app/{slug} возвращает:
{
  theme: {
    id: "dark-purple",
    accent: "#9B59B6",
    logo: "https://..."
  }
}
// Mini App применяет CSS переменные динамически:
document.documentElement.style.setProperty('--accent', theme.accent)
```

---

## 10. Уведомления

### Очередь (APScheduler каждые 5 минут)
```python
# Псевдокод
bookings = db.query("""
  SELECT b.*, c.telegram_id, m.name as master_name
  FROM bookings b
  JOIN clients c ON b.client_id = c.id
  JOIN masters m ON b.master_id = m.id
  WHERE b.status = 'active'
    AND b.date = CURRENT_DATE + 1     -- за 24 часа
    AND b.remind_24_sent = FALSE
    AND m.plan = 'pro'                -- только pro
""")
for b in bookings:
    bot.send_message(c.telegram_id, f"Напоминание: завтра в {b.time} к {master_name}")
    db.update(b.id, remind_24_sent=True)
```

### Что и когда
| Событие | Кому | Текст |
|---------|------|-------|
| Запись создана | Клиенту | «Записан к {мастер} на {дата} {время}. Адрес: {адрес}» |
| Запись создана | Мастеру | «Новая запись: {клиент} на {дата} {время} — {услуга}» |
| За 24 часа | Клиенту (pro) | «Напоминание: завтра в {время}. Отменить: /cancel_{id}» |
| За 2 часа | Клиенту (pro) | «Ждём вас через 2 часа» |
| Клиент отменил | Мастеру | «{Клиент} отменил запись на {дата}» |
| Просьба об оценке | Клиенту (pro) | «Как прошло? Оцените работу мастера» |

---

## 11. Деплой на Beget

### Структура файлов на сервере
```
/var/www/beauty-platform/
├── backend/
│   ├── main.py              ← FastAPI app
│   ├── bot.py               ← aiogram bot
│   ├── models.py            ← SQLAlchemy модели
│   ├── routes/              ← API роуты
│   ├── services/            ← Google Calendar, ЮKassa, уведомления
│   └── requirements.txt
├── frontend/
│   └── tg-app/              ← текущий Mini App (статика)
└── .env                     ← секреты (не в git)
```

### .env на сервере
```
BOT_TOKEN=...
DATABASE_URL=postgresql://user:pass@localhost:5432/beauty
REDIS_URL=redis://localhost:6379
YOKASSA_PLATFORM_SHOP_ID=...    # для подписок
YOKASSA_PLATFORM_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SECRET_KEY=...                  # для шифрования yokassa_key мастеров
STORAGE_BUCKET=...
STORAGE_KEY=...
```

### Nginx конфиг (упрощённо)
```nginx
server {
  server_name platform.com;

  location /api/     { proxy_pass http://127.0.0.1:8000; }
  location /bot/     { proxy_pass http://127.0.0.1:8000; }
  location /app/     { root /var/www/beauty-platform/frontend; try_files $uri /tg-app/index.html; }
  location /panel/   { root /var/www/beauty-platform/frontend; }
}
```

---

## 12. Что разрабатывать в первую очередь

### Этап 1 — База (нужна для любой работы)
- [ ] Настроить VPS: Ubuntu, Nginx, PostgreSQL, Redis
- [ ] Создать все таблицы БД (раздел 3)
- [ ] FastAPI: авторизация через Telegram initData
- [ ] API: публичный профиль мастера `/api/app/{slug}`
- [ ] API: свободные слоты `/api/app/{slug}/slots`
- [ ] API: создать запись `/api/app/{slug}/bookings`
- [ ] Подключить Mini App к API (убрать localStorage, читать с сервера)

### Этап 2 — Бот
- [ ] aiogram: /start с deep link → определение мастера
- [ ] Сохранение telegram_id клиента при первом касании
- [ ] Уведомление мастеру о новой записи
- [ ] Уведомление клиенту после записи

### Этап 3 — Панель мастера
- [ ] Онбординг мастера через бота (раздел 6)
- [ ] Mini App панели: редактирование профиля, услуги, расписание
- [ ] Загрузка фото в S3

### Этап 4 — Монетизация
- [ ] ЮKassa: оплата подписки
- [ ] Проверка лимитов плана (5 услуг на free)
- [ ] Лимиты portfolio, уведомлений

### Этап 5 — Pro-фичи
- [ ] Google Calendar OAuth + двусторонняя синхронизация
- [ ] Напоминания (APScheduler)
- [ ] Предоплата через ЮKassa мастера
- [ ] White-label темы + логотип
- [ ] Аналитика
- [ ] Рассылки

---

## 13. Открытые вопросы (решить перед стартом)

- [ ] Домен платформы — зарегистрировать на Beget
- [ ] ЮKassa аккаунт для приёма подписок — нужно ИП или самозанятость
- [ ] Google Cloud Project — создать, получить client_id/secret для Calendar API
- [ ] Beget Object Storage — включить в личном кабинете Beget
