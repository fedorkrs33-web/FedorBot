# PLAN3.md

## Цель
Создание и заполнение таблицы `models` в базе данных для хранения конфигураций ИИ-моделей.

## Задачи
1. Реализовать SQL-запрос для создания таблицы `models`.
2. Создать функцию для заполнения таблицы `models` данными из существующего класса `AIModelConfig`.

## SQL-запрос для создания таблицы
```sql
CREATE_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_url TEXT NOT NULL,
    api_key_var TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    provider TEXT,
    model_name TEXT
);
"""

## Функция заполнения таблицы
Функция должна:
- Получить данные из таблицы `ai_model_config`.
- Заполнить таблицу `models` аналогичными данными.
- Обеспечить совместимость с существующей логикой приложения.
