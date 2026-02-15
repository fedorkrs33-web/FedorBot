from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from src.models import Proverb, AIResponse
from sqlalchemy import select

# Основное меню
def get_main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Просмотреть выбранную пословицу")],
        [KeyboardButton(text="Оставить заявку на добавление")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="Меню управления")])
    
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

            # Получаем статус анализа для каждой пословицы
            proverb_ids = [p.id for p in proverbs]
            analysis_result = await session.execute(
                select(AIResponse.proverb_id)
                .where(AIResponse.proverb_id.in_(proverb_ids))
                .distinct()
            )
            analyzed_ids = {row[0] for row in analysis_result.fetchall()}
            
            for p in proverbs:
                status = "✅" if p.id in analyzed_ids else "⏳"
                keyboard.append([
                    InlineKeyboardButton(text=f"{status} \"{p.text[:30]}...\"", callback_data=f"proverb_{p.id}")
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

# Меню управления для админов
def get_admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Пословица"), KeyboardButton(text="Анализ ИИ")],
        [KeyboardButton(text="Модели"), KeyboardButton(text="Промт")]    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)

# Подменю для управления пословицами
def get_proverb_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Добавить"), KeyboardButton(text="Удалить")],
        [KeyboardButton(text="Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)

# Клавиатура для списка моделей с переключателями
async def get_models_toggle_keyboard() -> InlineKeyboardMarkup:
    from src.models import Model
    from sqlalchemy import select
    from src.database import get_session
    
    keyboard = []
    async for session in get_session():
        result = await session.execute(select(Model))
        models = result.scalars().all()
        
        for model in models:
            status = "✅" if model.is_active else "❌"
            btn_text = f"{status} {model.name} ({model.provider})"
            keyboard.append([
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"toggle_model_{model.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_list_models")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура для возврата в меню управления
def get_back_to_admin_menu() -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text="Назад")]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)
