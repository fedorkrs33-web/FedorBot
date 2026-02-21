# Деплой на Vercel

На Vercel можно развернуть **только веб-админку** (Flask). Сам Telegram-бот на Vercel запустить нельзя: он работает long-polling и требует постоянно работающего процесса.

## Ограничения

| Компонент | Vercel | Рекомендация |
|-----------|--------|--------------|
| **Веб-админка** (Flask) | ✅ Да | Нужна облачная БД (см. ниже) |
| **Telegram-бот** (polling) | ❌ Нет | Деплой на Railway, Render, VPS |

На Vercel нет постоянного диска: файл `fedorbot.db` не сохранится между запросами. Поэтому для веб-админки на Vercel нужна **облачная база данных** (PostgreSQL).

---

## Шаг 1: Облачная БД

Создайте базу PostgreSQL, например:

- [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) (в том же аккаунте)
- [Supabase](https://supabase.com) (бесплатный tier)
- [Neon](https://neon.tech)

Скопируйте **connection string** (URL подключения), например:
`postgresql://user:pass@host:5432/dbname?sslmode=require`

Схему таблиц (`users`, `proverbs`, `prompts`, `models`, `ai_responses`) нужно создать в этой БД вручную или миграциями (те же таблицы, что в SQLite).

---

## Шаг 2: Переменные окружения в Vercel

В проекте Vercel: **Settings → Environment Variables** добавьте:

| Переменная | Значение |
|------------|----------|
| `ADMIN_PASSWORD` | Пароль входа в админку |
| `SECRET_KEY` | Случайная строка для сессий |
| `DATABASE_URL` | URL PostgreSQL (из шага 1) |

Без `DATABASE_URL` приложение будет ожидать локальный файл `fedorbot.db` и на Vercel не заработает.

---

## Шаг 3: Деплой

### Через Vercel CLI

1. Установите [Vercel CLI](https://vercel.com/docs/cli):
   ```powershell
   npm i -g vercel
   ```

2. В корне проекта:
   ```powershell
   cd c:\Work\FedorBot
   vercel
   ```
   Следуйте подсказкам (логин, проект, настройки).

3. Продакшен-деплой:
   ```powershell
   vercel --prod
   ```

### Через GitHub

1. Залейте проект на GitHub.
2. На [vercel.com](https://vercel.com) нажмите **Add New → Project** и импортируйте репозиторий.
3. В настройках проекта добавьте переменные окружения (шаг 2).
4. Деплой запустится автоматически при каждом `git push`.

---

## Точка входа

Vercel ищет Flask-приложение в одном из файлов: `app.py`, `server.py`, `index.py` (в корне или в `src/`). В проекте для этого используется **`app.py`** в корне:

```python
from web_app import app
```

Маршруты веб-админки (`/`, `/admin`, `/login`, API и т.д.) обрабатываются этим приложением.

---

## Где запускать бота

Telegram-бота запускайте на платформе с постоянным процессом:

- **Railway** — удобно, есть бесплатный tier
- **Render** — бесплатный tier с ограничениями
- **VPS** (Timeweb, Selectel, и т.п.) — `python -m src.bot` в screen/tmux или как systemd-сервис

Там же можно использовать ту же PostgreSQL (одна БД и для бота, и для веб-админки), если переведёте бота с SQLite на Postgres через `DATABASE_URL` в `src/config.py` и драйвер (например, `asyncpg`).
