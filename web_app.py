import os
from flask_restx import Api, Resource, fields
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from flask import Flask, request

# --- Настройки ---
DATABASE_PATH = "fedorbot.db"
if not os.path.exists(DATABASE_PATH):
    raise FileNotFoundError(f"База данных не найдена: {DATABASE_PATH}")

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Создаём Flask-приложение
app = Flask(__name__)
app.config["RESTX_MASK_SWAGGER"] = False

# Создаём API с Swagger
api = Api(
    app,
    title="FedorBot Admin API",
    version="1.0",
    description="Админ-панель для управления ботом",
    doc="/swagger/"
)

# SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

# --- Модели (для отображения в API) ---
proverb_model = api.model('Proverb', {
    'id': fields.Integer(description='ID пословицы'),
    'text': fields.String(description='Текст пословицы'),
    'is_active': fields.Boolean(description='Активна ли'),
    'added_at': fields.DateTime(description='Дата добавления')
})

prompt_model = api.model('Prompt', {
    'id': fields.Integer(description='ID промта'),
    'text': fields.String(description='Текст промта'),
    'is_active': fields.Boolean(description='Активен ли'),
    'created_by': fields.String(description='Кто создал (ID)'),
    'created_at': fields.DateTime(description='Дата создания')
})

model_model = api.model('Model', {
    'id': fields.Integer(description='ID модели'),
    'name': fields.String(description='Название модели'),
    'provider': fields.String(description='Провайдер'),
    'is_active': fields.Boolean(description='Активна ли'),
    'api_url': fields.String(description='API URL'),
    'model_name': fields.String(description='Имя модели в API')
})

# --- Пространства ---
ns_proverb = api.namespace('proverbs', description='Пословицы')
ns_prompt = api.namespace('prompts', description='Промты')
ns_model = api.namespace('models', description='Модели ИИ')


# --- Роуты API ---
@ns_proverb.route('/')
class ProverbList(Resource):
    @ns_proverb.marshal_list_with(proverb_model)
    def get(self):
        """Получить все активные пословицы"""
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT id, text, is_active, added_at FROM proverbs WHERE is_active = 1 ORDER BY added_at DESC"))
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "text": row.text,
                    "is_active": bool(row.is_active),
                    "added_at": row.added_at
                } for row in rows
            ]
        except Exception as e:
            return {"error": str(e)}, 500
        finally:
            session.close()


@ns_prompt.route('/')
class PromptList(Resource):
    @ns_prompt.marshal_list_with(prompt_model)
    def get(self):
        """Получить все активные промты"""
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT id, text, is_active, created_by, created_at FROM prompts WHERE is_active = 1 ORDER BY created_at DESC"))
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "text": row.text,
                    "is_active": bool(row.is_active),
                    "created_by": row.created_by,
                    "created_at": row.created_at
                } for row in rows
            ]
        except Exception as e:
            return {"error": str(e)}, 500
        finally:
            session.close()


@ns_model.route('/')
class ModelList(Resource):
    @ns_model.marshal_list_with(model_model)
    def get(self):
        """Получить все модели"""
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT id, name, provider, is_active, api_url, model_name FROM models"))
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "provider": row.provider,
                    "is_active": bool(row.is_active),
                    "api_url": row.api_url,
                    "model_name": row.model_name
                } for row in rows
            ]
        except Exception as e:
            return {"error": str(e)}, 500
        finally:
            session.close()


# --- Веб-интерфейс ---
@app.route("/")
def index():
    """Главная страница"""
    return """
    <html>
    <head><title>FedorBot Admin</title></head>
    <body style="font-family: sans-serif; padding: 20px; text-align: center; background: #f7f7f7;">
        <h1>🔐 FedorBot Web Admin</h1>
        <p>Интерфейс управления Telegram-ботом</p>
        <div style="margin: 30px 0;">
            <a href="/swagger" style="margin: 0 15px; font-size: 18px; text-decoration: none; color: #0066cc;">📝 API (Swagger)</a>
            <a href="/admin" style="margin: 0 15px; font-size: 18px; text-decoration: none; color: #0066cc;">📊 Админ-панель</a>
        </div>
        <hr>
        <small>База данных: <strong>fedorbot.db</strong></small>
    </body>
    </html>
    """, 200


@app.route("/admin")
def admin_page():
    # Получаем параметр вкладки
    tab = request.args.get("tab", "proverbs")
    search = request.args.get("q", "").strip()

    # --- Чтение пословиц ---
    def get_proverbs():
        with engine.connect() as conn:
            sql = "SELECT id, text, added_at FROM proverbs WHERE is_active = 1"
            if search:
                sql += " AND text LIKE :search"
            sql += " ORDER BY added_at DESC"
            result = conn.execute(text(sql), {"search": f"%{search}%"})
            return result.fetchall()

    # --- Чтение промтов ---
    def get_prompts():
        with engine.connect() as conn:
            sql = "SELECT id, text, created_at FROM prompts WHERE is_active = 1"
            if search:
                sql += " AND text LIKE :search"
            sql += " ORDER BY created_at DESC"
            result = conn.execute(text(sql), {"search": f"%{search}%"})
            return result.fetchall()

    # --- Чтение моделей ---
    def get_models():
        with engine.connect() as conn:
            sql = "SELECT id, name, provider, is_active, model_name FROM models"
            if search:
                sql += " WHERE name LIKE :search OR provider LIKE :search OR model_name LIKE :search"
            sql += " ORDER BY name"
            result = conn.execute(text(sql), {"search": f"%{search}%"})
            return result.fetchall()

    # --- Выбираем данные по вкладке ---
    if tab == "prompts":
        data = get_prompts()
        columns = ["ID", "Текст", "Дата создания"]
        rows = "".join(
            f"<tr><td>{p.id}</td><td style='text-align: left'>{(p.text[:120] + '...') if len(p.text) > 120 else p.text}</td><td>{p.created_at or '—'}</td></tr>"
            for p in data
        )
    elif tab == "models":
        data = get_models()
        columns = ["ID", "Название", "Провайдер", "Активна", "Модель в API"]
        rows = "".join(
            f"<tr><td>{m.id}</td><td>{m.name}</td><td>{m.provider}</td><td>{'✅' if m.is_active else '❌'}</td><td>{m.model_name or '—'}</td></tr>"
            for m in data
        )
    else:  # proverbs
        data = get_proverbs()
        columns = ["ID", "Текст", "Дата добавления"]
        rows = "".join(
            f"<tr><td>{p.id}</td><td style='text-align: left'>{(p.text[:120] + '...') if len(p.text) > 120 else p.text}</td><td>{p.added_at or '—'}</td></tr>"
            for p in data
        )

    if not rows:
        rows = "<tr><td colspan='5' style='color: #999'>Нет данных</td></tr>"

    # --- Генерация HTML ---
    return f"""
    <html>
    <head>
        <title>Админ-панель FedorBot</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f7f7f7; }}
            h1 {{ color: #333; }}
            .tabs {{ margin: 20px 0; display: flex; gap: 10px; }}
            .tab {{ padding: 10px 20px; background: #eee; border: 1px solid #ccc; cursor: pointer; border-radius: 5px 5px 0 0; }}
            .tab.active {{ background: white; border-bottom: none; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            th {{ background: #4CAF50; color: white; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .search {{ margin: 20px 0; }}
            .footer {{ margin-top: 40px; color: #888; font-size: 14px; }}
        </style>
    </head>
    <body>
        <h1>🔐 Админ-панель FedorBot</h1>
        <p>Управление данными бота через веб-интерфейс.</p>

        <a href="/swagger" style="color: #0066cc; font-size: 16px;">📄 API (Swagger)</a>

        <!-- Вкладки -->
        <div class="tabs">
            <a href="/admin?tab=proverbs" class="tab {'active' if tab == 'proverbs' else ''}">Пословицы</a>
            <a href="/admin?tab=prompts" class="tab {'active' if tab == 'prompts' else ''}">Промты</a>
            <a href="/admin?tab=models" class="tab {'active' if tab == 'models' else ''}">Модели ИИ</a>
        </div>

        <!-- Поиск -->
        <form method="get" class="search">
            <input type="hidden" name="tab" value="{tab}">
            <input type="text" name="q" value="{search}" placeholder="Поиск..." style="padding: 10px; width: 300px;">
            <button type="submit" style="padding: 10px 15px;">🔍 Найти</button>
            <a href="/admin?tab={tab}" style="margin-left: 10px; color: #666;">Сбросить</a>
        </form>

        <!-- Таблица -->
        <table>
            <thead>
                <tr>
                    {''.join(f'<th>{col}</th>' for col in columns)}
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <div class="footer">
            <p>База данных: <strong>fedorbot.db</strong> | Время загрузки: {datetime.now().strftime('%H:%M:%S')}</p>
            <p>💡 Можно копировать текст. Активные модели помечены ✅</p>
        </div>
    </body>
    </html>
    """, 200



if __name__ == "__main__":
    print("🌐 Веб-интерфейс запущен: http://localhost:5000")
    print("📄 API документация (Swagger): http://localhost:5000/swagger")
    print("🔐 Админ-панель: http://localhost:5000/admin")
    app.run(host="127.0.0.1", port=5000, debug=True)
