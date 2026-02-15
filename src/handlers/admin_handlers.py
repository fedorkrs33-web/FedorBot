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
