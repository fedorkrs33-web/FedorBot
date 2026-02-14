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
from typing import Optional

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
                await session.commit()
                await session.refresh(db_user)
                return db_user
            else:
                # Обновляем данные пользователя только если они изменились
                updated = False
                if db_user.username != user.username:
                    db_user.username = user.username
                    updated = True
                if db_user.first_name != user.first_name:
                    db_user.first_name = user.first_name
                    updated = True
                if db_user.is_admin != is_admin(user.id):
                    db_user.is_admin = is_admin(user.id)
                    updated = True
                
                if updated:
                    await session.commit()
                    await session.refresh(db_user)
                
                return db_user
        except Exception as e:
            print(f"Ошибка при создании/обновлении пользователя: {e}")
            await session.rollback()
            # Возвращаем None только в случае критической ошибки
            if "UNIQUE constraint failed" in str(e):
                # Пользователь уже существует, получаем его из базы
                try:
                    db_user = await session.get(User, str(user.id))
                    return db_user
                except:
                    return None
            return None

async def get_proverbs_keyboard(page: int = 0, limit: int = 5) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с пословицами из базы данных
    """
    keyboard = []
    
    async for session in get_db():
        try:
            # Получаем пословицы с пагинацией
            result = await session.execute(
                select(Proverb)
                .where(Proverb.is_active == True)
                .order_by(Proverb.added_at.desc())
                .offset(page * limit)
                .limit(limit + 1)  # +1 для проверки наличия следующей страницы
            )
            proverbs = result.scalars().all()
            
            has_next_page = len(proverbs) > limit
            if has_next_page:
                proverbs = proverbs[:-1]
            
            # Добавляем кнопки для каждой пословицы
            for proverb in proverbs:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"\"{proverb.text[:30]}...\"", 
                        callback_data=f"proverb_{proverb.id}"
                    )
                ])
                
        except Exception as e:
            print(f"Ошибка при получении пословиц для клавиатуры: {e}")
            return InlineKeyboardMarkup(inline_keyboard=[])
    
    # Добавляем навигацию по страницам
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", 
                callback_data=f"page_{page-1}"
            )
        )
    if has_next_page:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", 
                callback_data=f"page_{page+1}"
            )
        )
    
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def send_proverbs_page(message: types.Message, page: int = 0):
    """
    Отправляет страницу пословиц пользователю
    """
    keyboard = await get_proverbs_keyboard(page)
    
    if not keyboard.inline_keyboard:
        await message.answer("Пока нет ни одной пословицы. Добавьте первую!")
        return
    
    text = "Выберите пословицу:" if page == 0 else f"Страница {page + 1} пословиц:" 
    await message.answer(text, reply_markup=keyboard)


@dp.callback_query()
async def handle_callback_query(callback: types.CallbackQuery):
    """
    Обработка нажатий на кнопки в инлайн-клавиатуре
    """
    try:
        data = callback.data
        
        if data.startswith("page_"):
            page = int(data.split("_")[1])
            await send_proverbs_page(callback.message, page)
            
        elif data.startswith("proverb_"):
            proverb_id = int(data.split("_")[1])
            
            # Получаем выбранную пословицу
            async for session in get_db():
                try:
                    proverb = await session.get(Proverb, proverb_id)
                    if proverb and proverb.is_active:
                        text = f"Выбрана пословица:\n\"{proverb.text}\"\n\nЧто вы хотите с ней сделать?"
                        
                        # Клавиатура действий с пословицей
                        actions_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Анализ ИИ", callback_data=f"analyze_{proverb_id}")],
                            [InlineKeyboardButton(text="Поделиться", callback_data=f"share_{proverb_id}")]
                        ])
                        
                        # Для администраторов добавляем опции редактирования и удаления
                        if is_admin(callback.from_user.id):
                            actions_keyboard.inline_keyboard.append(
                                [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_{proverb_id}")]
                            )
                            actions_keyboard.inline_keyboard.append(
                                [InlineKeyboardButton(text="Удалить", callback_data=f"delete_{proverb_id}")]
                            )
                        
                        await callback.message.edit_text(text, reply_markup=actions_keyboard)
                    else:
                        await callback.answer("Пословица не найдена или удалена")
                
                except Exception as e:
                    print(f"Ошибка при обработке callback запроса для пословиц: {e}")
                    await callback.answer("Произошла ошибка при обработке запроса")
        
        elif data.startswith("analyze_"):
            proverb_id = int(data.split("_")[1])
            await cmd_analyze_proverb(callback, proverb_id)
        
        elif data.startswith("edit_"):
            proverb_id = int(data.split("_")[1])
            await cmd_edit_proverb_id(callback, proverb_id)
        
        elif data.startswith("delete_"):
            proverb_id = int(data.split("_")[1])
            await cmd_delete_proverb(callback, proverb_id)
        
        elif data.startswith("share_"):
            proverb_id = int(data.split("_")[1])
            await cmd_share_proverb(callback, proverb_id)
        
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка при обработке callback запроса: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")


# Обработка команды /start
@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    # Создаем или обновляем пользователя
    user = await create_or_update_user(message.from_user)
    if user is None:
        await message.answer("Ошибка при создании пользователя. Попробуйте позже.")
        return
    
    # Создаем клавиатуру с кнопками
    keyboard = []
    
    # Добавляем кнопки управления
    btn_analyze = KeyboardButton(text="Анализ ИИ")
    btn_add = KeyboardButton(text="Добавить")
    keyboard.append([btn_analyze])
    
    # Админ-кнопка доступна только администраторам
    if is_admin(message.from_user.id):
        btn_edit = KeyboardButton(text="Редактировать")
        keyboard.append([btn_add, btn_edit])
    else:
        keyboard.append([btn_add])
    
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
    
    if user is None:
        await message.answer("Ошибка при создании пользователя. Попробуйте позже.")
        return
    
    # Создаем ReplyKeyboardMarkup с клавиатурой
    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await message.answer(welcome_text, reply_markup=reply_markup)

# Обработка команды /help
@dp.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    help_text = """
🤖 *Доступные команды:*

/start - Начать работу с ботом
/help - Показать эту справку
/stats - Показать статистику

💡 *Функции бота:*

• Просмотр и анализ пословиц
• Добавление новых пословиц
• Интерпретация пословиц с помощью ИИ
• Сравнение различных интерпретаций

🛠 *Администрирование (для администраторов):*

• /block <user_id> - Блокировка пользователя
• /unblock <user_id> - Разблокировка пользователя
• /clear - Очистка истории сообщений
• Редактирование и удаление пословиц
    """
    
    await message.answer(help_text, parse_mode="Markdown")


# Обработка команды /stats (только для админов)
@dp.message(Command(commands=['stats']))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для просмотра статистики")
        return
    
    async for session in get_db():
        try:
            # Подсчет сообщений
            messages_count = await session.execute(
                select(func.count(Message.id))
            )
            messages_count = messages_count.scalar()
            
            # Подсчет пользователей
            users_count = await session.execute(
                select(func.count(User.id))
            )
            users_count = users_count.scalar()
            
            # Подсчет пословиц
            proverbs_count = await session.execute(
                select(func.count(Proverb.id))
            )
            proverbs_count = proverbs_count.scalar()
            
            # Активные пословиц
            active_proverbs_count = await session.execute(
                select(func.count(Proverb.id)).where(Proverb.is_active == True)
            )
            active_proverbs_count = active_proverbs_count.scalar()
            
            # Формируем сообщение со статистикой
            stats_text = f"""
📊 *Статистика бота:*

👥 Пользователи: {users_count}
💬 Сообщения: {messages_count}
📚 Всего пословиц: {proverbs_count}
✅ Активных пословиц: {active_proverbs_count}
❌ Удаленных пословиц: {proverbs_count - active_proverbs_count}

⏱ *Время работы:*
Бот запущен и готов к работе!
            """
            
            await message.answer(stats_text, parse_mode="Markdown")
            
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            await message.answer("Ошибка при получении статистики")


# Обработка команды /clear (только для админов)
@dp.message(Command(commands=['clear']))
async def cmd_clear(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав для выполнения этой команды")
        return
    
    async for session in get_db():
        try:
            # Удаляем все сообщения
            result = await session.execute(delete(Message))
            await session.commit()
            
            deleted_count = result.rowcount
            await message.answer(f"✅ Очищено {deleted_count} сообщений")
            
        except Exception as e:
            print(f"Ошибка при очистке сообщений: {e}")
            await session.rollback()
            await message.answer("❌ Ошибка при очистке сообщений")


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

# Обработка команды /analyze
async def cmd_analyze_proverbs(message: types.Message):
    """
    Обработка команды анализа пословиц
    """
    await send_proverbs_page(message)


# Обработка команды /add
async def cmd_add_proverb(message: types.Message):
    """
    Обработка команды добавления пословицы
    """
    await message.answer("Введите текст новой пословицы:")


# Обработка команды /edit
async def cmd_edit_proverb(message: types.Message):
    """
    Обработка команды редактирования пословицы
    """
    await send_proverbs_page(message)


# Обработка команды анализа конкретной пословицы
async def cmd_analyze_proverb(callback: types.CallbackQuery, proverb_id: int):
    """
    Обработка анализа выбранной пословицы
    """
    async for session in get_db():
        try:
            proverb = await session.get(Proverb, proverb_id)
            if proverb and proverb.is_active:
                # Здесь будет интеграция с ИИ-моделями
                response_text = f"ИИ-анализ пословицы:\n\"{proverb.text}\"\n\nПока функция в разработке. В будущем здесь будут отображаться интерпретации от различных ИИ-моделей."
                
                # Кнопка для сравнения интерпретаций
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Сравнить интерпретации", callback_data=f"compare_{proverb_id}")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_proverbs")]
                ])
                
                await callback.message.edit_text(response_text, reply_markup=keyboard)
            else:
                await callback.answer("Пословица не найдена или удалена")
        except Exception as e:
            print(f"Ошибка при анализе пословицы: {e}")
            await callback.answer("Произошла ошибка при анализе пословицы")


# Обработка редактирования конкретной пословицы
async def cmd_edit_proverb_id(callback: types.CallbackQuery, proverb_id: int):
    """
    Начало процесса редактирования пословицы
    """
    async for session in get_db():
        try:
            proverb = await session.get(Proverb, proverb_id)
            if proverb and proverb.is_active:
                text = f"Редактирование пословицы:\n\"{proverb.text}\"\n\nВведите новый текст пословицы или /cancel для отмены."
                
                # Сохраняем состояние редактирования
                # В реальном приложении это нужно хранить в базе данных или state
                
                await callback.message.edit_text(text)
                # Здесь нужно установить состояние ожидания нового текста
                # Это требует использования FSM (Finite State Machine)
            else:
                await callback.answer("Пословица не найдена или удалена")
        except Exception as e:
            print(f"Ошибка при начале редактирования пословицы: {e}")
            await callback.answer("Произошла ошибка при редактировании пословицы")


# Обработка удаления пословицы
async def cmd_delete_proverb(callback: types.CallbackQuery, proverb_id: int):
    """
    Обработка удаления пословицы
    """
    async for session in get_db():
        try:
            proverb = await session.get(Proverb, proverb_id)
            if proverb and proverb.is_active:
                # Помечаем пословицу как неактивную вместо физического удаления
                proverb.is_active = False
                await session.commit()
                
                await callback.answer("Пословица успешно удалена")
                # Возвращаемся к списку пословиц
                await send_proverbs_page(callback.message)
            else:
                await callback.answer("Пословица уже удалена")
        except Exception as e:
            print(f"Ошибка при удалении пословицы: {e}")
            await session.rollback()
            await callback.answer("Произошла ошибка при удалении пословицы")


# Обработка команды /share
async def cmd_share_proverb(callback: types.CallbackQuery, proverb_id: int):
    """
    Обработка команды делиться пословицей
    """
    async for session in get_db():
        try:
            proverb = await session.get(Proverb, proverb_id)
            if proverb and proverb.is_active:
                text = f"\"{proverb.text}\"\n\n#пословица #мудрость #FedorBot"
                
                # Кнопки для отправки в другие чаты
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Отправить другу", url=f"tg://msg_url?url={text}")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_proverbs")]
                ])
                
                await callback.message.edit_text(f"Поделиться пословицей:\n{text}", reply_markup=keyboard)
            else:
                await callback.answer("Пословица не найдена или удалена")
        except Exception as e:
            print(f"Ошибка при делении пословицей: {e}")
            await callback.answer("Произошла ошибка при делении пословицей")


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
        await cmd_analyze_proverbs(message)
    elif message.text == "Добавить":
        await cmd_add_proverb(message)
    elif message.text == "Редактировать":
        if is_admin(message.from_user.id):
            await cmd_edit_proverb(message)
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