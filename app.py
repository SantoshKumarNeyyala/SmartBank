import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, render_template, request

# ---------------- PATH + ENV ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
load_dotenv()

# ---------------- IMPORTS ----------------
from routes.auth_routes import auth
from routes.bank_routes import bank
from database.connection import DatabaseConnection
from utils.security import bcrypt
from extension import limiter, csrf
from config import CONFIG


# ---------------- LOGGING ----------------
def setup_logging(app: Flask) -> None:
    """Log to console + rotating file logs/app.log (and keep werkzeug URL visible)"""
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    # ✅ File handler
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, "app.log"),
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    # ✅ Console handler (THIS makes URL line visible)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # Avoid duplicate handlers during reloader
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)

    # Werkzeug logger (startup URL comes from here)
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in werkzeug_logger.handlers):
        werkzeug_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in werkzeug_logger.handlers):
        werkzeug_logger.addHandler(console_handler)


# ---------------- APP FACTORY ----------------
def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )

    # Load all config values from CONFIG class
    app.config.from_object(CONFIG)

    # Cookie security defaults (safe for dev)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_SECURE", False)  # True only on HTTPS

    # Init extensions
    bcrypt.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # Blueprints
    app.register_blueprint(auth)
    app.register_blueprint(bank)

    # Logging
    setup_logging(app)

    @app.before_request
    def log_request():
        if request.path.startswith("/static/"):
            return
        app.logger.info("REQ %s %s", request.method, request.path)

    # Home route
    @app.route("/")
    def home():
        return "<h2>Welcome to SmartBank 🚀</h2><a href='/register'>Register</a>"

    # Error pages
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled error: %s", e)
        return render_template("errors/500.html"), 500

    return app


app = create_app()


# ---------------- RUN ----------------
if __name__ == "__main__":
    with app.app_context():
        try:
            conn = DatabaseConnection.get_connection()
            conn.close()
            app.logger.info("DB connected successfully.")
        except Exception as e:
            app.logger.exception("DB connection failed: %s", e)

    app.logger.info("✅ Server starting at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))