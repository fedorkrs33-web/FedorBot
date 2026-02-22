import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

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
DATABASE_URL=sqlite+aiosqlite:///./fedorbot.db

# 🔐 PolzaAI API
POLZAAI_API_KEY=ваш_polzaai_api_key

# 🔐 GigaChat (Сбер)
GIGACHAT_CLIENT_ID=ваш_client_id
GIGACHAT_CLIENT_SECRET=ваш_client_secret

# 🔐 Yandex GPT
YANDEX_OAUTH_TOKEN=ваш_iam_token
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
print(f"Loaded .env from: {DOTENV_PATH}")

# --- 4. Читаем переменные ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS")
if admin_ids_str:
    try:
        ADMIN_IDS = list(map(int, [x.strip() for x in admin_ids_str.split(",") if x.strip()]))
    except ValueError as e:
        print(f"❌ Ошибка парсинга ADMIN_IDS: {e}")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fedorbot.db")

# --- 5. Список критических ключей ---
REQUIRED_KEYS = [
    "TELEGRAM_BOT_TOKEN",
    "POLZAAI_API_KEY",
    "GIGACHAT_CLIENT_ID",
    "GIGACHAT_CLIENT_SECRET",
    "YANDEX_OAUTH_TOKEN",
    "YANDEX_FOLDER_ID"
]  # Проверка для .env прочитана, всё на месте

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

class Config:
    # Кэширование IAM-токена
    _cached_iam_token = None
    _token_expiry = None

    @classmethod
    def get_yandex_credentials(cls):
        """
        Возвращает IAM-токен и Folder ID.
        Использует кэширование токена (живёт 12 часов).
        """
        oauth_token = os.getenv("YANDEX_OAUTH_TOKEN")
        folder_id = os.getenv("YANDEX_FOLDER_ID")

        if not oauth_token or not folder_id:
            logger.error("❌ Не заданы YANDEX_OAUTH_TOKEN или YANDEX_FOLDER_ID")
            return None, None

        # Проверяем кэш
        if (
            cls._cached_iam_token
            and cls._token_expiry
            and datetime.now() < cls._token_expiry
        ):
            logger.debug("🔁 Используем кэшированный IAM-токен")
            return cls._cached_iam_token, folder_id

        # Обновляем токен
        new_token = cls._fetch_iam_token(oauth_token)
        if new_token:
            cls._cached_iam_token = new_token
            cls._token_expiry = datetime.now() + timedelta(hours=11)  # обновим раньше истечения
            logger.info("✅ Новый IAM-токен получен и закэширован")
            return new_token, folder_id

        return None, None

    @staticmethod
    def _fetch_iam_token(oauth_token: str) -> str | None:
        """Запрашивает новый IAM-токен через OAuth"""
        try:
            response = requests.post(
                "https://iam.api.cloud.yandex.net/iam/v1/tokens",
                json={"yandexPassportOauthToken": oauth_token},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                expires_at = datetime.fromisoformat(data["expiresAt"].replace("Z", "+00:00"))
                logger.debug(f"IAM-токен получен, срок действия до: {expires_at}")
                return data["iamToken"]
            else:
                logger.error(f"❌ Ошибка при получении IAM-токена: {response.status_code} — {response.text}")
        except Exception as e:
            logger.exception(f"❌ Исключение при получении IAM-токена: {e}")
        return None

# --- 7. Успешный старт ---
print(f"All environment variables loaded.")
print(f"Bot starting. Admins: {ADMIN_IDS}")
print(f"DATABASE_URL: {DATABASE_URL.split('://')[0]}://... (hidden)")
