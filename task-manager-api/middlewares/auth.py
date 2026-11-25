"""Middleware de autenticação: identifica o usuário do token e exige login quando AUTH_REQUIRED=true."""
from flask import current_app, g, request

from errors import UnauthorizedError
from services.authorization_service import Actor

# Endpoints acessíveis sem token mesmo com AUTH_REQUIRED=true.
PUBLIC_ENDPOINTS = {"system.index", "system.health", "users.login", "users.create_user", "static"}


def _load_current_user():
    g.current_user = None
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        token_service = current_app.extensions["token_service"]
        g.current_user = token_service.user_from_token(header[len("Bearer "):])

    if current_app.config["AUTH_REQUIRED"] and request.endpoint not in PUBLIC_ENDPOINTS:
        if g.current_user is None or not g.current_user.active:
            raise UnauthorizedError("Token ausente ou inválido")


def current_actor():
    """Actor da requisição atual, entregue pelas views aos controllers."""
    return Actor(user=g.get("current_user"), auth_enabled=current_app.config["AUTH_REQUIRED"])


def register_auth(app):
    app.before_request(_load_current_user)
