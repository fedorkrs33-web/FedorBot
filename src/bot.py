from aiogram import Bot, Dispatcher
from src.config import BOT_TOKEN
from src.handlers import user_handlers, admin_handlers, proverb_handlers
from src.database import init_db
import asyncio
import logging
import sys

# Логи в консоль и в файл (удобно скопировать в чат при ошибках)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(proverb_handlers.router)

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
