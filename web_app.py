import os
import html
import io
from flask import Flask, request, redirect, session, render_template_string, send_file
from dotenv import load_dotenv
from flask_restx import Api, Resource, fields
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from datetime import datetime
from version import __version__

load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_PASSWORD:
    raise RuntimeError("❌ Не задан ADMIN_PASSWORD в .env")

# --- Настройки БД (локально: SQLite; на Vercel/продакшене: задайте DATABASE_URL в env) ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # Преобразуем aiosqlite -> sqlite для синхронного доступа
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
else:
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, echo=False)

# --- Flask & API ---
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_for_dev")
app.config["RESTX_MASK_SWAGGER"] = False

api = Api(
    app,
    title="FedorBot Admin API",
    version=__version__,
    description="Админ-панель для управления ботом",
    doc="/swagger/"
)

# --- Модели API ---
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


# --- Авторизация ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return """
        <html>
        <head><title>🔐 Вход</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h2>Войдите в админ-панель</h2>
            <form method="post" action="/login">
                <input type="text" name="username" placeholder="Логин (из Telegram)" required
                       style="padding: 10px; margin: 5px; width: 200px; font-size: 16px;"><br>
                <input type="password" name="password" placeholder="Пароль" required
                       style="padding: 10px; margin: 5px; width: 200px; font-size: 16px;"><br>
                <button type="submit" style="padding: 10px 20px; background: #0066cc; color: white; border: none; border-radius: 5px; margin-top: 10px;">
                    Войти
                </button>
            </form>
        </body>
        </html>
        """

    # POST: обработка формы
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return "<script>alert('Введите логин и пароль'); window.history.back();</script>"

    # Проверяем пароль сразу
    if password != ADMIN_PASSWORD:
        return "<script>alert('❌ Неверный пароль'); window.history.back();</script>"

    # Проверяем, есть ли пользователь в БД и он админ
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sql_text("SELECT user_id, username, first_name FROM users WHERE first_name = :name AND is_admin = 1"),
                {"name": username},
            )
            user = result.fetchone()

        if not user:
            return """
            <script>
                alert('❌ Пользователь не найден или не является администратором.\\nПроверьте логин и права.');
                window.location.href='/login';
            </script>
            """

        # Успешный вход
        session['logged_in'] = True
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['first_name'] = user[2] or user[1]

        return redirect("/admin")

    except Exception as e:
        print(f"🔴 Ошибка при входе: {e}")  # ← будет в консоли
        return f"""
        <script>
            alert('Ошибка сервера: {str(e)}');
            window.location.href='/login';
        </script>
        """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# --- API Роуты ---

@ns_proverb.route('/')
class ProverbList(Resource):
    @ns_proverb.marshal_list_with(proverb_model)
    def get(self):
        """Получить все активные пословицы"""
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text("""
                    SELECT id, text, is_active, added_at 
                    FROM proverbs 
                    WHERE is_active = 1 
                    ORDER BY added_at DESC
                """))
                return [
                    {"id": r.id, "text": r.text, "is_active": bool(r.is_active), "added_at": r.added_at}
                    for r in result.fetchall()
                ]
        except Exception as e:
            return {"error": str(e)}, 500


@ns_prompt.route('/')
class PromptList(Resource):
    @ns_prompt.marshal_list_with(prompt_model)
    def get(self):
        """Получить все активные промты"""
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text("""
                    SELECT id, text, is_active, created_by, created_at 
                    FROM prompts 
                    WHERE is_active = 1 
                    ORDER BY created_at DESC
                """))
                return [
                    {"id": r.id, "text": r.text, "is_active": bool(r.is_active), "created_by": r.created_by, "created_at": r.created_at}
                    for r in result.fetchall()
                ]
        except Exception as e:
            return {"error": str(e)}, 500

@ns_model.route('/')
class ModelList(Resource):
    @ns_model.marshal_list_with(model_model)
    def get(self):
        """Получить все модели"""
        try:
            with engine.connect() as conn:
                result = conn.execute(sql_text("""
                    SELECT id, name, provider, is_active, api_url, model_name 
                    FROM models
                """))
                return [
                    {"id": r.id, "name": r.name, "provider": r.provider, "is_active": bool(r.is_active), "api_url": r.api_url, "model_name": r.model_name}
                    for r in result.fetchall()
                ]
        except Exception as e:
            return {"error": str(e)}, 500


# --- Веб-интерфейс ---
@app.route("/")
@login_required
def index():
    return f"""
    <html>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>🔐 FedorBot Web Admin v{__version__}</h1>
        <p>Интерфейс управления Telegram-ботом</p>
        <a href="/admin" style="font-size: 18px; margin: 10px; padding: 15px; background: #0066cc; color: white; text-decoration: none; border-radius: 8px;">📊 Перейти в админку</a><br>
        <a href="/swagger" style="color: #555;">📄 API (Swagger)</a>
    </body>
    </html>
    """


@app.route("/admin")
@login_required
def admin_page():
    tab = request.args.get("tab", "proverbs")
    search = request.args.get("q", "").strip()

    # --- Функции чтения ---
    def get_proverbs():
        with engine.connect() as conn:
            sql = "SELECT id, text, added_at FROM proverbs WHERE is_active = 1"
            if search:
                sql += " AND text LIKE :search"
            sql += " ORDER BY added_at DESC"
            return conn.execute(sql_text(sql), {"search": f"%{search}%"}).fetchall()

    def get_prompts():
        with engine.connect() as conn:
            sql = "SELECT id, text, created_at FROM prompts WHERE is_active = 1"
            if search:
                sql += " AND text LIKE :search"
            sql += " ORDER BY created_at DESC"
            return conn.execute(sql_text(sql), {"search": f"%{search}%"}).fetchall()

    def get_models():
        with engine.connect() as conn:
            sql = "SELECT id, name, provider, is_active, model_name FROM models"
            if search:
                sql += " WHERE name LIKE :search OR provider LIKE :search OR model_name LIKE :search"
            sql += " ORDER BY name"
            return conn.execute(sql_text(sql), {"search": f"%{search}%"}).fetchall()

    def get_proverbs_for_analysis():
        with engine.connect() as conn:
            return conn.execute(sql_text("""
                SELECT id, text FROM proverbs WHERE is_active = 1 ORDER BY added_at DESC LIMIT 20
            """)).fetchall()

    def get_proverbs_with_ai_counts():
        with engine.connect() as conn:
            return conn.execute(sql_text("""
                SELECT p.id, p.text, p.added_at,
                       (SELECT COUNT(*) FROM ai_responses ar WHERE ar.proverb_id = p.id) as ai_count
                FROM proverbs p
                WHERE p.is_active = 1
                ORDER BY p.added_at DESC
            """)).fetchall()

    # --- Генерация контента ---
    columns = []
    rows = ""

    if tab == "proverbs":
        data = get_proverbs()
        columns = ["ID", "Текст", "Дата добавления", "Действие"]
        rows = "".join(
            f"""
            <tr>
                <td><a href='/proverb/{p.id}' style='color: #0066cc;'>{p.id}</a></td>
                <td style='text-align: left;' title="{p.text}">{p.text[:120] + '...' if len(p.text) > 120 else p.text}</td>
                <td>{p.added_at or '—'}</td>
                <td>
                    <button onclick="showEditProverbModal({p.id}, `{p.text.replace('`', '\\`')}`)"
                            style="padding:5px 10px; background:#2196F3; color:white; border:none; border-radius:3px; cursor:pointer; margin-right:5px;">
                        Редактировать
                    </button>
                    <form method="post" action="/delete_proverb/{p.id}" style="display:inline;" onsubmit="return confirm('Удалить эту пословицу?');">
                        <button type="submit" style="padding:5px 10px; background:#f44336; color:white; border:none; border-radius:3px; cursor:pointer;">
                            Удалить
                        </button>
                    </form>
                </td>
            </tr>
            """
            for p in data
        )

    elif tab == "prompts":
        data = get_prompts()
        columns = ["ID", "Текст", "Дата добавления", "Действие"]
        rows = "".join(
            f"""
            <tr>
                <td>{p.id}</td>
                <td style='text-align: left; cursor: pointer; color: #0066cc;' 
                    onclick="showPromptModal({p.id}, `{p.text.replace('`', '\\`')}`)"
                    title="Кликните, чтобы посмотреть полностью">
                    {p.text[:120] + '...' if len(p.text) > 120 else p.text}
                </td>
                <td>{p.created_at or '—'}</td>
                <td>
                    <button onclick="showEditPromptModal({p.id}, `{p.text.replace('`', '\\`')}`)"
                            style="padding:5px 10px; background:#2196F3; color:white; border:none; border-radius:3px; cursor:pointer; margin-right:5px;">
                        Редактировать
                    </button>
                    <form method="post" action="/delete_prompt/{p.id}" style="display:inline;" onsubmit="return confirm('Удалить этот промт?');">
                        <button type="submit" style="padding:5px 10px; background:#f44336; color:white; border:none; border-radius:3px; cursor:pointer;">
                            Удалить
                        </button>
                    </form>
                </td>
            </tr>
            """
            for p in data
        )


    elif tab == "ai_responses":
        data = get_proverbs_with_ai_counts()
        columns = ["ID", "Пословица", "Ответов ИИ", "Действие"]
        rows = "".join(
            f"""
            <tr>
                <td>{p.id}</td>
                <td style='text-align: left;' title="{html.escape(p.text)}">{html.escape(p.text[:80])}{'…' if len(p.text) > 80 else ''}</td>
                <td>{p.ai_count}</td>
                <td><a href='/proverb/{p.id}' class="btn" style="padding: 6px 12px;">Просмотр ответов</a></td>
            </tr>
            """
            for p in data
        )

    elif tab == "models":
        data = get_models()
        columns = ["ID", "Название", "Провайдер", "Активна", "Модель в API"]
        rows = "".join(
            f"""
            <tr>
                <td>{m.id}</td>
                <td>{m.name}</td>
                <td>{m.provider}</td>
                <td>{'✅' if m.is_active else '❌'}</td>
                <td>{m.model_name or '—'}</td>
            </tr>
            """
            for m in data
        )

    # --- Вкладка "Пользователи" ---
    elif tab == "users":
        columns = ["ID", "Юзернейм", "Имя", "Админ", "Статус", "Дата регистрации", "Действия"]
        
        # Поиск по username или first_name
        search_filter = f"%{search}%"
        with engine.connect() as conn:
            query = """
                SELECT user_id, username, first_name, is_admin, is_blocked, blocked_at, created_at 
                FROM users 
                WHERE (:search IS NULL OR username LIKE :search OR first_name LIKE :search)
                ORDER BY is_admin DESC, created_at DESC
            """
            result = conn.execute(sql_text(query), {"search": search_filter if search else None})
            users = result.fetchall()

        rows = "".join(
            f"""
            <tr>
                <td>{u.user_id}</td>
                <td>@{u.username or '—'}</td>
                <td>{u.first_name or '—'}</td>
                <td>{'✅' if u.is_admin else '❌'}</td>
                <td>{'🔴 Заблокирован' if u.is_blocked else '🟢 Активен'}</td>
                <td>{datetime.fromisoformat(u.created_at).strftime('%Y-%m-%d %H:%M') if u.created_at else '—'}</td>
                <td>
                    {'<form method="post" action="/unblock_user" style="display:inline;">'
                    f'<input type="hidden" name="user_id" value="{u.user_id}">'
                    f'<button type="submit" style="padding:5px 10px; background:#8bc34a; color:white; border:none; border-radius:3px; margin-right:5px;">Разблокировать</button>'
                    '</form>' if u.is_blocked else
                    '<form method="post" action="/block_user" style="display:inline;">'
                    f'<input type="hidden" name="user_id" value="{u.user_id}">'
                    f'<button type="submit" style="padding:5px 10px; background:#f44336; color:white; border:none; border-radius:3px; margin-right:5px;">Заблокировать</button>'
                    '</form>'}
                    {'<form method="post" action="/make_admin" style="display:inline;">'
                    f'<input type="hidden" name="user_id" value="{u.user_id}">'
                    f'<button type="submit" style="padding:5px 10px; background:#ff9800; color:white; border:none; border-radius:3px;">{'Снять админа' if u.is_admin else 'Назначить админом'}</button>'
                    '</form>'}
                </td>
            </tr>
            """
            for u in users
        )

    elif tab == "control":
        columns = []
        rows = """
        <div style="text-align: center; margin: 30px 0;">
            <h2>🛠 Управление ботом</h2>
        </div>

        <!-- Добавить пословицу -->
        <h3>➕ Добавить новую пословицу</h3>
        <form method="post" action="/add_proverb" style="margin: 20px 0; padding: 15px; background: #f0f8ff; border-radius: 8px; max-width: 600px; margin: 20px auto;">
            <textarea name="text" placeholder="Введите пословицу..." 
                    style="width: 100%; height: 60px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;"
                    required></textarea><br>
            <button type="submit" style="margin-top: 10px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; font-size: 16px;">
                📥 Добавить
            </button>
        </form>

        <!-- Добавить промт -->
        <h3>💬 Добавить новый промт</h3>
        <form method="post" action="/add_prompt" style="margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 8px; max-width: 700px; margin: 20px auto;">
            <textarea name="text" placeholder="Введите текст промта..." 
                    style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;"
                    required></textarea><br>
            <small style="color: #666;">💡 Пример: "Объясни пословицу как для ребёнка 8 лет"</small><br>
            <button type="submit" style="margin-top: 10px; padding: 10px 20px; background: #9c27b0; color: white; border: none; border-radius: 5px; font-size: 16px;">
                ✨ Добавить промт
            </button>
        </form>

        <!-- Управление моделями -->
        <h3>🤖 Модели ИИ</h3>
        <p>Вкл/Выкл активных моделей</p>
        <table border="0" cellspacing="5" style="margin: 15px auto; background: white; width: 80%; max-width: 600px;">
            <tr style="background: #eee;"><th>ID</th><th>Название</th><th>Статус</th><th>Действие</th></tr>
        """
        
        # --- Список моделей ---
        with engine.connect() as conn:
            models = conn.execute(sql_text("SELECT id, name, is_active FROM models ORDER BY name")).fetchall()
            for m in models:
                action = f"""
                <a href="/toggle_model/{m.id}" style="padding: 5px 10px; background: {'#f44336' if m.is_active else '#8bc34a'};
                    color: white; text-decoration: none; border-radius: 3px;">
                    {'Выключить' if m.is_active else 'Включить'}
                </a>
                """
                rows += f"<tr><td>{m.id}</td><td>{m.name}</td><td>{'✅ Активна' if m.is_active else '❌ Выключена'}</td><td>{action}</td></tr>"
        rows += "</table>"

        # --- Ссылки на списки ---
        rows += """
        <h3>📚 Быстрый доступ к спискам</h3>
        <p>
            <a href="/admin?tab=proverbs" class="btn">📜 Все пословицы</a>
            <a href="/admin?tab=prompts" class="btn">💬 Все промты</a>
            <a href="/admin?tab=models" class="btn">🤖 Модели</a>
            <a href="/admin?tab=ai_responses" class="btn">💬 Анализы ИИ</a>
        </p>
        """

    elif tab == "analyze":
        proverbs = get_proverbs_for_analysis()
        rows = "<h3>🔍 Выберите пословицу для анализа ИИ</h3>"
        for p in proverbs:
            # Экранируем кавычки и обратные кавычки в тексте
            safe_text = p.text.replace('"', '&quot;').replace('`', '\\`')
            rows += f"""
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; cursor: pointer;" 
                onclick="showPromptModal({p.id}, `{safe_text}`)" 
                title="Просмотреть полный текст">
                <strong>{p.text[:120] + '...' if len(p.text) > 120 else p.text}</strong>
                <button style="margin-left: 10px; padding: 5px 10px; background: #ff9800; color: white; border: none; border-radius: 3px; cursor: pointer;">
                    Запустить анализ
                </button>
                <small>(временно недоступно)</small>
            </div>
            """
        columns = []

    else:
        data = get_proverbs()
        columns = ["ID", "Текст", "Дата добавления"]
        rows = "".join(
            f"""
            <tr>
                <td><a href='/proverb/{p.id}' style='color: #0066cc;'>{p.id}</a></td>
                <td style='text-align: left;' title="{p.text}">{p.text[:120] + '...' if len(p.text) > 120 else p.text}</td>
                <td>{p.added_at or '—'}</td>
            </tr>
            """
            for p in data
        )

    if not rows:
        rows = "<tr><td colspan='5' style='color: #999;'>Нет данных</td></tr>"

    # --- Вкладки ---
    tabs_html = """
    <div class="tabs">
        <a href="/admin?tab=proverbs" class="tab">Пословицы</a>
        <a href="/admin?tab=prompts" class="tab">Промты</a>
        <a href="/admin?tab=models" class="tab">Модели ИИ</a>
        <a href="/admin?tab=ai_responses" class="tab">💬 Анализы ИИ</a>
        <a href="/admin?tab=users" class="tab">Пользователи</a>
        <a href="/admin?tab=control" class="tab">Управление</a>
    </div>
    """

    return f"""
    <html>
    <head>
        <title>Админ-панель FedorBot v{__version__}</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f7f7f7; }}
            h1, h2, h3 {{ color: #333; }}
            .tabs {{ margin: 20px 0; display: flex; gap: 10px; }}
            .tab {{ padding: 10px 20px; background: #eee; border: 1px solid #ccc; text-decoration: none; border-radius: 5px 5px 0 0; }}
            .tab:hover {{ background: #ddd; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            th {{ background: #4CAF50; color: white; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .search {{ margin: 20px 0; }}
            .btn {{ margin: 0 5px; padding: 8px 12px; border: none; border-radius: 4px; text-decoration: none; color: white; cursor: pointer; }}
            .footer {{ margin-top: 40px; color: #888; font-size: 14px; }}
            .btn {{
                margin: 0 10px;
                padding: 10px 15px;
                background: #0066cc;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                display: inline-block;
                font-size: 14px;
            }}
        </style>
    </head>

    <body>
        <p style="text-align: right;">
            <small>Привет, <strong>{session.get('first_name', 'Админ')}</strong> | 
            <a href="/logout" style="color: #f44336;">Выход</a></small>
        </p>
        <h1>🔐 Админ-панель FedorBot v{__version__}</h1>
        <p>Управление данными бота через веб-интерфейс.</p>
        <a href="/swagger" style="color: #0066cc; font-size: 16px;">📄 API (Swagger)</a>

        {tabs_html}

        <form method="get" class="search">
            <input type="hidden" name="tab" value="{tab}">
            <input type="text" name="q" value="{search}" placeholder="Поиск..." style="padding: 10px; width: 300px;">
            <button type="submit" style="padding: 10px 15px;">🔍 Найти</button>
            <a href="/admin?tab={tab}" style="margin-left: 10px; color: #666;">Сбросить</a>
        </form>

        {('<table><thead><tr>' + ''.join(f'<th>{col}</th>' for col in columns) + '</tr></thead><tbody>' + rows + '</tbody></table>') if columns else rows}

        <div class="footer">
            <p>Версия: <strong>{__version__}</strong> | База данных: <strong>fedorbot.db</strong> | Время загрузки: {datetime.now().strftime('%H:%M:%S')}</p>
            <p>💡 Можно копировать текст. Активные модели помечены ✅</p>
        </div>

    <!-- Модальное окно для просмотра промта -->
    <div id="promptModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);"
        onclick="this.style.display='none';">
        <div style="background: white; margin: 10% auto; padding: 20px; width: 80%; max-width: 800px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative;"
            onclick="event.stopPropagation();">
            <h3>📋 Полный текст промта</h3>
            <pre id="promptText" style="white-space: pre-wrap; word-wrap: break-word; max-height: 50vh; overflow-y: auto; background: #f4f4f4; padding: 15px; border-radius: 5px;"></pre>
            <button onclick="document.getElementById('promptModal').style.display='none';"
                    style="margin-top: 10px; padding: 8px 16px; background: #555; color: white; border: none; border-radius: 5px; cursor: pointer;">
                Закрыть
            </button>
        </div>
    </div>

    <script>
    function showPromptModal(id, text) {{
        document.getElementById("promptText").textContent = text;
        document.getElementById("promptModal").style.display = "block";
    }}

    function showEditProverbModal(id, text) {{
        document.getElementById("editProverbId").value = id;
        document.getElementById("editProverbText").value = text;
        document.getElementById("editProverbModal").style.display = "block";
    }}

    function showEditPromptModal(id, text) {{
        document.getElementById("editPromptId").value = id;
        document.getElementById("editPromptText").value = text;
        document.getElementById("editPromptModal").style.display = "block";
    }}
    </script>

    <!-- Модальное окно для редактирования пословицы -->
    <div id="editProverbModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);"
        onclick="this.style.display='none';">
        <div style="background: white; margin: 10% auto; padding: 20px; width: 80%; max-width: 700px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative;"
            onclick="event.stopPropagation();">
            <h3>✏️ Редактировать пословицу</h3>
            <form id="editProverbForm" method="post" action="/edit_proverb">
                <input type="hidden" id="editProverbId" name="id" value="">
                <textarea id="editProverbText" name="text" 
                        style="width: 100%; height: 80px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;"
                        required></textarea><br>
                <button type="submit" style="margin-top: 10px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px;">
                    Сохранить
                </button>
                <button type="button" onclick="document.getElementById('editProverbModal').style.display='none';"
                        style="margin-top: 10px; margin-left: 10px; padding: 10px 20px; background: #999; color: white; border: none; border-radius: 5px;">
                    Отмена
                </button>
            </form>
        </div>
    </div>

    <!-- Модальное окно для редактирования промта -->
    <div id="editPromptModal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);"
        onclick="this.style.display='none';">
        <div style="background: white; margin: 10% auto; padding: 20px; width: 80%; max-width: 700px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative;"
            onclick="event.stopPropagation();">
            <h3>✏️ Редактировать промт</h3>
            <form id="editPromptForm" method="post" action="/edit_prompt">
                <input type="hidden" id="editPromptId" name="id" value="">
                <textarea id="editPromptText" name="text" 
                        style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 16px;"
                        required></textarea><br>
                <button type="submit" style="margin-top: 10px; padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px;">
                    Сохранить
                </button>
                <button type="button" onclick="document.getElementById('editPromptModal').style.display='none';"
                        style="margin-top: 10px; margin-left: 10px; padding: 10px 20px; background: #999; color: white; border: none; border-radius: 5px;">
                    Отмена
                </button>
            </form>
        </div>
    </div>    

    </body>
    </html>
    """


# --- Детали пословицы ---
@app.route("/proverb/<int:proverb_id>")
@login_required
def view_proverb(proverb_id):
    with engine.connect() as conn:
        proverb = conn.execute(
            sql_text("SELECT id, text, added_at FROM proverbs WHERE id = :id AND is_active = 1"),
            {"id": proverb_id}
        ).fetchone()

        if not proverb:
            return "<h1>❌ Пословица не найдена</h1><p><a href='/admin'>← Назад</a></p>", 404

        responses = conn.execute(
            sql_text("""
                SELECT ar.id as response_id, ar.response, ar.prompt, m.name as model_name, ar.created_at
                FROM ai_responses ar
                JOIN models m ON ar.model_id = m.id
                WHERE ar.proverb_id = :id
                ORDER BY m.name
            """),
            {"id": proverb_id}
        ).fetchall()

    responses_html = ""
    if responses:
        for r in responses:
            prompt_short = (r.prompt[:150] + "...") if len(r.prompt) > 150 else r.prompt
            response_text = r.response.replace("\n", "<br>")
            response_escaped = html.escape(r.response)
            safe_model = html.escape(r.model_name)
            responses_html += f"""
            <div class="ai-response-block" style="margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;">
                <h3>🤖 {safe_model}</h3>
                <p><strong>Промт:</strong> {html.escape(prompt_short)}</p>
                <p><strong>Ответ:</strong></p>
                <p style="background: white; padding: 10px; border-radius: 5px; font-style: italic;">{response_text}</p>
                <textarea id="response-{r.response_id}" style="display:none;">{response_escaped}</textarea>
                <p style="margin-top: 10px;">
                    <button type="button" class="btn-copy" data-response-id="{r.response_id}" style="padding: 6px 12px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 8px;">📋 Копировать</button>
                    <a href="/download_ai_response/{r.response_id}" class="btn-download" style="padding: 6px 12px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">💾 Скачать файл</a>
                </p>
                <small style="color: #666;">Дата: {r.created_at}</small>
            </div>
            """
    else:
        responses_html = "<p><em>❌ Нет ответов ИИ. Проанализируйте в боте.</em></p>"

    return f"""
    <html>
    <head><title>Пословица #{proverb_id}</title>
        <style>
            .btn-copy:hover, .btn-download:hover {{ opacity: 0.9; }}
        </style>
    </head>
    <body style="font-family: sans-serif; padding: 20px;">
        <h1>📜 Пословица #{proverb_id}</h1>
        <p style="font-size: 18px; font-style: italic; color: #333;">«{html.escape(proverb.text)}»</p>
        <p><strong>Добавлена:</strong> {proverb.added_at or '—'}</p>
        <hr>
        <h2>💬 Ответы моделей ИИ</h2>
        {responses_html}
        <p><a href="/admin?tab=ai_responses" style="color: #0066cc;">← Назад к списку анализов</a> &nbsp; <a href="/admin?tab=proverbs" style="color: #0066cc;">Пословицы</a></p>
        <script>
            document.querySelectorAll('.btn-copy').forEach(function(btn) {{
                btn.addEventListener('click', function() {{
                    var id = this.getAttribute('data-response-id');
                    var el = document.getElementById('response-' + id);
                    if (el) {{
                        el.select();
                        el.setSelectionRange(0, 99999);
                        try {{
                            navigator.clipboard.writeText(el.value);
                            this.textContent = '✓ Скопировано';
                            var t = this;
                            setTimeout(function() {{ t.textContent = '📋 Копировать'; }}, 2000);
                        }} catch (e) {{
                            alert('Скопируйте текст вручную из поля выше.');
                        }}
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """

@app.route("/download_ai_response/<int:response_id>")
@login_required
def download_ai_response(response_id):
    """Скачать ответ ИИ в виде текстового файла."""
    with engine.connect() as conn:
        row = conn.execute(
            sql_text("""
                SELECT ar.response, ar.prompt, m.name as model_name, p.text as proverb_text
                FROM ai_responses ar
                JOIN models m ON ar.model_id = m.id
                JOIN proverbs p ON ar.proverb_id = p.id
                WHERE ar.id = :id
            """),
            {"id": response_id}
        ).fetchone()
    if not row:
        return "<h1>❌ Ответ не найден</h1>", 404
    content = f"Пословица: {row.proverb_text}\n\nМодель: {row.model_name}\n\nПромт:\n{row.prompt}\n\nОтвет:\n{row.response}"
    filename = f"ai_response_{response_id}_{row.model_name.replace(' ', '_')}.txt"
    buf = io.BytesIO(content.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/edit_proverb", methods=["POST"])
@login_required
def edit_proverb():
    try:
        proverb_id = request.form.get("id")
        new_text = request.form.get("text", "").strip()

        if not proverb_id or not new_text:
            return "<script>alert('❌ ID или текст не указаны'); window.history.back();</script>"

        with engine.connect() as conn:
            conn.execute(
                sql_text("UPDATE proverbs SET text = :text WHERE id = :id"),
                {"text": new_text, "id": proverb_id}
            )
            conn.commit()
        return "<script>alert('✅ Пословица обновлена'); window.location.href='/admin?tab=proverbs';</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"

@app.route("/edit_prompt", methods=["POST"])
@login_required
def edit_prompt():
    try:
        prompt_id = request.form.get("id")
        new_text = request.form.get("text", "").strip()

        if not prompt_id or not new_text:
            return "<script>alert('❌ ID или текст не указаны'); window.history.back();</script>"

        with engine.connect() as conn:
            conn.execute(
                sql_text("UPDATE prompts SET text = :text WHERE id = :id"),
                {"text": new_text, "id": prompt_id}
            )
            conn.commit()
        return "<script>alert('✅ Промт обновлён'); window.location.href='/admin?tab=prompts';</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"

# --- Переключение модели ---
@app.route("/toggle_model/<int:model_id>")
@login_required
def toggle_model(model_id):
    try:
        with engine.connect() as conn:
            current = conn.execute(
                sql_text("SELECT is_active FROM models WHERE id = :id"),
                {"id": model_id}
            ).fetchone()
            if not current:
                return "❌ Модель не найдена", 404

            new_status = 0 if current.is_active else 1
            conn.execute(
               sql_text("UPDATE models SET is_active = :status WHERE id = :id"),
                {"status": new_status, "id": model_id}
            )
            conn.commit()

        return f"""
        <script>alert('Статус обновлён!'); window.location.href='/admin?tab=control';</script>
        """
    except Exception as e:
        return f"❌ Ошибка: {e}", 500

@app.route("/add_proverb", methods=["POST"])
@login_required
def add_proverb():
    proverb_text = request.form.get("text", "").strip()
    if not proverb_text:
        return "<script>alert('❌ Текст пословицы не может быть пустым!'); window.history.back();</script>"

    try:
        print(f"🔧 Добавляем пословицу: {proverb_text[:50]}...")  # ← лог в консоль
        with engine.connect() as conn:
            conn.execute(
                sql_text("""
                    INSERT INTO proverbs (text, is_active, added_at)
                    VALUES (:text, 1, datetime('now'))
                """),
                {"text": proverb_text}
            )

            conn.commit()  # ← ВАЖНО: для SQLAlchemy нужно явно коммитить!
            print("✅ Пословица добавлена в БД")
        return "<script>alert('✅ Пословица добавлена!'); window.location.href='/admin?tab=proverbs';</script>"
    except Exception as e:
        print(f"🔴 Ошибка при добавлении пословицы: {e}")  # ← видно в терминале
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"



@app.route("/add_prompt", methods=["POST"])
@login_required
def add_prompt():
    prompt_text = request.form.get("text", "").strip()
    if not prompt_text:
        return "<script>alert('❌ Текст промта не может быть пустым!'); window.history.back();</script>"

    try:
        print(f"🔧 Добавляем промт: {prompt_text[:50]}...")  # ← лог
        with engine.connect() as conn:
            conn.execute(
                sql_text("""
                    INSERT INTO prompts (text, is_active, created_by, created_at)
                    VALUES (:text, 1, NULL, datetime('now'))
                """),
                {"text": prompt_text}
            )
            conn.commit()  # ← обязательно!
            print("✅ Промт добавлен в БД")
        return "<script>alert('✅ Промт добавлен!'); window.location.href='/admin?tab=prompts';</script>"
    except Exception as e:
        print(f"🔴 Ошибка при добавлении промта: {e}")
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"

@app.route("/delete_proverb/<int:proverb_id>", methods=["POST"])
@login_required
def delete_proverb(proverb_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sql_text("SELECT text FROM proverbs WHERE id = :id"),
                {"id": proverb_id}
            ).fetchone()

            if not result:
                return "<script>alert('❌ Пословица не найдена'); window.history.back();</script>"

            conn.execute(
                sql_text("DELETE FROM proverbs WHERE id = :id"),
                {"id": proverb_id}
            )
            conn.commit()
        return "<script>alert('✅ Пословица удалена'); window.location.href='/admin?tab=proverbs';</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"


@app.route("/delete_prompt/<int:prompt_id>", methods=["POST"])
@login_required
def delete_prompt(prompt_id):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                sql_text("SELECT text FROM prompts WHERE id = :id"),
                {"id": prompt_id}
            ).fetchone()

            if not result:
                return "<script>alert('❌ Промт не найден'); window.history.back();</script>"

            conn.execute(
              sql_text("DELETE FROM prompts WHERE id = :id"),
                {"id": prompt_id}
            )
            conn.commit()
        return "<script>alert('✅ Промт удалён'); window.location.href='/admin?tab=prompts';</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"

@app.route("/block_user", methods=["POST"])
@login_required
def block_user():
    try:
        user_id = request.form.get("user_id")
        if not user_id:
            return "<script>alert('❌ Не указан ID пользователя'); window.history.back();</script>"

        with engine.connect() as conn:
            conn.execute(
                sql_text("""
                    UPDATE users 
                    SET is_blocked = 1, blocked_at = datetime('now'), blocked_by = :admin_id 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id, "admin_id": session.get("user_id")}
            )
            conn.commit()
        return "<script>alert('✅ Пользователь заблокирован'); window.history.back();</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"


@app.route("/unblock_user", methods=["POST"])
@login_required
def unblock_user():
    try:
        user_id = request.form.get("user_id")
        if not user_id:
            return "<script>alert('❌ Не указан ID пользователя'); window.history.back();</script>"

        with engine.connect() as conn:
            conn.execute(
                sql_text("""
                    UPDATE users 
                    SET is_blocked = 0, blocked_at = NULL, blocked_by = NULL 
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            )
            conn.commit()
        return "<script>alert('✅ Пользователь разблокирован'); window.history.back();</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"


@app.route("/make_admin", methods=["POST"])
@login_required
def make_admin():
    try:
        user_id = request.form.get("user_id")
        if not user_id:
            return "<script>alert('❌ Не указан ID пользователя'); window.history.back();</script>"

        with engine.connect() as conn:
            result = conn.execute(
                sql_text("SELECT is_admin FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            if not result:
                return "<script>alert('❌ Пользователь не найден'); window.history.back();</script>"

            new_status = 0 if result.is_admin else 1
            conn.execute(
                sql_text("UPDATE users SET is_admin = :status WHERE user_id = :user_id"),
                {"status": new_status, "user_id": user_id}
            )
            conn.commit()
        action = "назначен администратором" if new_status else "снят с прав администратора"
        return f"<script>alert('✅ Пользователь {action}'); window.history.back();</script>"
    except Exception as e:
        return f"<script>alert('❌ Ошибка: {e}'); window.history.back();</script>"

# --- Запуск ---
if __name__ == "__main__":
    print("\n" + "="*60)
    print(f"🌐 Веб-интерфейс FedorBot v{__version__} запущен!")
    print("🏠 Откройте: http://localhost:5000")
    print("📊 Админка: /admin")
    print("📘 API: /swagger")
    print("="*60)
    app.run(host="127.0.0.1", port=5000, debug=True)
