from aiogram import Bot, Dispatcher
from src.middlewares.block_check import BlockCheckMiddleware
from src.config import BOT_TOKEN
from src.handlers import user_handlers, admin_handlers, proverb_handlers
from src.database import init_db
from version import __version__
import asyncio
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

async def main():
    logging.info("Запуск FedorBot v%s", __version__)
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем middleware
    dp.message.middleware(BlockCheckMiddleware())
    dp.callback_query.middleware(BlockCheckMiddleware())

    # Подключаем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(proverb_handlers.router)

    print(f"Бот запущен... (v{__version__})")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    