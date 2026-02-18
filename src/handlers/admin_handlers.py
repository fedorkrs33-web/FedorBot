import logging
logger = logging.getLogger(__name__)
from aiogram import Router, types, F
from aiogram.filters import Command
from src.config import ADMIN_IDS
from src.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging
from src.keyboards import (
    get_admin_menu,
    get_proverb_menu,
    get_back_to_admin_menu,
    get_models_toggle_keyboard,
    get_prompt_menu,
    get_proverbs_keyboard,
    get_prompts_list_keyboard,
)
from src.network import Network
import asyncio
from datetime import datetime
from src.states import PromptStates
from src.models import User, Message, Proverb, Model, AIResponse, Prompt, Comparison
from src.buttons import (
    BTN_PROVERB, BTN_ANALYZE_II, BTN_MODELS, BTN_PROMPTS,
    BTN_ADD_PROVERB, BTN_DELETE_PROVERB,
    BTN_ADD_PROMPT, BTN_DELETE_PROMPT, BTN_LINK_PROMPT_TO_MODEL,
    BTN_BACK
)



router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Обработка кнопки "Пословица"
@router.message(F.text == BTN_PROVERB)
async def cmd_proverb_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Выберите действие с пословицами:", reply_markup=get_proverb_menu())

# Обработка кнопки "Добавить" в подменю
@router.message(F.text == BTN_ADD_PROVERB)
async def cmd_add_proverb(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Введите текст новой пословицы:")
    # Здесь должна быть реализация FSM для добавления

# Обработка кнопки "Удалить" в подменю
@router.message(F.text == BTN_DELETE_PROVERB)
async def cmd_delete_proverb(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    keyboard = await get_proverbs_keyboard(0)
    await message.answer("Выберите пословицу для удаления:", reply_markup=keyboard)

# Обработка кнопки "Анализ ИИ"
@router.message(F.text == BTN_ANALYZE_II)
async def cmd_analyze_ii(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    keyboard = await get_proverbs_keyboard(0)
    await message.answer("Выберите пословицу для анализа:", reply_markup=keyboard)


# Обработка выбора пословицы для анализа
@router.callback_query(F.data.startswith("analyze_"))
async def process_analyze_proverb(callback: types.CallbackQuery):
    try:
        await callback.answer()
        proverb_id = int(callback.data.split("_")[1])

        async with get_session() as session:
            result = await session.execute(
                select(Proverb).where(Proverb.id == proverb_id, Proverb.is_active == True)
            )
            proverb = result.scalar_one_or_none()

            if not proverb:
                await callback.message.edit_text("❌ Пословица не найдена или удалена.")
                return

            await callback.message.edit_text(f"🔍 Анализируем пословицу:\n\n«{proverb.text}»\n\nПодождите...")

            result = await session.execute(
                select(Model)
                .where(Model.is_active == True)
                .options(selectinload(Model.prompt))  # ← Подгружаем prompt сразу
            )
            active_models = result.scalars().all()

            if not active_models:
                await callback.message.edit_text("⚠️ Нет активных моделей ИИ.")
                return

        # Сбор ответов
        network = Network()
        responses = []

        async with get_session() as session:
            for model in active_models:
                try:
                    prompt_text = "Объясни смысл этой пословицы простыми словами."
                    if model.prompt and model.prompt.is_active:
                        prompt_text = model.prompt.text
                    elif model.prompt_id:
                        prompt_text = "⚠️ Промт удалён. Используется стандартный."

                    final_prompt = f"{prompt_text}\n\nПословица: {proverb.text}"

                    response_text = await asyncio.wait_for(
                        network.send_prompt_to_model({
                            "name": model.name,
                            "provider": model.provider,
                            "api_url": model.api_url,
                            "api_key_var": model.api_key_var,
                            "model_name": model.model_name or model.name,
                        }, final_prompt),
                        timeout=30.0
                    )

                    responses.append({"model": model.name, "response": response_text})

                    ai_response = AIResponse(
                        proverb_id=proverb.id,
                        model_id=model.id,
                        prompt=final_prompt,
                        response=response_text
                    )
                    session.add(ai_response)

                except asyncio.TimeoutError:
                    responses.append({"model": model.name, "response": "⏰ Таймаут"})
                except Exception as e:
                    logging.error(f"Ошибка при генерации от {model.name}: {e}")
                    responses.append({"model": model.name, "response": f"❌ Ошибка: {str(e)}"})

            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                logging.error(f"Ошибка при сохранении ответов: {e}")
                await callback.message.edit_text("❌ Не удалось сохранить результаты.")
                return

        # Формирование результата
        result_text = f"✅ Результаты анализа пословицы:\n\n«{proverb.text}»\n\n"
        for r in responses:
            result_text += f"\n🤖 *{r['model']}*\n{r['response']}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back_to_proverbs")]
        ])
        if len(responses) > 1:
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(text="Сравнить интерпретации", callback_data=f"compare_{proverb_id}")
            ])

        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            await callback.message.edit_text(parts[0], reply_markup=None, parse_mode="Markdown")
            for part in parts[1:]:
                await callback.message.answer(part, parse_mode="Markdown")
        else:
            await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка при анализе пословицы: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при анализе.")


# --- СРАВНЕНИЕ ИНТЕРПРЕТАЦИЙ ---
@router.callback_query(F.data.startswith("compare_"))
async def cmd_compare_interpretations(callback: types.CallbackQuery):
    try:
        await callback.answer()
        proverb_id = int(callback.data.split("_")[1])

        async with get_session() as session:
            result = await session.execute(
                select(Proverb).where(Proverb.id == proverb_id, Proverb.is_active == True)
            )    
            proverb = result.scalar_one_or_none()

            if not proverb or not proverb.is_active:
                await callback.message.edit_text("❌ Пословица не найдена.")
                return

            # Получаем все ответы ИИ
            result = await session.execute(
                select(AIResponse)
                .join(Model)
                .where(AIResponse.proverb_id == proverb_id)
                .order_by(Model.name)
            )
            responses = result.scalars().all()

            if len(responses) < 2:
                await callback.message.edit_text(
                    "⚠️ Нужно как минимум 2 ответа для сравнения."
                )
                return

            # Сортируем и получаем ID моделей
            sorted_model_ids = sorted({r.model_id for r in responses})
            model_ids_str = ",".join(map(str, sorted_model_ids))

            # 🔍 Проверяем кэш
            cache_result = await session.execute(
                select(Comparison).where(
                    Comparison.proverb_id == proverb_id,
                    Comparison.model_ids == model_ids_str
                )
            )
            cached = cache_result.scalar_one_or_none()

            if cached:
                result_text = cached.result_text
                await callback.message.edit_text("📊 Найдено в кэше. Загружаю сравнение...")
            else:
                # Формируем промпт для сравнения
                comparison_text = f"""
Пословица: "{proverb.text}"

Проанализируй и сравни следующие интерпретации. Выдели:
1. Общие идеи
2. Различия в подходе
3. Стиль изложения
4. Глубину анализа

Сделай краткий, содержательный итоговый вывод.

Интерпретации:
"""
                for resp in responses:
                    name = resp.model.name if resp.model else "Неизвестно"
                    content = resp.response[:600] + "..." if len(resp.response) > 600 else resp.response
                    comparison_text += f"\n--- {name} ---\n{content}\n"

                comparison_text += "\n\nСравни и сделай вывод."

                await callback.message.edit_text("🔍 Сравниваю интерпретации... Подождите.")

                # Отправляем в GigaChat
                network = Network()
                model_data = {
                    "name": "GigaChat",
                    "provider": "gigachat",
                    "api_url": "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    "api_key_var": "GIGACHAT_CLIENT_ID",
                    "model_name": "GigaChat"
                }

                try:
                    result_text = await asyncio.wait_for(
                        network.send_prompt_to_model(model_data, comparison_text),
                        timeout=30.0
                    )

                    # 📦 Сохраняем в кэш
                    new_comparison = Comparison(
                        proverb_id=proverb_id,
                        result_text=result_text,
                        model_ids=model_ids_str
                    )
                    session.add(new_comparison)
                    await session.commit()

                except asyncio.TimeoutError:
                    await callback.message.edit_text("⏰ Время ожидания истекло при сравнении.")
                    return
                except Exception as e:
                    logging.error(f"Ошибка при генерации сравнения: {e}")
                    await callback.message.edit_text("❌ Ошибка при сравнении.")
                    return

            # ✅ Отправляем результат (всегда)
            if len(result_text) > 4000:
                parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
                await callback.message.edit_text(parts[0], parse_mode="Markdown")
                for part in parts[1:]:
                    await callback.message.answer(part, parse_mode="Markdown")
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data=f"proverb_{proverb_id}")]
                ])
                await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка в cmd_compare_interpretations: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при сравнении.")


# Обработка кнопки "Модели"
@router.message(F.text == BTN_MODELS)
async def cmd_models_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    kb = await get_models_toggle_keyboard()
    await message.answer("Управление моделями ИИ:", reply_markup=kb)

# Обработка переключения состояния модели
@router.callback_query(F.data.startswith("toggle_model_"))
async def callback_toggle_model(callback: types.CallbackQuery):
    await callback.answer()
    model_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        model = await session.get(Model, model_id)
        if not model:
            await callback.answer("Модель не найдена", show_alert=True)
            return
        
        # Меняем статус активности
        model.is_active = not model.is_active
        await session.commit()
        
        # Отправляем уведомление
        status = "включена" if model.is_active else "отключена"
        await callback.answer(f"Модель \"{model.name}\" {status}", show_alert=True)
        
        # Обновляем клавиатуру
        kb = await get_models_toggle_keyboard()
        await callback.message.edit_reply_markup(reply_markup=kb)

# Обработка кнопки "Назад" для возврата в меню управления
@router.message(F.text == BTN_BACK)
async def cmd_back_to_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Меню управления:", reply_markup=get_admin_menu())

# Обработка callback для обновления клавиатуры моделей
@router.callback_query(F.data == "ai_list_models")
async def callback_refresh_models(callback: types.CallbackQuery):
    await callback.answer()
    kb = await get_models_toggle_keyboard()
    await callback.message.edit_reply_markup(reply_markup=kb)

# Обработка callback для возврата из меню моделей
@router.callback_query(F.data == "admin_back")
async def callback_admin_back(callback: types.CallbackQuery):
    await callback.answer()
    if not is_admin(callback.from_user.id):
        await callback.message.answer("❌ Нет прав.")
        return
    await callback.message.answer("Меню управления:", reply_markup=get_admin_menu())

# --- ОБРАБОТЧИКИ ДЛЯ ПРОМТОВ ---

@router.message(F.text == BTN_PROMPTS)
async def cmd_prompt_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Выберите действие:", reply_markup=get_prompt_menu())

@router.message(F.text == BTN_ADD_PROMPT)
async def cmd_add_prompt(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Введите текст нового промпта:")
    await state.set_state(PromptStates.waiting_for_text)

@router.message(PromptStates.waiting_for_text)
async def process_new_prompt(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 5:
        await message.answer("Слишком короткий промпт. Введите более содержательный текст.")
        return

    logger.info(f"Админ {message.from_user.id} добавил промт: {text[:60]}...")

    async with get_session() as session:
        try:
            prompt = Prompt(
                text=text,
                created_by=str(message.from_user.id)
            )
            session.add(prompt)
            await session.commit()
            await message.answer(f"✅ Промпт добавлен:\n\n{text}")
        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка при добавлении промта: {e}")
            await message.answer("❌ Не удалось добавить промпт.")
    
    await state.clear()

@router.message(F.text == BTN_DELETE_PROMPT)
async def cmd_delete_prompt(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return

    async with get_session() as session:
        result = await session.execute(select(Prompt).where(Prompt.is_active == True))
        prompts = result.scalars().all()

        if not prompts:
            await message.answer("📭 Нет доступных промптов.")
            return

        kb = await get_prompts_list_keyboard(prompts, page=0)
        await message.answer("Выберите промпт для удаления:", reply_markup=kb)

# --- CALLBACK: Пагинация и удаление ---
@router.callback_query(F.data.startswith("prompt_page_"))
async def callback_prompt_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    async with get_session() as session:
        result = await session.execute(select(Prompt).where(Prompt.is_active == True))
        prompts = result.scalars().all()
        kb = await get_prompts_list_keyboard(prompts, page)
        await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_prompt_"))
async def callback_delete_prompt(callback: types.CallbackQuery):
    prompt_id = int(callback.data.split("_")[2])
    async with get_session() as session:
        try:
            prompt = await session.get(Prompt, prompt_id)
            if not prompt or not prompt.is_active:
                await callback.answer("Уже удалён.")
                return
            prompt.is_active = False
            await session.commit()
            await callback.answer("🗑️ Промпт удалён.")
            await callback.message.edit_text("Промпт успешно удалён.", parse_mode="Markdown")
        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка при удалении промта: {e}")
            await callback.answer("❌ Ошибка при удалении.")


@router.callback_query(F.data == "back_to_prompt_menu")
async def callback_back_to_prompt_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Выберите действие:", reply_markup=get_prompt_menu())

@router.message(F.text == BTN_LINK_PROMPT_TO_MODEL)
async def cmd_link_prompt_to_model(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return

    async with get_session() as session:
        result = await session.execute(select(Model).where(Model.is_active == True))
        models = result.scalars().all()
        result = await session.execute(select(Prompt).where(Prompt.is_active == True))
        prompts = result.scalars().all()

        if not models:
            await message.answer("📭 Нет активных моделей.")
            return
        if not prompts:
            await message.answer("📭 Нет доступных промптов. Сначала добавьте хотя бы один.")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=m.name,
                callback_data=f"select_model_for_prompt:{m.id}"
            )] for m in models
        ])
        await message.answer("Выберите модель:", reply_markup=kb)


@router.callback_query(F.data.startswith("select_model_for_prompt:"))
async def callback_select_model_for_prompt(callback: types.CallbackQuery):
    try:
        model_id = int(callback.data.split(":")[1])

        async with get_session() as session:
            model = await session.get(Model, model_id)
            if not model:
                await callback.answer("❌ Модель не найдена.")
                return

            prompts = (await session.execute(
                select(Prompt).where(Prompt.is_active == True)
            )).scalars().all()

            if not prompts:
                await callback.message.edit_text("📭 Нет доступных промптов. Сначала добавьте хотя бы один.")
                return

            # Формируем inline-кнопки — теперь только названия (без текста)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🔹 {p.text[:40]}{'...' if len(p.text) > 40 else ''}",
                    callback_data=f"preview_prompt:{model.id}:{p.id}"
                )] for p in prompts
            ])
            kb.inline_keyboard.append([
                InlineKeyboardButton(text="❌ Без промта", callback_data=f"assign_prompt:{model.id}:null")
            ])
            kb.inline_keyboard.append([
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")
            ])

            await callback.message.edit_text(
                f"Выберите промт для модели *{model.name}*\n\n"
                "👉 Нажмите на промт, чтобы увидеть полный текст.",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка в callback_select_model_for_prompt: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data.startswith("preview_prompt:"))
async def callback_preview_prompt(callback: types.CallbackQuery):
    try:
        parts = callback.data.split(":")
        model_id = int(parts[1])
        prompt_id = int(parts[2])

        async with get_session() as session:
            model = await session.get(Model, model_id)
            prompt = await session.get(Prompt, prompt_id)

            if not model or not prompt or not prompt.is_active:
                await callback.answer("❌ Данные не найдены.")
                return

            # Экранируем для Markdown
            escaped_text = prompt.text.replace('`', '\\`')

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Привязать этот промт",
                    callback_data=f"assign_prompt:{model.id}:{prompt.id}"
                )],
                [InlineKeyboardButton(
                    text="⬅️ Выбрать другой",
                    callback_data=f"select_model_for_prompt:{model.id}"
                )]
            ])

            await callback.message.edit_text(
                f"📄 *Полный текст промта для модели «{model.name}»:*\n\n"
                f"```\n{escaped_text}\n```\n\n"
                f"📌 Подтвердите привязку:",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка при предпросмотре промта: {e}")
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("assign_prompt:"))
async def callback_assign_prompt(callback: types.CallbackQuery):
    try:
        # Разбиваем по ":"
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Неверный формат данных.")
            return

        _, model_id_str, prompt_id_str = parts
        model_id = int(model_id_str)

        async with get_session() as session:
            model = await session.get(Model, model_id)
            if not model:
                await callback.answer("❌ Модель не найдена.")
                return

            # Определяем prompt_id
            prompt_id = None if prompt_id_str == "null" else int(prompt_id_str)

            # Привязываем
            model.prompt_id = prompt_id
            logger.info(f"Админ {callback.from_user.id} привязал промт {prompt_id} к модели {model_id}")
            
            # Подготавливаем текст для отображения
            prompt_text_display = "отсутствует"
            if prompt_id is not None:
                prompt = await session.get(Prompt, prompt_id)
                if not prompt or not prompt.is_active:
                    await callback.answer("❌ Промпт не найден или удалён.")
                    return
                prompt_text_display = prompt.text[:50] + "..." if len(prompt.text) > 50 else prompt.text

            await session.commit()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Изменить", callback_data=f"select_model_for_prompt:{model_id}")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_admin")]
            ])

            await callback.answer(f"✅ Промпт обновлён для {model.name}")
            await callback.message.edit_text(
                f"Готово.\n\nМодель: *{model.name}*\nПромт: `{prompt_text_display}`",
                reply_markup=kb,
                parse_mode="Markdown"
            )

    except ValueError as e:
        await callback.answer("❌ Ошибка: неверный ID.")
        logging.error(f"Ошибка парсинга ID: {callback.data} — {e}")
    except Exception as e:
        await callback.answer("❌ Ошибка при привязке промта.")
        logging.error(f"Неизвестная ошибка: {e}")

@router.callback_query(F.data == "back_to_admin")
async def callback_back_to_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав.", show_alert=True)
        return

    await callback.answer()  # убираем "часики"
    
    # Удаляем старое сообщение с inline-клавиатурой
    try:
        await callback.message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение: {e}")

    # Отправляем новое сообщение с Reply-клавиатурой
    await callback.message.answer("Меню управления:", reply_markup=get_admin_menu())