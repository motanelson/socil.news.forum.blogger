from flask import Flask, request, redirect, send_from_directory
import sqlite3
import hashlib
import secrets
import os

app = Flask(__name__)

DB = "blog.db"
IMAGE_FOLDER = "images"
MAX_FILE_SIZE = 5 * 1024 * 1024

os.makedirs(IMAGE_FOLDER, exist_ok=True)

lista1 = ["news", "actualidade", "desporto", "social"]

# ---------- DB ----------
def get_db():
    return sqlite3.connect(DB, timeout=10, check_same_thread=False)


def init_db():
    with get_db() as db:
        c = db.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            password TEXT,
            approved INTEGER DEFAULT 0,
            activation_key TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            url TEXT,
            message TEXT,
            image TEXT
        )
        """)


# ---------- UTIL ----------
def sanitize(text):
    return text.replace("<", "").replace(">", "")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_key():
    return secrets.token_hex(16)


# ---------- USERS ----------
def create_user(url, password):
    key = generate_key()

    with get_db() as db:
        c = db.cursor()
        c.execute(
            "INSERT INTO users (url, password, approved, activation_key) VALUES (?, ?, 0, ?)",
            (url, hash_password(password), key)
        )
        user_id = c.lastrowid

    link = f"http://127.0.0.1:5000/activate/{user_id}/{key}"

    with open("approve.txt", "a") as f:
        f.write(f"{url}|||{link}\n")


def check_user(url, password):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT password, approved FROM users WHERE url=?", (url,))
        row = c.fetchone()

    if row:
        if row[0] != hash_password(password):
            return "wrong_pass"
        if row[1] == 0:
            return "not_approved"
        return "ok"

    return "not_exist"


# ---------- IMAGE ----------
def save_image(file):
    if file:
        filename = file.filename.lower()

        if not (filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".jpeg") or filename.endswith(".gif")):
            return None

        data = file.read()
        if len(data) > MAX_FILE_SIZE:
            return None

        with get_db() as db:
            c = db.cursor()
            c.execute("SELECT MAX(id) FROM posts")
            max_id = c.fetchone()[0]
            file_id = (max_id or 0) + 1

        ext = filename.split(".")[-1]
        new_name = f"{file_id}.{ext}"

        path = os.path.join(IMAGE_FOLDER, new_name)
        with open(path, "wb") as f:
            f.write(data)

        return new_name

    return None


@app.route("/images/<filename>")
def get_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)


# ---------- POSTS ----------
def save_post(category, url, message, image):
    with get_db() as db:
        c = db.cursor()
        c.execute(
            "INSERT INTO posts (category, url, message, image) VALUES (?, ?, ?, ?)",
            (category, url, message, image)
        )


def load_posts(category, page, per_page=5):
    offset = (page - 1) * per_page

    with get_db() as db:
        c = db.cursor()
        c.execute(
            "SELECT url, message, image FROM posts WHERE category=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (category, per_page, offset)
        )
        return c.fetchall()


def count_posts(category):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM posts WHERE category=?", (category,))
        return c.fetchone()[0]


# ---------- ROUTES ----------

@app.route("/")
def home():
    html = """
    <body style="background:black;color:white;font-family:Arial;">
    <h1>Fórum Notícias</h1>
    <a href="/register">➕ Registar</a>
    """
    for cat in lista1:
        html += f'<br><a href="/{cat}">{cat}</a>'
    html += "</body>"
    return html


@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""

    if request.method == "POST":
        url = sanitize(request.form.get("url", ""))
        password = request.form.get("password", "")

        if url and password:
            try:
                create_user(url, password)
                msg = "✅ Registado! Aguarda aprovação."
            except:
                msg = "❌ Já existe"

    return f"""
    <body style="background:black;color:white;">
    <a href="/">⬅</a>
    <form method="POST">
        <input name="url"><br>
        <input type="password" name="password"><br>
        <button>Registar</button>
    </form>
    <p>{msg}</p>
    </body>
    """


@app.route("/activate/<int:user_id>/<key>")
def activate(user_id, key):
    with get_db() as db:
        c = db.cursor()
        c.execute("SELECT activation_key FROM users WHERE id=?", (user_id,))
        row = c.fetchone()

        if row and row[0] == key:
            c.execute("UPDATE users SET approved=1 WHERE id=?", (user_id,))
            db.commit()
            return "✅ Ativado!"

    return "❌ Inválido"


@app.route("/<category>", methods=["GET", "POST"])
def category(category):
    if category not in lista1:
        return "Erro", 404

    page = request.args.get("page", 1, type=int)
    error = ""

    if request.method == "POST":
        url = sanitize(request.form.get("url", ""))
        msg = sanitize(request.form.get("message", ""))
        password = request.form.get("password", "")
        file = request.files.get("image")

        if url and msg and password:
            res = check_user(url, password)

            if res == "ok":
                img = save_image(file)
                save_post(category, url, msg, img)
                return redirect(f"/{category}?page={page}")
            elif res == "wrong_pass":
                error = "Password errada"
            elif res == "not_approved":
                error = "Conta não ativada"
            else:
                error = "Utilizador não existe"

    posts = load_posts(category, page)
    total = count_posts(category)
    total_pages = (total + 4) // 5 if total else 1

    html = f"""
    <body style="background:black;color:white;">
    <a href="/">⬅</a>
    <h2>{category}</h2>

    <form method="POST" enctype="multipart/form-data">
        <input name="url"><br>
        <input type="password" name="password"><br>
        <textarea name="message"></textarea><br>
        <input type="file" name="image"><br>
        <button>Submit</button>
    </form>

    <p>{error}</p>
    <hr>
    """

    for u, m, img in posts:
        html += f"<b>{u}</b><br><p>{m}</p>"
        if img:
            html += f'<img src="/images/{img}" width="300"><br>'
        html += "<hr>"

    html += f"Página {page}/{total_pages}<br>"

    if page > 1:
        html += f'<a href="/{category}?page={page-1}">⬅</a> '
    if page < total_pages:
        html += f'<a href="/{category}?page={page+1}">➡</a>'

    html += "</body>"
    return html


if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)
