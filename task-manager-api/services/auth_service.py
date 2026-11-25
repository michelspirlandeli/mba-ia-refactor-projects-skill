"""Autenticação: tokens assinados (itsdangerous) e limitação de tentativas de login."""
import threading
import time

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from errors import TooManyRequestsError
from models.user import User

TOKEN_SALT = "auth-token"


class TokenService:
    def __init__(self, secret_key, max_age_seconds):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._max_age = max_age_seconds

    def issue(self, user):
        return self._serializer.dumps({"user_id": user.id})

    def user_from_token(self, token):
        try:
            data = self._serializer.loads(token, max_age=self._max_age)
        except (BadSignature, SignatureExpired):
            return None
        return db.session.get(User, data.get("user_id"))


class LoginThrottle:
    """Bloqueia (429) após `max_failures` falhas para o mesmo (IP, email) dentro da janela.

    Estado encapsulado e protegido por lock; uma instância por aplicação (criada no create_app).
    Em deploy com vários processos, troque por um store compartilhado (ex.: Redis).
    """

    def __init__(self, max_failures, window_seconds, clock=time.monotonic):
        self._max_failures = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        return [t for t in self._failures.get(key, []) if now - t < self._window]

    def check(self, key):
        with self._lock:
            recent = self._recent(key, self._clock())
            self._failures[key] = recent
            if len(recent) >= self._max_failures:
                raise TooManyRequestsError("Muitas tentativas de login. Tente novamente mais tarde.")

    def register_failure(self, key):
        with self._lock:
            now = self._clock()
            self._failures[key] = self._recent(key, now) + [now]

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)
