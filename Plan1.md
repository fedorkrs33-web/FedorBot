# План реализации Этапа 1: Базовая функциональность бота

## Цель

Создать рабочий асинхронный Telegram-бот, который отвечает на команды и сохраняет сообщения пользователей в базу данных.

## Подробный план реализации

### 1.1 Инициализация проекта

**Задача:** Настроить окружение для разработки Python-бота

**Действия:**
1. Создать виртуальное окружение:
   ```bash
   python -m venv .venv
   ```

2. Активировать виртуальное окружение:
   - Windows:
     ```cmd
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

3. Установить необходимые зависимости:
   ```bash
   pip install aiogram sqlalchemy aiosqlite python-dotenv pydantic
   ```

4. Создать файл requirements.txt:
   ```bash
   pip freeze > requirements.txt
   ```

5. Проверить версию Python (должна быть 3.10+):
   ```bash
   python --version
   ```

**Ожидаемый результат:** Работающее виртуальное окружение с установленными зависимостями

---

### 1.2 База данных

**Задача:** Настроить подключение к базе данных и создать схему

**Действия:**
1. Создать структуру проекта:
   ```
   mkdir src
   touch src/models.py
   touch src/database.py
   ```

2. Создать схему базы данных в src/models.py:
   ```python
   from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
   from sqlalchemy.ext.declarative import declarative_base
   from datetime import datetime
   
   Base = declarative_base()
   
   class Message(Base):
       __tablename__ = 'messages'
       
       id = Column(Integer, primary_key=True, index=True)
       message_id = Column(Integer)
       chat_id = Column(String)
       username = Column(String, nullable=True)
       first_name = Column(String, nullable=True)
       content = Column(Text)
       from_bot = Column(Boolean, default=False)
       created_at = Column(DateTime, default=datetime.utcnow)
   ```

3. Настроить подключение к базе данных в src/database.py:
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from sqlalchemy.orm import sessionmaker
   from src.models import Base
   
   # Асинхронный движок для SQLite
   engine = create_async_engine("sqlite+aiosqlite:///fedorbot.db", echo=True)
   
   # Создаем сессию
   AsyncSessionLocal = sessionmaker(
       engine, 
       class_=AsyncSession, 
       expire_on_commit=False
   )
   
   # Создаем таблицы
   async def init_db():
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
   ```

4. Создать пустую базу данных:
   ```bash
   # При первом запуске бота база данных создастся автоматически
   # или можно создать вручную:
   touch fedorbot.db
   ```

**Ожидаемый результат:** Файлы базы данных и модели созданы, подключение настроено

---

### 1.3 Переменные окружения

**Задача:** Настроить безопасное хранение конфиденциальных данных

**Действия:**
1. Создать файл .env в корне проекта:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
   ```

2. Создать пример файла .env.example:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

3. Создать модуль для загрузки переменных окружения src/config.py:
   ```python
   import os
   from dotenv import load_dotenv
   
   # Загружаем переменные окружения
   load_dotenv()
   
   # Получаем токен из переменных окружения
   BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
   
   if not BOT_TOKEN:
       raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
   ```

4. Добавить .env в .gitignore:
   ```
   # Virtual Environment
   .venv/
   
   # Environment Variables
   .env
   
   # Database
   *.db
   
   # Logs
   *.log
   
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   ```

**Ожидаемый результат:** Переменные окружения загружаются безопасно, токен не попадает в репозиторий

---

### 1.4 Основные команды

**Задача:** Реализовать обработку команд и текстовых сообщений

**Действия:**
1. Создать основной файл бота src/bot.py:
   ```python
   from aiogram import Bot, Dispatcher, types
   from aiogram.filters import Command
   from src.config import BOT_TOKEN
   from src.database import init_db, AsyncSessionLocal
   from src.models import Message
   from datetime import datetime
   import asyncio
   
   # Создаем экземпляры бота и диспетчера
   bot = Bot(token=BOT_TOKEN)
   dp = Dispatcher()
   
   # Обработка команды /start
   @dp.message(Command(commands=['start']))
   async def cmd_start(message: types.Message):
       await message.answer("Привет! Я новый Telegram-бот на Python и aiogram")
   
   # Обработка текстовых сообщений
   @dp.message()
   async def handle_message(message: types.Message):
       # Получаем информацию о пользователе
       user = message.from_user
       
       # Создаем запись для базы данных
       message_data = {
           "message_id": message.message_id,
           "chat_id": str(message.chat.id),
           "username": user.username,
           "first_name": user.first_name,
           "content": message.text,
           "from_bot": False
       }
       
       # Сохраняем сообщение в базу данных
       async with AsyncSessionLocal() as session:
           try:
               db_message = Message(**message_data)
               session.add(db_message)
               await session.commit()
               
               print(f"Сообщение от {user.first_name} сохранено в базу данных")
           except Exception as e:
               print(f"Ошибка при сохранении сообщения: {e}")
               await session.rollback()
       
       # Отвечаем на сообщение
       await message.answer(f"Получено ваше сообщение: {message.text}")
   
   # Функция для отправки сообщения
   async def send_message(chat_id: str, text: str) -> bool:
       try:
           await bot.send_message(chat_id, text)
           
           # Сохраняем исходящее сообщение
           async with AsyncSessionLocal() as session:
               try:
                   db_message = Message(
                       message_id=0,
                       chat_id=chat_id,
                       content=text,
                       from_bot=True
                   )
                   session.add(db_message)
                   await session.commit()
               except Exception as e:
                   print(f"Ошибка при сохранении исходящего сообщения: {e}")
                   await session.rollback()
           
           return True
       except Exception as e:
           print(f"Ошибка при отправке сообщения: {e}")
           return False
   
   # Основная функция запуска бота
   async def main():
       # Инициализируем базу данных
       await init_db()
       
       # Запускаем бота
       print("Бот запущен...")
       await dp.start_polling(bot)
   
   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. Создать файл __init__.py в папке src:
   ```python
   # Это пустой файл для создания пакета
   ```

**Ожидаемый результат:** Бот обрабатывает команду /start и текстовые сообщения

---

### 1.5 Работа с базой данных

**Задача:** Обеспечить надежное сохранение сообщений в базу данных с валидацией

**Действия:**
1. Создать Pydantic-модели для валидации данных src/schemas.py:
   ```python
   from pydantic import BaseModel
   from typing import Optional
   
   class MessageCreate(BaseModel):
       message_id: int
       chat_id: str
       username: Optional[str] = None
       first_name: Optional[str] = None
       content: str
       from_bot: bool = False
   
   class MessageResponse(MessageCreate):
       id: int
       created_at: str
       
       class Config:
           from_attributes = True
   ```

2. Модифицировать обработку сообщений с валидацией в src/bot.py:
   ```python
   from src.schemas import MessageCreate
   
   # ... (остальной код)
   
   @dp.message()
   async def handle_message(message: types.Message):
       user = message.from_user
       
       # Валидируем данные перед сохранением
       try:
           message_data = MessageCreate(
               message_id=message.message_id,
               chat_id=str(message.chat.id),
               username=user.username,
               first_name=user.first_name,
               content=message.text
           )
           
           # Сохраняем сообщение в базу данных
           async with AsyncSessionLocal() as session:
               try:
                   # Преобразуем Pydantic-модель в словарь
                   db_message = Message(**message_data.model_dump())
                   session.add(db_message)
                   await session.commit()
                   
                   print(f"Сообщение от {user.first_name} сохранено в базу данных")
               except Exception as e:
                   print(f"Ошибка при сохранении сообщения: {e}")
                   await session.rollback()
       except Exception as e:
           print(f"Ошибка при валидации данных: {e}")
   
   # ... (остальной код)
   ```

3. Добавить обработку ошибок в базе данных:
   ```python
   from sqlalchemy.exc import SQLAlchemyError
   
   # ... (в функции handle_message)
   
   async with AsyncSessionLocal() as session:
       try:
           db_message = Message(**message_data.model_dump())
           session.add(db_message)
           await session.commit()
           
           print(f"Сообщение от {user.first_name} сохранено в базу данных")
       except SQLAlchemyError as e:
           print(f"Ошибка SQLAlchemy при сохранении: {e}")
           await session.rollback()
       except Exception as e:
           print(f"Неожиданная ошибка при сохранении: {e}")
           await session.rollback()
   ```

**Ожидаемый результат:** Сообщения валидируются перед сохранением, ошибки обрабатываются корректно

---

## Итоговый результат этапа

После реализации всех шагов будет создан рабочий асинхронный Telegram-бот с следующей функциональностью:

1. Бот запускается и подключается к Telegram API
2. Обрабатывает команду /start и отвечает пользователю
3. Принимает текстовые сообщения от пользователей
4. Валидирует данные с помощью Pydantic
5. Сохраняет сообщения в SQLite базу данных с помощью SQLAlchemy ORM
6. Отвечает на сообщения пользователей
7. Сохраняет исходящие сообщения от бота
8. Обрабатывает ошибки при работе с базой данных

## Проверка работоспособности

1. Активировать виртуальное окружение
2. Установить зависимости: `pip install -r requirements.txt`
3. Запустить бота: `python src/bot.py`
4. В Telegram найти бота и отправить команду /start
5. Отправить текстовое сообщение
6. Проверить, что в консоли появляются сообщения о сохранении в базу данных
7. Проверить, что бот отвечает на сообщения
8. Проверить, что файл fedorbot.db создан и содержит данные

## Документация

- **requirements.txt** — список зависимостей
- **.env.example** — пример файла переменных окружения
- **Plan1.md** — данный план реализации
- **PROJECT.md** — общий план проекта