"""Proteção das rotas administrativas por token (header X-Admin-Token)."""
import hmac
import logging
from functools import wraps

from flask import current_app, request

from src.middlewares.error_handler import ForbiddenError

logger = logging.getLogger(__name__)


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN", "")
        if not expected:
            # Sem ADMIN_TOKEN configurado a rota fica aberta (compatibilidade com o comportamento legado).
            logger.warning("Rota administrativa %s acessada sem ADMIN_TOKEN configurado", request.path)
            return view(*args, **kwargs)
        provided = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(provided, expected):
            raise ForbiddenError("Acesso administrativo negado")
        return view(*args, **kwargs)

    return wrapper
