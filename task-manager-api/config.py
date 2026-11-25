"""Configuração da aplicação (variáveis de ambiente) e constantes de domínio."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Autenticação: quando true, todas as rotas (exceto /, /health, /login e POST /users)
    # exigem "Authorization: Bearer <token>" emitido pelo /login.
    AUTH_REQUIRED = _env_bool("AUTH_REQUIRED")
    TOKEN_MAX_AGE_SECONDS = int(os.environ.get("TOKEN_MAX_AGE_SECONDS", str(8 * 3600)))

    # Notificações por email (desligadas por padrão; credenciais só via ambiente).
    NOTIFICATIONS_ENABLED = _env_bool("NOTIFICATIONS_ENABLED")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")


# --- Regras de domínio ---
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
CLOSED_STATUSES = ("done", "cancelled")
VALID_ROLES = ("user", "admin", "manager")
DEFAULT_ROLE = "user"

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta"
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}

MIN_PASSWORD_LENGTH = 4
DEFAULT_COLOR = "#000000"
RECENT_ACTIVITY_DAYS = 7
DATE_FORMAT = "%Y-%m-%d"
