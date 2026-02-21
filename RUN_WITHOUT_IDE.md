# Запуск FedorBot без IDE и без Docker

Все команды выполняйте в **PowerShell** или **cmd** (от имени пользователя). Папка проекта: `c:\Work\FedorBot`.

---

## 1. Проверить Python

Должен быть установлен Python 3.10 или новее.

```powershell
python --version
```

Если команда не найдена — установите Python с [python.org](https://www.python.org/downloads/) и при установке отметьте **"Add Python to PATH"**.

---

## 2. Открыть папку проекта

```powershell
cd c:\Work\FedorBot
```

Дальше все команды — из этой папки.

---

## 3. Создать виртуальное окружение (один раз)

```powershell
python -m venv .venv
```

---

## 4. Включить виртуальное окружение

В **PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

В **cmd**:

```cmd
.venv\Scripts\activate.bat
```

После этого в начале строки появится `(.venv)` — окружение активно.

---

## 5. Установить зависимости (один раз)

```powershell
pip install -r requirements.txt
```

Если чего-то не хватает (например, aiosqlite или Flask):

```powershell
pip install aiosqlite Flask Flask-RESTX
```

---

## 6. Настроить .env

В папке `c:\Work\FedorBot` должен быть файл **`.env`**. Минимум для бота:

- `TELEGRAM_BOT_TOKEN=...` — токен от @BotFather
- `ADMIN_IDS=...` — ваш Telegram user_id (число)

Создать из примера и отредактировать в Блокноте:

```powershell
copy .env.example .env
notepad .env
```

Сохраните и закройте Блокнот.

---

## 7. Запустить бота

```powershell
python -m src.bot
```

В консоли должно появиться «Бот запущен...». Остановка: **Ctrl+C**.

---

## 8. (По желанию) Запустить веб-админку

В **другом** окне PowerShell (бот может продолжать работать в первом):

```powershell
cd c:\Work\FedorBot
.\.venv\Scripts\Activate.ps1
python web_app.py
```

Откройте в браузере: <http://localhost:5000>

Остановка: **Ctrl+C**.

---

## Краткая шпаргалка (когда всё уже настроено)

Один раз в новом терминале:

```powershell
cd c:\Work\FedorBot
.\.venv\Scripts\Activate.ps1
python -m src.bot
```

Всё. IDE и Docker не нужны.
