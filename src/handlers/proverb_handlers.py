from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from src.config import ADMIN_IDS
from src.states import ProverbStates
from src.keyboards import get_proverbs_keyboard
from src.database import get_session
from src.models import Proverb, Model, AIResponse
from sqlalchemy import select, delete
from src.network import Network
import logging
import asyncio

router = Router()

# Удалён дублирующий обработчик команды "Анализ ИИ"

@router.message(F.text == "Редактировать")
async def cmd_edit_proverbs(message: types.Message, state: FSMContext):
    # Отправляем список пословиц для выбора
    kb = await get_proverbs_keyboard(page=0)
    await message.answer("Выберите пословицу для редактирования:", reply_markup=kb)
    await state.set_state(ProverbStates.editing_proverb)    

@router.message(F.text == "Добавить")
async def cmd_add(message: types.Message, state: FSMContext):
    await message.answer("Введите текст новой пословицы:")
    await state.set_state(ProverbStates.waiting_for_text)

@router.message(ProverbStates.waiting_for_text)
async def process_new_proverb(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 3:
        await message.answer("Слишком коротко. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    editing_id = data.get("editing_proverb_id")

    async for session in get_session():
        if editing_id:
            # Редактирование существующей
            proverb = await session.get(Proverb, editing_id)
            if proverb and proverb.is_active:
                old_text = proverb.text
                proverb.text = text
                await session.commit()
                await message.answer(f"✅ Обновлено:\nБыло: «{old_text}»\nСтало: «{text}»")
            else:
                await message.answer("❌ Пословица не найдена.")
        else:
            # Добавление новой
            new_proverb = Proverb(text=text, added_by=str(message.from_user.id), is_active=True)
            session.add(new_proverb)
            await session.commit()
            await message.answer(f"✅ Добавлено:\n«{text}»")

    await state.clear()

@router.callback_query(F.data.startswith("page_"))
async def callback_page(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    kb = await get_proverbs_keyboard(page)
    text = f"Страница {page + 1}" if page > 0 else "Пословицы"
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("proverb_"))
async def callback_proverb(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    async for session in get_session():
        p = await session.get(Proverb, pid)
        if not p or not p.is_active:
            await callback.answer("Не найдено.")
            return
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Анализ ИИ", callback_data=f"analyze_{pid}")],
            [types.InlineKeyboardButton(text="Поделиться", callback_data=f"share_{pid}")]
        ])
        if str(callback.from_user.id) in map(str, ADMIN_IDS):
            kb.inline_keyboard.append([types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_{pid}")])
        await callback.message.edit_text(f"Выбрано:\n«{p.text}»", reply_markup=kb)
        await callback.answer()

@router.callback_query(F.data.startswith("delete_"))
async def callback_delete(callback: types.CallbackQuery):
    pid = int(callback.data.split("_")[1])
    async for session in get_session():
        p = await session.get(Proverb, pid)
        if not p or not p.is_active:
            await callback.answer("Уже удалено.")
            return
        p.is_active = False
        await session.commit()
        await callback.answer("🗑️ Удалено.")
        await callback.message.edit_text("Пословица удалена.")


@router.callback_query(F.data.startswith("analyze_"))
async def process_analyze_proverb(callback: types.CallbackQuery):
    # Пропускаем установку бота, так как он уже доступен
    pass
    # Убеждаемся, что бот установлен
    if not hasattr(callback, 'bot') or callback.bot is None:
        # Это может произойти при прямом вызове, пропускаем проверку
        pass
    await callback.answer()
    proverb_id = int(callback.data.split("_")[-1])

    # Получаем сессию
    async for session in get_session():
        # Находим пословицу
        result = await session.execute(select(Proverb).where(Proverb.id == proverb_id))
        proverb = result.scalar_one_or_none()
        if not proverb:
            await callback.message.answer("Пословица не найдена.")
            return

        # Получаем активные модели ИИ
        result = await session.execute(select(Model).where(Model.is_active == True))
        models = result.scalars().all()

        if not models:
            await callback.message.answer("Нет доступных моделей ИИ для анализа.")
            return

        # Показываем прогресс
        progress_msg = await callback.message.answer(f"Запрос отправлен в {len(models)} моделей ИИ...")

        responses = []
        for model in models:
            try:
                # Читаем промпт из файла
                try:
                    with open("C:/Work/FedorBot/prompt.txt", "r", encoding="utf-8") as f:
                        prompt_template = f.read().strip()
                    # Заменяем плейсхолдер на текст пословицы
                    prompt = prompt_template.replace("proverbs.text", proverb.text)
                except Exception as e:
                    # Резервный промпт в случае ошибки чтения файла
                    prompt = f"Дай глубокую культурную и лингвистическую интерпретацию следующей русской пословицы: {proverb.text}\nОбъясни её смысл, происхождение и употребление."

                # Отправляем запрос
                raw_response = await Network.send_prompt_to_model(
                    model_data={
                        'name': model.name,
                        'api_url': model.api_url,
                        'api_key_var': model.api_key_var,
                        'provider': model.provider,
                        'model_name': model.model_name
                    },
                    prompt=prompt
                )

                # Сохраняем ответ в БД
                ai_response = AIResponse(
                    proverb_id=proverb.id,
                    model_id=model.id,
                    prompt=prompt,
                    response=raw_response,
                    usage_tokens=len(raw_response.split()),
                    response_time_ms=1000  # заглушка
                )
                session.add(ai_response)
                await session.commit()

                # Создаём заголовок с именем модели
                header = f"<b>{model.name}</b> ({model.provider}):\n\n"
                # Объединяем заголовок с ответом
                full_response = header + raw_response
                responses.append(full_response)

            except Exception as e:
                responses.append(f"❌ Ошибка в {model.name}: {str(e)}")
                continue

        # Отправляем ответы по одному, разбивая длинные сообщения
        if responses:
            for response in responses:
                # Разбиваем длинные ответы на части
                while len(response) > 4000:
                    part = response[:4000]
                    await progress_msg.reply(part, parse_mode="HTML")
                    response = response[4000:]
                await progress_msg.reply(response, parse_mode="HTML")
        else:
            await progress_msg.reply("❌ Не удалось получить ответы от моделей ИИ.")
        
        break  # Выходим из цикла после использования сессии

