# Структура базы данных

## Таблицы

### `proverbs`
Хранит список пословиц.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| text | TEXT | Текст пословицы |
| added_by | STRING | ID пользователя, добавившего пословицу |
| added_at | DATETIME | Дата и время добавления |
| is_active | BOOLEAN | Активна ли запись |

### `models`
Конфигурация моделей ИИ.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| name | STRING(100) | Человекочитаемое имя модели |
| provider | STRING(50) | Провайдер (polzaai, gigachat, yandex, openai и т.д.) |
| model_name | STRING(100) | Имя модели в API |
| api_key_var | STRING(100) | Название переменной окружения с API-ключом (POLZAAI_API_KEY, GIGACHAT_CLIENT_ID, YANDEX_IAM_TOKEN и т.д.) |
| api_url | STRING(255) | URL API |
| is_active | BOOLEAN | Активна ли модель |
| created_at | DATETIME | Дата создания |
| updated_at | DATETIME | Дата последнего обновления |

### `ai_responses`
Хранит ответы ИИ на интерпретацию пословиц.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| proverb_id | INTEGER | Ссылка на `proverbs.id` |
| model_id | INTEGER | Ссылка на `ai_model_config.id` |
| prompt | TEXT | Отправленный промпт |
| response | TEXT | Ответ от ИИ |
| created_at | DATETIME | Дата создания записи |
| processed_at | DATETIME | Дата обработки запроса |
| is_cached | BOOLEAN | Является ли ответ кэшированным |
| usage_tokens | INTEGER | Количество использованных токенов |
| response_time_ms | INTEGER | Время ответа в миллисекундах |

### `messages`
Хранит историю сообщений.

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | Первичный ключ |
| message_id | INTEGER | ID сообщения в Telegram |
| chat_id | STRING | ID чата |
| username | STRING | Username отправителя |
| first_name | STRING | Имя отправителя |
| content | TEXT | Текст сообщения |
| from_bot | BOOLEAN | Отправлено ботом |
| created_at | DATETIME | Дата создания |

### `users`
Информация о пользователях бота.

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | STRING | Telegram ID пользователя |
| username | STRING | Username |
| first_name | STRING | Имя |
| is_admin | BOOLEAN | Является ли администратором |
| is_blocked | BOOLEAN | Заблокирован ли |
| blocked_by | STRING | Кто заблокировал |
| blocked_at | DATETIME | Когда заблокирован |
| created_at | DATETIME | Дата регистрации |