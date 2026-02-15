from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Model

# Начальные данные для таблицы models
INITIAL_MODELS = [
    {
        "name": "DeepSeek",
        "api_url": "https://api.polza.ai/v1/chat/completions",
        "api_key_var": "POLZA_API_KEY",
        "is_active": 1,
        "provider": "Polza",
        "model_name": "deepseek-v3.2"
    },
    {
        "name": "Anthropic",
        "api_url": "https://api.polza.ai/v1/chat/completions",
        "api_key_var": "POLZA_API_KEY",
        "is_active": 1,
        "provider": "Polza",
        "model_name": "claude-3-haiku"
    },
    {
        "name": "GigaChat",
        "api_url": "",  # будет автозаполнен
        "api_key_var": "GIGACHAT",
        "is_active": 1,
        "provider": "gigachat",
        "model_name": "GigaChat"
    },
    {
        "name": "Yandex GPT",
        "api_url": "https://d5dsop9op9ghv14u968d.hsvi2zuh.apigw.yandexcloud.net",
        "api_key_var": "YANDEX_OAUTH_TOKEN",
        "is_active": 1,
        "provider": "yandex",
        "model_name": "yandexgpt/latest"
    },
    {
        "name": "Grok",
        "api_url": "https://api.polza.ai/v1/chat/completions",
        "api_key_var": "POLZA_API_KEY",
        "is_active": 1,
        "provider": "Polza",
        "model_name": "grok-3-beta"
    }
]

async def insert_initial_models():
    """
    Вставляет начальные данные в таблицу model, если она пуста.
    """
    from src.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Проверяем, пуста ли таблица models
            result = await session.execute(select(Model))
            existing_models = result.scalars().all()
            
            if not existing_models:
                print("Заполняем таблицу models начальными данными...")
                for model_data in INITIAL_MODELS:
                    model = Model(**model_data)
                    session.add(model)
                await session.commit()
                print(f"Успешно добавлено {len(INITIAL_MODELS)} моделей.")
            else:
                print(f"Таблица models уже содержит {len(existing_models)} записей. Данные не добавлены.")