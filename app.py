
import os
import sqlite3
from pathlib import Path
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g,
    render_template_string,
)
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- CONFIGURATION ----------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "freshmeat.db"
TEMPLATE_DIR = BASE_DIR / "templates"

app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-only-change-this-secret-key"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ---------------- DATABASE ----------------

def init_db():
    with sqlite3.connect(DATABASE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


init_db()


# ---------------- LOGIN CHECK ----------------

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
        elif len(username) < 3 or len(username) > 50:
            flash("Username must be 3 to 50 characters.", "error")
        elif any(not (c.isalnum() or c in "_.-") for c in username):
            flash("Username can contain letters, numbers, ., _ and - only.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                flash("Username already exists. Choose another.", "error")
            else:
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))

        return render_template("register.html")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash FROM users "
            "WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    dashboard_file = TEMPLATE_DIR / "dashboard.html"

    if dashboard_file.exists():
        return render_template("dashboard.html")

    return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>FreshMeat Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: #f5f5f5;
                    text-align: center;
                    padding: 50px 15px;
                }
                main {
                    max-width: 650px;
                    margin: auto;
                    padding: 30px;
                    background: white;
                    border-radius: 15px;
                }
                a, button {
                    display: inline-block;
                    padding: 12px 20px;
                    margin: 8px;
                    background: #d62828;
                    color: white;
                    border: 0;
                    border-radius: 6px;
                    text-decoration: none;
                    cursor: pointer;
                }
            </style>
        </head>
        <body>
            <main>
                <h1>FreshMeat Dashboard</h1>
                <h2>Welcome, {{ username }}!</h2>
                <p>You are logged in successfully.</p>
                <a href="{{ url_for('home') }}">Home</a>
                <form method="POST" action="{{ url_for('logout') }}">
                    <button type="submit">Logout</button>
                </form>
            </main>
        </body>
        </html>
    """, username=session["username"])



# ---------------- CHANGE PASSWORD ----------------

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        db = get_db()
        user = db.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], old_password
        ):
            flash("Old password is incorrect.", "error")
        elif len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "error")
        else:
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (
                    generate_password_hash(new_password),
                    session["user_id"]
                )
            )
            db.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("dashboard"))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Change Password | FreshMeat</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #fff7f2;
                margin: 0;
                padding: 40px 15px;
            }
            form {
                max-width: 400px;
                margin: 30px auto;
                padding: 25px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 5px 20px #0001;
            }
            input, button {
                width: 100%;
                padding: 12px;
                margin: 8px 0 16px;
                box-sizing: border-box;
            }
            button {
                background: #a62828;
                color: white;
                border: 0;
                cursor: pointer;
            }
            a { color: #a62828; }
        </style>
    </head>
    <body>
        <form method="POST">
            <h2>Change Admin Password</h2>
            {% for category, message in get_flashed_messages(with_categories=true) %}
                <p>{{ message }}</p>
            {% endfor %}
            <label>Old Password</label>
            <input type="password" name="old_password" required>

            <label>New Password</label>
            <input type="password" name="new_password" minlength="8" required>

            <label>Confirm New Password</label>
            <input type="password" name="confirm_password" minlength="8" required>

            <button type="submit">Change Password</button>
            <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
        </form>
    </body>
    </html>
    """)


# ---------------- LOGOUT ----------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(debug=True)
