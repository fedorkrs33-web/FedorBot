# src/utils.py
import re
from aiogram import types

def escape_markdown_v2(text: str) -> str:
    """
    Экранирует спецсимволы для MarkdownV2.
    https://core.telegram.org/bots/api#markdownv2-style
    """
    escape_chars = r'_*[]()~>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


async def safe_send_message(
    message: types.Message | types.CallbackQuery,
    text: str,
    parse_mode: str = "MarkdownV2",
    reply_markup: types.InlineKeyboardMarkup | types.ReplyKeyboardMarkup | None = None,
    edit: bool = False,
    disable_web_page_preview: bool = False
):
    """
    Безопасно отправляет или редактирует сообщение.
    - Автоматически экранирует MarkdownV2.
    - Делит текст, если он слишком длинный.
    - Использует edit_text или answer в зависимости от контекста.
    """
    # Экранируем только если используем MarkdownV2
    if parse_mode == "MarkdownV2":
        text = escape_markdown_v2(text)

    # Ограничиваем длину одной части
    MAX_LENGTH = 4096
    parts = [text[i:i + MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]

    # Получаем объект сообщения
    msg = message.message if isinstance(message, types.CallbackQuery) else message

    try:
        if edit and hasattr(msg, "message_id"):
            # Редактируем первое сообщение
            await msg.edit_text(
                parts[0],
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            # Остальные части — отправляем как новые
            for part in parts[1:]:
                await msg.answer(
                    part,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview
                )
        else:
            # Просто отправляем (новое сообщение)
            for i, part in enumerate(parts):
                if i == 0:
                    await msg.answer(
                        part,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup if i == 0 else None,
                        disable_web_page_preview=disable_web_page_preview
                    )
                else:
                    await msg.answer(
                        part,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview
                    )
    except Exception as e:
        # Если Markdown сломался — пробуем без форматирования
        if parse_mode == "MarkdownV2":
            print(f"⚠️ Ошибка с MarkdownV2, повторяем без парсинга: {e}")
            await safe_send_message(
                message=message,
                text=text.replace('\\', ''),  # убираем экранирование
                parse_mode=None,
                reply_markup=reply_markup,
                edit=edit,
                disable_web_page_preview=disable_web_page_preview
            )
        else:
            print(f"❌ Не удалось отправить сообщение: {e}")
            await msg.answer("❌ Произошла ошибка при отправке.")