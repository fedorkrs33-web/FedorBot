from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select, delete, func
from src.config import BOT_TOKEN, ADMIN_IDS
from src.database import init_db, AsyncSessionLocal, get_db
from src.models import Message, User, Proverb
from src.schemas import MessageCreate, UserCreate, UserUpdate, ProverbResponse
from datetime import datetime
import asyncio
from sqlalchemy.exc import SQLAlchemyError

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Проверка блокировки пользователя
async def is_user_blocked(user_id: str) -> bool:
    async for session in get_db():
        try:
            user = await session.get(User, user_id)
            return user is not None and user.is_blocked
        except Exception as e:
            print(f"Ошибка при проверке блокировки пользователя: {e}")
            return False

# Создание или обновление пользователя в базе данных
async def create_or_update_user(user: types.User) -> User:
    async for session in get_db():
        try:
            db_user = await session.get(User, str(user.id))
            if db_user is None:
                db_user = User(
                    user_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    is_admin=is_admin(user.id)
                )
                session.add(db_user)
            else:
                db_user.username = user.username
                db_user.first_name = user.first_name
                
            await session.commit()
            await session.refresh(db_user)
            return db_user
        except Exception as e:
            print(f"Ошибка при создании/обновлении пользователя: {e}")
            await session.rollback()
            return None

# Обработка команды /start
@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    # Создаем или обновляем пользователя
    user = await create_or_update_user(message.from_user)
    
    # Создаем клавиатуру с кнопками
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    # Добавляем кнопки управления
    btn_analyze = KeyboardButton(text="Анализ ИИ")
    btn_add = KeyboardButton(text="Добавить")
    keyboard.add(btn_analyze)
    
    # Админ-кнопка доступна только администраторам
    if is_admin(message.from_user.id):
        btn_edit = KeyboardButton(text="Редактировать")
        keyboard.add(btn_add, btn_edit)
    else:
        keyboard.add(btn_add)
    
    # Получаем случайные пословицы из базы данных
    async for session in get_db():
        try:
            # Получаем до 5 активных пословиц
            result = await session.execute(
                select(Proverb).where(Proverb.is_active == True).order_by(func.random()).limit(5)
            )
            proverbs = result.scalars().all()
            
            if proverbs:
                proverbs_text = "\n\n".join([f"\"{p.text}\"" for p in proverbs])
                welcome_text = f"Добро пожаловать, {user.first_name}!\n\nСегодняшние пословицы:\n{proverbs_text}"
            else:
                welcome_text = f"Добро пожаловать, {user.first_name}!\n\nДобавьте первую пословицу!"
        except Exception as e:
            print(f"Ошибка при получении пословиц: {e}")
            welcome_text = f"Добро пожаловать, {user.first_name}!\n\nОшибка загрузки пословиц."
    
    await message.answer(welcome_text, reply_markup=keyboard)

# Обработка блокировки пользователя (только для админов)
@dp.message(Command(commands=['block']))
async def cmd_block(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды")
        return
    
    # Получаем ID пользователя из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Использование: /block <user_id>")
        return
    
    try:
        user_id_to_block = int(command_parts[1])
    except ValueError:
        await message.answer("Неверный формат ID пользователя")
        return
    
    async for session in get_db():
        try:
            # Находим пользователя
            user = await session.get(User, str(user_id_to_block))
            if user is None:
                await message.answer(f"Пользователь с ID {user_id_to_block} не найден")
                return
            
            # Блокируем пользователя
            user_update = UserUpdate(
                is_blocked=True,
                blocked_by=str(message.from_user.id),
                blocked_at=datetime.utcnow()
            )
            
            for key, value in user_update.model_dump(exclude_unset=True).items():
                setattr(user, key, value)
                
            await session.commit()
            await session.refresh(user)
            
            # Удаляем сообщения от заблокированного пользователя
            result = await session.execute(
                delete(Message).where(Message.chat_id == str(user_id_to_block))
            )
            await session.commit()
            
            deleted_count = result.rowcount
            await message.answer(f"Пользователь {user_id_to_block} успешно заблокирован. Удалено {deleted_count} сообщений.")
            
            # Оповещаем заблокированного пользователя
            try:
                await bot.send_message(
                    user_id_to_block,
                    "Вы были заблокированы в боте. Дальнейшее использование невозможно."
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение заблокированному пользователю: {e}")
                
        except Exception as e:
            print(f"Ошибка при блокировке пользователя: {e}")
            await session.rollback()
            await message.answer("Ошибка при блокировке пользователя")

# Обработка команды /unblock (только для админов)
@dp.message(Command(commands=['unblock']))
async def cmd_unblock(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды")
        return
    
    # Получаем ID пользователя из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Использование: /unblock <user_id>")
        return
    
    try:
        user_id_to_unblock = int(command_parts[1])
    except ValueError:
        await message.answer("Неверный формат ID пользователя")
        return
    
    async for session in get_db():
        try:
            # Находим пользователя
            user = await session.get(User, str(user_id_to_unblock))
            if user is None:
                await message.answer(f"Пользователь с ID {user_id_to_unblock} не найден")
                return
            
            # Разблокируем пользователя
            user.is_blocked = False
            user.blocked_by = None
            user.blocked_at = None
            
            await session.commit()
            await session.refresh(user)
            
            await message.answer(f"Пользователь {user_id_to_unblock} успешно разблокирован.")
            
            # Оповещаем разблокированного пользователя
            try:
                await bot.send_message(
                    user_id_to_unblock,
                    "Вы были разблокированы в боте. Теперь вы можете продолжить использование."
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение разблокированному пользователю: {e}")
                
        except Exception as e:
            print(f"Ошибка при разблокировке пользователя: {e}")
            await session.rollback()
            await message.answer("Ошибка при разблокировке пользователя")

# Обработка текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    # Проверяем, не заблокирован ли пользователь
    if await is_user_blocked(str(message.from_user.id)):
        await message.answer("Вы заблокированы в боте и не можете отправлять сообщения.")
        return
    
    # Создаем или обновляем пользователя
    user = await create_or_update_user(message.from_user)
    
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
        async for session in get_db():
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

    # Обработка кнопок
    if message.text == "Анализ ИИ":
        await message.answer("Выберите пословицу для анализа с помощью ИИ")
    elif message.text == "Добавить":
        await message.answer("Введите новую пословицу:")
    elif message.text == "Редактировать":
        if is_admin(message.from_user.id):
            await message.answer("Выберите пословицу для редактирования:")
        else:
            await message.answer("У вас нет прав для редактирования пословиц")
    else:
        # Отвечаем на сообщение
        await message.answer(f"Получено ваше сообщение: {message.text}")

# Функция для отправки сообщения
async def send_message(chat_id: str, text: str) -> bool:
    try:
        await bot.send_message(chat_id, text)
        
        # Сохраняем исходящее сообщение
        async for session in get_db():
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