from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # Если используете Base из models.py
        from src.models import Base
        await conn.run_sync(Base.metadata.create_all)

# Удобная функция для получения сессии
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
