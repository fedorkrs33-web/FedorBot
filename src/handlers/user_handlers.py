from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram import F
from src.config import ADMIN_IDS
from src.keyboards import get_main_menu, get_admin_menu, get_proverbs_keyboard
from src.database import get_session
from src.models import User, Proverb, AIResponse, Model
from sqlalchemy import select, func
import logging

router = Router()

@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    print("🔧 /start: начало обработки")
    async for session in get_session():
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
            
            # Отправляем кнопки управления
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

# Обработка кнопки "Просмотреть выбранную пословицу"
@router.message(F.text == "Просмотреть выбранную пословицу")
async def cmd_view_selected(message: types.Message):
    kb = await get_proverbs_keyboard(0)
    await message.answer("Выберите пословицу для просмотра анализа:", reply_markup=kb)

# Обработка выбора пословицы для анализа
@router.callback_query(F.data.startswith("proverb_"))
async def callback_proverb_analysis(callback: types.CallbackQuery):
    await callback.answer()
    proverb_id = int(callback.data.split("_")[1])
    
    async for session in get_session():
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
            await callback.message.answer(f"Анализ для пословицы «{proverb.text}» ещё не доступен. Администраторы работают над этим.")
            return
        
        # Формируем ответ с анализами
        text = f"<b>Анализ пословицы «{proverb.text}»:</b>\n\n"
        for response in responses:
            # Явно загружаем модель, чтобы избежать lazy loading
            model = await session.get(Model, response.model_id)
            text += f"<b>{model.name}</b> ({model.provider}):\n{response.response}\n\n"
        
        await callback.message.answer(text, parse_mode="HTML")

# Обработка новой кнопки "Оставить заявку на добавление"
@router.message(F.text == "Оставить заявку на добавление")
async def cmd_request_add(message: types.Message):
    await message.answer("Пожалуйста, введите текст пословицы, которую хотите добавить:")

# Обработка кнопки "Меню управления" для админов
@router.message(F.text == "Меню управления")
async def cmd_admin_menu(message: types.Message):
    if str(message.from_user.id) in map(str, ADMIN_IDS):
        await message.answer("Меню управления:", reply_markup=get_admin_menu())
    else:
        await message.answer("У вас нет прав на использование этого меню.")

# Обработка кнопки "Назад" для возврата в главное меню
@router.message(F.text == "Назад")
async def cmd_back_to_main(message: types.Message):
    async for session in get_session():
        result = await session.execute(select(User).where(User.user_id == str(message.from_user.id)))
        user = result.scalar_one_or_none()
        is_admin = user.is_admin if user else False
    await message.answer("Главное меню:", reply_markup=get_main_menu(is_admin))
