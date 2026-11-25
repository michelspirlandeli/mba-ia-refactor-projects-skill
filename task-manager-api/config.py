"""Configuração da aplicação (variáveis de ambiente) e constantes de domínio."""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PRODUCTION_ENVS = ("production", "prod", "producao")


def _env_bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _secret_key(app_env):
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if app_env in PRODUCTION_ENVS:
        raise RuntimeError("SECRET_KEY é obrigatório em produção (tokens precisam sobreviver a restarts e workers)")
    # Dev: chave efêmera. Tokens emitidos deixam de valer quando o processo reinicia.
    return secrets.token_hex(32)


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    SECRET_KEY = _secret_key(APP_ENV)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _env_bool("FLASK_DEBUG")
    # Use 0.0.0.0 apenas em container/rede controlada.
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    # Origens separadas por vírgula. Vazio = CORS desabilitado (mesma origem apenas).
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

    # Autenticação ligada por padrão: todas as rotas (exceto /, /health, /login e POST /users)
    # exigem "Authorization: Bearer <token>". AUTH_REQUIRED=false é opt-out explícito para dev.
    AUTH_REQUIRED = _env_bool("AUTH_REQUIRED", "true")
    TOKEN_MAX_AGE_SECONDS = int(os.environ.get("TOKEN_MAX_AGE_SECONDS", str(8 * 3600)))
    LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "5"))
    LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", str(15 * 60)))

    # Notificações por email (desligadas por padrão; credenciais só via ambiente).
    NOTIFICATIONS_ENABLED = _env_bool("NOTIFICATIONS_ENABLED")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_TIMEOUT_SECONDS = int(os.environ.get("SMTP_TIMEOUT_SECONDS", "10"))


# --- Regras de domínio ---
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
VALID_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE, STATUS_CANCELLED)
CLOSED_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
VALID_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_MANAGER)
DEFAULT_ROLE = ROLE_USER
PRIVILEGED_ROLES = (ROLE_ADMIN, ROLE_MANAGER)  # gerenciam tasks, categorias e relatórios

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 150
MAX_CATEGORY_DESCRIPTION_LENGTH = 300
MAX_TAGS_LENGTH = 500
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2  # prioridades 1 e 2 contam como "alta"
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}

MIN_PASSWORD_LENGTH = 8
DEFAULT_COLOR = "#000000"
RECENT_ACTIVITY_DAYS = 7
DATE_FORMAT = "%Y-%m-%d"
MAX_PAGE_SIZE = 100

API_VERSION = "1.0"
