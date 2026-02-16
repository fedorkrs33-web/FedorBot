import os
from dotenv import load_dotenv

# --- Настройки проекта ---
PROJECT_DIR = os.getcwd()
DOTENV_PATH = os.path.join(PROJECT_DIR, ".env")
DOTENV_EXAMPLE_PATH = os.path.join(PROJECT_DIR, ".env.example")

# Шаблон для .env.example
ENV_TEMPLATE = '''
# 🤖 Telegram Bot
TELEGRAM_BOT_TOKEN=ваш_токен_бота

# 👤 Администраторы (через запятую)
ADMIN_IDS=123456789,987654321

# 🗄 База данных (по умолчанию SQLite)
DATABASE_URL=sqlite+aiosqlite:///./bot.db

# 🔐 PolzaAI API
POLZAAI_API_KEY=ваш_polzaai_api_key

# 🔐 GigaChat (Сбер)
GIGACHAT_CLIENT_ID=ваш_client_id
GIGACHAT_CLIENT_SECRET=ваш_client_secret

# 🔐 Yandex GPT
YANDEX_IAM_TOKEN=ваш_iam_token
YANDEX_FOLDER_ID=ваш_folder_id

# 🌐 Другие модели (если используются)
# OPENROUTER_API_KEY=ваш_openrouter_key
# ANTHROPIC_API_KEY=ваш_claude_key
'''.strip()

# --- 1. Создаём .env.example, если его нет ---
if not os.path.exists(DOTENV_EXAMPLE_PATH):
    try:
        with open(DOTENV_EXAMPLE_PATH, "w", encoding="utf-8") as f:
            f.write(ENV_TEMPLATE)
        print(f"✅ Создан файл: {DOTENV_EXAMPLE_PATH}")
    except Exception as e:
        print(f"❌ Не удалось создать .env.example: {e}")

# --- 2. Если .env отсутствует — создаём из примера ---
if not os.path.exists(DOTENV_PATH):
    try:
        if os.path.exists(DOTENV_EXAMPLE_PATH):
            with open(DOTENV_EXAMPLE_PATH, "r", encoding="utf-8") as src:
                content = src.read()
            with open(DOTENV_PATH, "w", encoding="utf-8") as dst:
                # Убираем значения по умолчанию
                cleaned = "\n".join(
                    line if not "=" in line else 
                    line.split("=")[0] + "=" for line in content.splitlines()
                )
                dst.write(cleaned)
            print(f"✅ Создан пустой .env на основе .env.example")
            print(f"   ⚠️ Заполните ключи в файле: {DOTENV_PATH}")
        else:
            # Если даже example нет — создаём базовый
            with open(DOTENV_PATH, "w", encoding="utf-8") as f:
                f.write("TELEGRAM_BOT_TOKEN=\nADMIN_IDS=\n")
            print(f"⚠️ Создан минимальный .env. Добавьте остальные переменные вручную.")
    except Exception as e:
        print(f"❌ Не удалось создать .env: {e}")
        raise

# --- 3. Загружаем переменные окружения ---
load_dotenv(dotenv_path=DOTENV_PATH, verbose=True)
print(f"🔹 Загружен .env из: {DOTENV_PATH}")

# --- 4. Читаем переменные ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS")
if admin_ids_str:
    try:
        ADMIN_IDS = list(map(int, [x.strip() for x in admin_ids_str.split(",") if x.strip()]))
    except ValueError as e:
        print(f"❌ Ошибка парсинга ADMIN_IDS: {e}")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# --- 5. Список критических ключей ---
REQUIRED_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "POLZAAI_API_KEY",
    "GIGACHAT_CLIENT_ID",
    "GIGACHAT_CLIENT_SECRET",
    "YANDEX_IAM_TOKEN",
    "YANDEX_FOLDER_ID"
]

# --- 6. Проверка наличия ключей ---
missing = []
for key in REQUIRED_KEYS:
    value = os.getenv(key)
    if not value or value.strip() == "=" or value.strip() == "":
        missing.append(key)

if missing:
    print(f"❌ Не хватает обязательных переменных в .env: {missing}")
    print(f"   Образец: {DOTENV_EXAMPLE_PATH}")
    print(f"   Редактируйте: {DOTENV_PATH}")
    raise ValueError(f"Отсутствуют переменные окружения: {missing}")

# --- 7. Успешный старт ---
print(f"✅ Все переменные окружения загружены.")
print(f"🤖 Бот запускается. Администраторы: {ADMIN_IDS}")
print(f"🔗 DATABASE_URL: {DATABASE_URL.split('://')[0]}://... (скрыто)")
