from aiogram import Router, types
from aiogram.filters import Command
from aiogram import F
from src.config import ADMIN_IDS
from src.database import get_session
from src.models import User, Message, Proverb
from sqlalchemy import select, func, delete
import logging

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command(commands=['stats']))
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return

    async for session in get_session():
        try:
            msg_count = (await session.execute(select(func.count(Message.id)))).scalar()
            user_count = (await session.execute(select(func.count(User.id)))).scalar()
            proverb_count = (await session.execute(select(func.count(Proverb.id)))).scalar()
            active_count = (await session.execute(
                select(func.count(Proverb.id)).where(Proverb.is_active == True)
            )).scalar()

            text = f"""
📊 *Статистика:*
👥 Пользователей: {user_count}
💬 Сообщений: {msg_count}
📚 Пословиц: {proverb_count} ({active_count} активных)
"""
            await message.answer(text, parse_mode="Markdown")
        except Exception as e:
            logging.error(e)
            await message.answer("Ошибка при получении статистики")

@router.message(Command(commands=['clear']))
async def cmd_clear(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    async for session in get_session():
        result = await session.execute(delete(Message))
        await session.commit()
        await message.answer(f"✅ Очищено {result.rowcount} сообщений")

@router.message(Command(commands=['block']))
async def cmd_block(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Использование: /block <user_id>")
        return

    async for session in get_session():
        user = await session.get(User, str(user_id))
        if not user:
            await message.answer("Пользователь не найден.")
            return
        user.is_blocked = True
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} заблокирован.")
        try:
            await message.bot.send_message(user_id, "Вы заблокированы.")
        except Exception as e:
            logging.info(f"Не удалось уведомить: {e}")

@router.message(Command(commands=['unblock']))
async def cmd_unblock(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Использование: /unblock <user_id>")
        return

    async for session in get_session():
        user = await session.get(User, str(user_id))
        if not user:
            await message.answer("Пользователь не найден.")
            return
        user.is_blocked = False
        await session.commit()
        await message.answer(f"✅ Пользователь {user_id} разблокирован.")
