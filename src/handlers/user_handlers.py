import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram import F
from src.config import ADMIN_IDS
from src.keyboards import get_main_menu, get_admin_menu, get_proverbs_keyboard
from src.database import get_session
from src.models import User, Proverb, AIResponse, Model
from sqlalchemy import select, func, delete

router = Router()

@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    print("🔧 /start: начало обработки")
    async with get_session() as session:
        try:
            user_id = str(message.from_user.id)
            username = message.from_user.username
            first_name = message.from_user.first_name or "Клиент"

            # 🔍 Ищем пользователя по user_id
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                print(f"✅ Создаём нового пользователя: {user_id}")
                new_user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    is_admin=(user_id in map(str, ADMIN_IDS))
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                user = new_user
            else:
                print(f"🔄 Пользователь найден: {user_id}, обновляем данные при необходимости")
                updated = False
                if user.username != username:
                    user.username = username
                    updated = True
                if user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                current_is_admin = user_id in map(str, ADMIN_IDS)
                if user.is_admin != current_is_admin:
                    user.is_admin = current_is_admin
                    updated = True

                if updated:
                    await session.commit()
                    await session.refresh(user)

            # Формируем приветствие
            welcome_text = f"Добро пожаловать, <b>{first_name}</b>!\n\n"
            
            # Отправляем приветствие
            await message.answer(welcome_text, parse_mode="HTML", disable_notification=True)
            
            # Отправляем интерактивную таблицу пословиц
            proverb_kb = await get_proverbs_keyboard(0)
            await message.answer("Выберите пословицу:", reply_markup=proverb_kb, disable_notification=True)
            
            # Отправляем основное меню (только для администраторов)
            await message.answer("Выберите действие:", reply_markup=get_main_menu(user.is_admin), disable_notification=True)

        except Exception as e:
            logging.error(f"Ошибка в /start: {e}")

@router.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    help_text = """
🤖 *Доступные команды:*

/start - Начать
/help - Помощь
/stats - Статистика (админ)

💡 Функции:
• Просмотр и анализ пословиц
• Добавление новых
• Интерпретация ИИ
"""
    await message.answer(help_text, parse_mode="Markdown")

# Удалён обработчик просмотра выбранной пословицу, так как кнопка больше не выводится

# Обработка выбора пословицы для анализа
@router.callback_query(F.data.startswith("proverb_"))
async def callback_proverb_analysis(callback: types.CallbackQuery):
    proverb_id = int(callback.data.split("_")[1])
    
    async with get_session() as session:
        # Получаем пословицу
        proverb = await session.get(Proverb, proverb_id)
        if not proverb or not proverb.is_active:
            await callback.message.answer("Пословица не найдена.")
            return
        
        # Получаем анализ из БД
        result = await session.execute(
            select(AIResponse)
            .where(AIResponse.proverb_id == proverb_id)
            .order_by(AIResponse.created_at.desc())
        )
        responses = result.scalars().all()
        
        if not responses:
            # Создаём клавиатуру с кнопкой "Анализировать сейчас"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Анализировать сейчас", callback_data=f"analyze_{proverb_id}")],
                [types.InlineKeyboardButton(text="Назад", callback_data="back_to_proverbs")]
            ])
            await callback.message.edit_text(f"Анализ для пословицы «{proverb.text}» ещё не доступен.\nХотите инициировать анализ?", reply_markup=keyboard)
            await callback.answer()
            return
        
        # Формируем и отправляем каждый анализ
        for response in responses:
            # Явно загружаем модель, чтобы избежать lazy loading
            model = await session.get(Model, response.model_id)
            
            # Формируем заголовок
            header = f"<b>{model.name}</b> ({model.provider}):\n\n"
            full_text = header + response.response
            
            # Разбиваем длинные сообщения
            while len(full_text) > 4000:
                part = full_text[:4000]
                await callback.message.answer(part, parse_mode="HTML")
                full_text = full_text[4000:]
            
            # Отправляем остаток
            if full_text:
                await callback.message.answer(full_text, parse_mode="HTML")
        
        # Обновляем оригинальное сообщение с кнопками
        kb = await get_proverbs_keyboard(0)
        if callback.message:
            try:
                await callback.message.edit_text("Выберите пословицу для просмотра анализа:", reply_markup=kb)
            except Exception as e:
                logging.error(f"Ошибка при обновлении сообщения: {e}")
                # Если не удалось обновить, отправляем новое
                await callback.message.answer("Выберите пословицу для просмотра анализа:", reply_markup=kb)
        
        # Отправляем подтверждение
        await callback.answer()

# Обработка новой кнопки "Оставить заявку на добавление"
# Удалён обработчик заявки на добавление, так как кнопка больше не выводится

# Обработка кнопки "Меню управления" для админов
@router.message(F.text == "Меню управления")
async def cmd_admin_menu(message: types.Message):
    if str(message.from_user.id) in map(str, ADMIN_IDS):
        await message.answer("Меню управления:", reply_markup=get_admin_menu())
    else:
        await message.answer("У вас нет прав на использование этого меню.")

# Обработка кнопки "Назад" для возврата в главное меню
# Удалён обработчик кнопки "Назад", так как она больше не нужна
