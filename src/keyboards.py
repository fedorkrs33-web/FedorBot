from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основное меню
def get_main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text="Анализ ИИ")]]
    
    if is_admin:
        buttons.append([KeyboardButton(text="Добавить"), KeyboardButton(text="Редактировать")])
    else:
        buttons.append([KeyboardButton(text="Добавить")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)

# Клавиатура для выбора пословиц
async def get_proverbs_keyboard(page: int = 0, limit: int = 5) -> InlineKeyboardMarkup:
    from src.models import Proverb
    from sqlalchemy import select, func
    from src.database import get_session

    keyboard = []
    async for session in get_session():
        try:
            result = await session.execute(
                select(Proverb)
                .where(Proverb.is_active == True)
                .order_by(Proverb.added_at.desc())
                .offset(page * limit)
                .limit(limit + 1)
            )
            proverbs = result.scalars().all()
            has_next = len(proverbs) > limit
            proverbs = proverbs[:limit]

            for p in proverbs:
                keyboard.append([
                    InlineKeyboardButton(text=f"\"{p.text[:30]}...\"", callback_data=f"proverb_{p.id}")
                ])

            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page-1}"))
            if has_next:
                nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page_{page+1}"))
            if nav:
                keyboard.append(nav)

        except Exception as e:
            print(f"Ошибка при создании клавиатуры пословиц: {e}")

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
