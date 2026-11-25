"""Regras de autorização (quem pode fazer o quê). Puras: recebem o Actor, não dependem do Flask."""
from dataclasses import dataclass

from config import PRIVILEGED_ROLES, ROLE_ADMIN
from errors import ForbiddenError


@dataclass(frozen=True)
class Actor:
    """Quem está fazendo a requisição.

    `auth_enabled=False` (AUTH_REQUIRED=false, opt-out de dev) libera tudo — contrato legado.
    """
    user: object = None
    auth_enabled: bool = True

    @property
    def unrestricted(self):
        return not self.auth_enabled

    @property
    def user_id(self):
        return self.user.id if self.user is not None else None

    def has_role(self, *roles):
        return self.user is not None and self.user.role in roles

    def is_admin(self):
        return self.has_role(ROLE_ADMIN)

    def is_privileged(self):
        return self.has_role(*PRIVILEGED_ROLES)


def _deny(message):
    raise ForbiddenError(message)


def ensure_admin(actor):
    if not (actor.unrestricted or actor.is_admin()):
        _deny("Apenas administradores podem executar esta ação")


def ensure_privileged(actor):
    if not (actor.unrestricted or actor.is_privileged()):
        _deny("Apenas administradores ou gerentes podem executar esta ação")


def ensure_self_or_admin(actor, user_id):
    if not (actor.unrestricted or actor.is_admin() or actor.user_id == user_id):
        _deny("Você só pode alterar o próprio usuário")


def ensure_self_or_privileged(actor, user_id):
    if not (actor.unrestricted or actor.is_privileged() or actor.user_id == user_id):
        _deny("Acesso permitido apenas ao próprio usuário, administradores ou gerentes")


def ensure_can_modify_task(actor, task):
    if not (actor.unrestricted or actor.is_privileged() or (task.user_id and actor.user_id == task.user_id)):
        _deny("Você só pode alterar as próprias tasks")


def ensure_can_assign_task(actor, user_id):
    """Usuário comum só atribui tasks a si mesmo (ou deixa sem responsável)."""
    if user_id is None or actor.unrestricted or actor.is_privileged() or actor.user_id == user_id:
        return
    _deny("Você só pode atribuir tasks a si mesmo")


def ensure_can_set_privileged_fields(actor, fields, default_role):
    """role != padrão e o campo `active` só podem ser definidos por admin."""
    if actor.unrestricted or actor.is_admin():
        return
    if fields.get("role", default_role) != default_role or "active" in fields:
        _deny("Apenas administradores podem alterar role ou status de ativação")
