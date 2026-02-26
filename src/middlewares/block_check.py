from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.models import User
from sqlalchemy import select

class BlockCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id

        # Получаем сессию БД
        async with get_session() as session:
            result = await session.execute(
                select(User.is_blocked).where(User.user_id == user_id)
            )
            row = result.fetchone()

            if row is not None and row[0]:  # Если пользователь найден и заблокирован
                await event.answer("❌ Вы заблокированы и не можете использовать этого бота.")
                return  # Не передаём управление дальше

        # Если не заблокирован — продолжаем обработку
        return await handler(event, data)