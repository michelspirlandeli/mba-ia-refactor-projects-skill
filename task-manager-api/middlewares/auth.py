"""Tokens assinados (itsdangerous) e verificação opcional de autenticação."""
from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from middlewares.error_handler import UnauthorizedError
from models.user import User

TOKEN_SALT = "auth-token"
# Endpoints acessíveis sem token mesmo com AUTH_REQUIRED=true.
PUBLIC_ENDPOINTS = {"system.index", "system.health", "users.login", "users.create_user", "static"}


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def issue_token(user):
    return _serializer().dumps({"user_id": user.id})


def user_from_token(token):
    try:
        data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE_SECONDS"])
    except (BadSignature, SignatureExpired):
        return None
    return db.session.get(User, data.get("user_id"))


def _load_current_user():
    g.current_user = None
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        g.current_user = user_from_token(header[len("Bearer "):])

    if current_app.config["AUTH_REQUIRED"] and request.endpoint not in PUBLIC_ENDPOINTS:
        if g.current_user is None or not g.current_user.active:
            raise UnauthorizedError("Token ausente ou inválido")


def register_auth(app):
    app.before_request(_load_current_user)
