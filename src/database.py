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

# Получение сессии для использования в контекстном менеджере
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session