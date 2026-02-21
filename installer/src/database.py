from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, text
from src.config import DATABASE_URL
from src.initial_data import insert_initial_models
from src.models import Model
import logging
from contextlib import asynccontextmanager  # ← важно!

# Создаём асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# === ✅ ПРАВИЛЬНЫЙ АСИНХРОННЫЙ КОНТЕКСТНЫЙ МЕНЕДЖЕР ===
@asynccontextmanager
async def get_session():
    """
    Асинхронный контекстный менеджер для безопасной работы с БД.
    Гарантирует commit, rollback и закрытие сессии.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _add_prompts_type_column_if_missing(sync_conn):
    """Добавляет колонку prompts.type, если её нет (миграция для старых БД)."""
    try:
        sync_conn.execute(text("ALTER TABLE prompts ADD COLUMN type VARCHAR DEFAULT 'standard'"))
    except Exception:
        pass  # колонка уже есть или другая ошибка


# === Инициализация БД ===
async def init_db():
    async with engine.begin() as conn:
        from src.models import Base
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_prompts_type_column_if_missing)

    async with get_session() as session:
        try:
            result = await session.execute(select(func.count()).select_from(Model))
            count = result.scalar()
            if count == 0:
                await insert_initial_models()
                logging.info("✅ Начальные модели добавлены.")
            else:
                logging.info(f"ℹ️ Уже существует {count} моделей.")
        except Exception as e:
            logging.error(f"Ошибка при проверке моделей: {e}")