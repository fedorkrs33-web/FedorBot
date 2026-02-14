import os
from dotenv import load_dotenv

# --- Отладка: где мы находимся и есть ли .env ---
print("Текущая директория:", os.getcwd())
print("Файлы в директории:", os.listdir(os.getcwd()))

# Загружаем .env
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), verbose=True)

# --- Отладка: какие переменные загрузились ---
print("TELEGRAM_BOT_TOKEN из env:", os.getenv("TELEGRAM_BOT_TOKEN"))
print("ADMIN_IDS из env:", os.getenv("ADMIN_IDS"))
print("DATABASE_URL из env:", os.getenv("DATABASE_URL"))
# --------------------------------------------------

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS")
if admin_ids_str:
    try:
        ADMIN_IDS = list(map(int, [x.strip() for x in admin_ids_str.split(",")]))
    except Exception as e:
        print(f"Ошибка парсинга ADMIN_IDS: {e}")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

print(f"✅ Бот запускается. Администраторы: {ADMIN_IDS}")

print(f"Бот запускается с токеном: {BOT_TOKEN[:5]}...")  # Для отладки (удалите в продакшене)
print("Переменные окружения:")
print("BOT_TOKEN:", "загружен" if BOT_TOKEN else "None")
print("ADMIN_IDS:", ADMIN_IDS)
print("DATABASE_URL:", DATABASE_URL)