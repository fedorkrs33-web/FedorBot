from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from src.database import get_session
from src.buttons import (
    BTN_PROVERB,
    BTN_ANALYZE_II,
    BTN_MODELS,
    BTN_PROMPTS,
    BTN_BACK,
    BTN_ADMIN_MENU,
    BTN_ADD_PROVERB,
    BTN_DELETE_PROVERB,
    BTN_ADD_PROMPT,
    BTN_DELETE_PROMPT,
    BTN_LINK_PROMPT_TO_MODEL,
)


# Основное меню
def get_main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    buttons = []
    if is_admin:
        buttons.append([KeyboardButton(text=BTN_ADMIN_MENU)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)


# Клавиатура для выбора пословиц
async def get_proverbs_keyboard(page: int = 0, limit: int = 5) -> InlineKeyboardMarkup:
    from src.models import Proverb, AIResponse

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

            proverb_ids = [p.id for p in proverbs]
            if proverb_ids:
                analysis_result = await session.execute(
                    select(AIResponse.proverb_id, func.count(AIResponse.id))
                    .where(AIResponse.proverb_id.in_(proverb_ids))
                    .group_by(AIResponse.proverb_id)
                )
                analysis_counts = dict(analysis_result.fetchall())
            else:
                analysis_counts = {}

            for p in proverbs:
                count = analysis_counts.get(p.id, 0)
                status = f"🤖{count}" if count > 0 else "⏳"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{status} \"{p.text[:30]}...\"",
                        callback_data=f"proverb_{p.id}"
                    )
                ])

            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page_{page-1}"))
            if has_next:
                nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page_{page+1}"))
            if nav:
                keyboard.append(nav)

            keyboard.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_admin")])

        except Exception as e:
            print(f"Ошибка при создании клавиатуры пословиц: {e}")

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Меню управления для админов
def get_admin_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=BTN_PROVERB), KeyboardButton(text=BTN_ANALYZE_II)],
        [KeyboardButton(text=BTN_MODELS), KeyboardButton(text=BTN_PROMPTS)]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)


# Подменю для управления пословицами
def get_proverb_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=BTN_ADD_PROVERB), KeyboardButton(text=BTN_DELETE_PROVERB)],
        [KeyboardButton(text=BTN_BACK)]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)


# Клавиатура для списка моделей
async def get_models_toggle_keyboard() -> InlineKeyboardMarkup:
    from src.models import Model

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
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True
    )


# Клавиатура для управления промтами
def get_prompt_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD_PROMPT)],
            [KeyboardButton(text=BTN_DELETE_PROMPT)],
            [KeyboardButton(text=BTN_LINK_PROMPT_TO_MODEL)],
            [KeyboardButton(text=BTN_BACK)]
        ],
        resize_keyboard=True
    )


# Клавиатура для списка промтов (асинхронная!)
async def get_prompts_list_keyboard(prompts: list, page: int = 0, limit: int = 5) -> InlineKeyboardMarkup:
    keyboard = []
    start = page * limit
    end = start + limit
    paginated = prompts[start:end]
    has_next = len(prompts) > end

    for prompt in paginated:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🔹 {prompt.text[:30]}...",
                callback_data=f"delete_prompt_{prompt.id}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prompt_page_{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"prompt_page_{page+1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_prompt_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
