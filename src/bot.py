from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from src.config import BOT_TOKEN
from src.database import init_db, AsyncSessionLocal
from src.models import Message
from src.schemas import MessageCreate
from datetime import datetime
import asyncio
from sqlalchemy.exc import SQLAlchemyError

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обработка команды /start
@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я новый Telegram-бот на Python и aiogram")

# Обработка текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    # Получаем информацию о пользователе
    user = message.from_user
    
    # Валидируем данные перед сохранением
    try:
        message_data = MessageCreate(
            message_id=message.message_id,
            chat_id=str(message.chat.id),
            username=user.username,
            first_name=user.first_name,
            content=message.text
        )
        
        # Сохраняем сообщение в базу данных
        async with AsyncSessionLocal() as session:
            try:
                # Преобразуем Pydantic-модель в словарь
                db_message = Message(**message_data.model_dump())
                session.add(db_message)
                await session.commit()
                
                print(f"Сообщение от {user.first_name} сохранено в базу данных")
            except SQLAlchemyError as e:
                print(f"Ошибка SQLAlchemy при сохранении: {e}")
                await session.rollback()
            except Exception as e:
                print(f"Неожиданная ошибка при сохранении: {e}")
                await session.rollback()
    except Exception as e:
        print(f"Ошибка при валидации данных: {e}")

    # Отвечаем на сообщение
    await message.answer(f"Получено ваше сообщение: {message.text}")

# Функция для отправки сообщения
async def send_message(chat_id: str, text: str) -> bool:
    try:
        await bot.send_message(chat_id, text)
        
        # Сохраняем исходящее сообщение
        async with AsyncSessionLocal() as session:
            try:
                db_message = Message(
                    message_id=0,
                    chat_id=chat_id,
                    content=text,
                    from_bot=True
                )
                session.add(db_message)
                await session.commit()
            except SQLAlchemyError as e:
                print(f"Ошибка SQLAlchemy при сохранении исходящего сообщения: {e}")
                await session.rollback()
            except Exception as e:
                print(f"Неожиданная ошибка при сохранении исходящего сообщения: {e}")
                await session.rollback()
        
        return True
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        return False

# Основная функция запуска бота
async def main():
    # Инициализируем базу данных
    await init_db()
    
    # Запускаем бота
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())