import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

# Список администраторов (через запятую в .env)
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS.split(",") if id.strip()]

# Конфигурация ИИ-моделей (будет использоваться на этапе 3)
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")