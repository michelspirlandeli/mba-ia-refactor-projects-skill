"""Proteção das rotas administrativas por token (header X-Admin-Token).

Fail-closed: sem ADMIN_TOKEN configurado as rotas /admin/* ficam desabilitadas (403).
"""
import hmac
import logging
from functools import wraps

from flask import current_app, request

from src.exceptions import ForbiddenError

logger = logging.getLogger(__name__)


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_TOKEN", "")
        if not expected:
            logger.warning("Rota administrativa %s bloqueada: ADMIN_TOKEN não configurado", request.path)
            raise ForbiddenError("Rotas administrativas desabilitadas: configure ADMIN_TOKEN")
        provided = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(provided, expected):
            raise ForbiddenError("Acesso administrativo negado")
        return view(*args, **kwargs)

    return wrapper
