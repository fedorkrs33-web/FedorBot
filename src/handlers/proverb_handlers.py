from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from src.config import ADMIN_IDS
from src.states import ProverbStates
from src.keyboards import get_proverbs_keyboard
from src.database import get_session
from src.models import Proverb
from sqlalchemy import select, delete
import logging

router = Router()

@router.message(F.text == "Анализ ИИ")
@router.message(Command(commands=['analyze']))
async def cmd_analyze(message: types.Message):
    kb = await get_proverbs_keyboard(0)
    text = "Выберите пословицу:" if kb.inline_keyboard else "Нет пословиц."
    await message.answer(text, reply_markup=kb)

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
