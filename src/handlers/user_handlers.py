from aiogram import Router, types
from aiogram.filters import Command
from aiogram import F
from src.config import ADMIN_IDS
from src.keyboards import get_main_menu
from src.database import get_session
from src.models import User, Proverb
from sqlalchemy import select, func
import logging

router = Router()

@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    print("🔧 /start: начало обработки")  # ← Для проверки
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

            # 📚 Получаем случайные пословицы
            result = await session.execute(
                select(Proverb).where(Proverb.is_active == True).order_by(func.random()).limit(5)
            )
            proverbs = result.scalars().all()

            text = f"Добро пожаловать, {first_name}!"
            if proverbs:
                text += "\n\nСегодняшние пословицы:\n" + "\n\n".join([f"«{p.text}»" for p in proverbs])

            await message.answer(text, reply_markup=get_main_menu(user.is_admin))

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
