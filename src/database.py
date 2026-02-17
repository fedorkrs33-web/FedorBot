from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from src.config import DATABASE_URL
from src.initial_data import insert_initial_models
from src.models import Model
import logging

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        from src.models import Base
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
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

# ✅ НОВАЯ ВЕРСИЯ: возвращает сессию для async with
def get_session() -> AsyncSession:
    return AsyncSessionLocal()
