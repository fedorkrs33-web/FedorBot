from aiogram import Bot, Dispatcher
from src.config import BOT_TOKEN
from src.handlers import user_handlers, admin_handlers, proverb_handlers
from src.database import init_db
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

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
