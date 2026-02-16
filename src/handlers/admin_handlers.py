from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram import F
from src.config import ADMIN_IDS
from src.database import get_session
from src.models import User, Message, Proverb, Model, AIResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging
from src.keyboards import get_admin_menu, get_proverb_menu, get_back_to_admin_menu, get_models_toggle_keyboard, get_proverbs_keyboard
from src.network import Network
import asyncio
from datetime import datetime

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Обработка кнопки "Пословица"
@router.message(F.text == "Пословица")
async def cmd_proverb_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Выберите действие с пословицами:", reply_markup=get_proverb_menu())

# Обработка кнопки "Добавить" в подменю
@router.message(F.text == "Добавить")
async def cmd_add_proverb(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Введите текст новой пословицы:")
    # Здесь должна быть реализация FSM для добавления

# Обработка кнопки "Удалить" в подменю
@router.message(F.text == "Удалить")
async def cmd_delete_proverb(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await message.answer("Выберите пословицу для удаления:", reply_markup=get_proverbs_keyboard(0))
    # Здесь должна быть реализация выбора и удаления

# Обработка кнопки "Анализ ИИ"
@router.message(F.text == "Анализ ИИ")
async def cmd_analyze_ii(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    kb = await get_proverbs_keyboard(0)
    await message.answer("Выберите пословицу для анализа:", reply_markup=kb)

# Обработка выбора пословицы для анализа
@router.callback_query(F.data.startswith("analyze_"))
async def process_analyze_proverb(callback: types.CallbackQuery):
    try:
        await callback.answer()
        proverb_id = int(callback.data.split("_")[1])

        async for session in get_session():
            proverb = await session.get(Proverb, proverb_id)
            if not proverb or not proverb.is_active:
                await callback.message.edit_text("❌ Пословица не найдена или удалена.")
                return

            # Отправляем сообщение: "Анализируем..."
            await callback.message.edit_text(f"🔍 Анализируем пословицу:\n\n«{proverb.text}»\n\nПодождите...")

            # Получаем активные модели
            result = await session.execute(
                select(Model).where(Model.is_active == True)
            )
            active_models = result.scalars().all()

            if not active_models:
                await callback.message.answer("⚠️ Нет активных моделей ИИ. Включите хотя бы одну в меню «Модели».")
                return

            # Читаем промт
            try:
                with open("C:/Work/FedorBot/prompt.txt", "r", encoding="utf-8") as f:
                    base_prompt = f.read().strip()
            except Exception as e:
                logging.error(f"Ошибка чтения промта: {e}")
                base_prompt = "Объясни смысл этой пословицы простыми словами."

            # Формируем финальный промт
            final_prompt = f"{base_prompt}\n\nПословица: {proverb.text}"

            # Отправляем запрос в каждую модель
            responses = []
            network = Network()  # Убедитесь, что Network инициализирована правильно

            for model in active_models:
                try:
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
                    responses.append({
                        "model": model.name,
                        "response": response_text
                    })
                    # Сохраняем ответ в БД
                    ai_response = AIResponse(
                        proverb_id=proverb.id,
                        model_id=model.id,
                        prompt=final_prompt,  # важно: у вас есть поле prompt → заполняем его
                        response=response_text
                    )
                    session.add(ai_response)
                except asyncio.TimeoutError:
                    responses.append({
                        "model": model.name,
                        "response": "❌ Время ожидания ответа истекло."
                    })
                except Exception as e:
                    logging.error(f"Ошибка при генерации от {model.name}: {e}")
                    responses.append({
                        "model": model.name,
                        "response": f"❌ Ошибка модели: {str(e)}"
                    })

            await session.commit()

            # Формируем итоговое сообщение
            result_text = f"✅ Результаты анализа пословицы:\n\n«{proverb.text}»\n\n"
            for r in responses:
                result_text += f"\n🤖 *{r['model']}*\n{r['response']}\n"

            # Кнопка "Сравнить" (если моделей > 1)
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

        async for session in get_session():
            proverb = await session.get(Proverb, proverb_id)
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
                # Формируем промт для сравнения
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
@router.message(F.text == "Модели")
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
    
    async for session in get_session():
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

# Обработка кнопки "Промт"
@router.message(F.text == "Промт")
async def cmd_prompt_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    
    try:
        with open("C:/Work/FedorBot/prompt.txt", "r", encoding="utf-8") as f:
            prompt_text = f.read()
    except Exception as e:
        prompt_text = "Ошибка чтения файла промта."
    
    # Создаём клавиатуру с кнопкой "Сохранить"
    save_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Сохранить")], [KeyboardButton(text="Назад")]],
        resize_keyboard=True
    )
    
    await message.answer(f"Текущий промт:\n\n{prompt_text}", reply_markup=save_kb)
    # Здесь должна быть реализация редактирования и сохранения

# Обработка кнопки "Назад" для возврата в меню управления
@router.message(F.text == "Назад")
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
