"""Casos de uso de usuários e autenticação."""
import logging

from sqlalchemy import func

from config import DEFAULT_ROLE
from database import db
from errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from models.task import Task
from models.user import User
from services import authorization_service as authz
from utils.helpers import utcnow
from utils.validators import require_payload, validate_new_user, validate_user_update

logger = logging.getLogger(__name__)

USER_TASK_FIELDS = ('id', 'title', 'description', 'status', 'priority', 'created_at', 'due_date')


def get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    return user


def _email_taken(email, exclude_id=None):
    existing = db.session.execute(db.select(User).filter_by(email=email)).scalar()
    return existing is not None and existing.id != exclude_id


def list_users():
    task_counts = dict(db.session.execute(
        db.select(Task.user_id, func.count()).group_by(Task.user_id)
    ).all())
    users = db.session.execute(db.select(User).order_by(User.id)).scalars()
    return [{**user.to_dict(), 'task_count': task_counts.get(user.id, 0)} for user in users]


def get_user(user_id):
    user = get_user_or_404(user_id)
    data = user.to_dict()
    tasks = db.session.execute(db.select(Task).where(Task.user_id == user_id).order_by(Task.id)).scalars()
    data['tasks'] = [task.to_dict() for task in tasks]
    return data


def create_user(payload, actor):
    fields = validate_new_user(payload)
    if _email_taken(fields['email']):
        raise ConflictError('Email já cadastrado')
    # Cadastro é público, mas roles privilegiados só podem ser atribuídos por admin autenticado.
    authz.ensure_can_set_privileged_fields(actor, {'role': fields['role']}, DEFAULT_ROLE)

    user = User(name=fields['name'], email=fields['email'], role=fields['role'])
    user.set_password(fields['password'])
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado id=%s', user.id)
    return user.to_dict()


def update_user(user_id, payload, actor):
    authz.ensure_self_or_admin(actor, user_id)
    user = get_user_or_404(user_id)
    fields = validate_user_update(payload)
    authz.ensure_can_set_privileged_fields(actor, fields, DEFAULT_ROLE)

    if 'email' in fields and _email_taken(fields['email'], exclude_id=user_id):
        raise ConflictError('Email já cadastrado')

    password = fields.pop('password', None)
    if password:
        user.set_password(password)
    for name, value in fields.items():
        setattr(user, name, value)
    db.session.commit()
    return user.to_dict()


def delete_user(user_id, actor):
    authz.ensure_admin(actor)
    user = get_user_or_404(user_id)
    # Remove as tasks do usuário na mesma transação (bulk delete em vez de laço).
    db.session.execute(db.delete(Task).where(Task.user_id == user_id))
    db.session.delete(user)
    db.session.commit()
    logger.info('Usuário deletado id=%s', user_id)


def get_user_tasks(user_id):
    get_user_or_404(user_id)
    tasks = db.session.execute(db.select(Task).where(Task.user_id == user_id).order_by(Task.id)).scalars()
    now = utcnow()
    result = []
    for task in tasks:
        data = task.to_dict()
        summary = {field: data[field] for field in USER_TASK_FIELDS}
        summary['overdue'] = task.is_overdue(now)
        result.append(summary)
    return result


def login(payload, client_key, throttle, token_service):
    require_payload(payload)
    email, password = payload.get('email'), payload.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError('Email e senha devem ser texto')

    key = (client_key, email.lower())
    throttle.check(key)  # 429 após muitas falhas seguidas

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
    if not user or not user.check_password(password):
        throttle.register_failure(key)
        logger.info('Falha de login')
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    throttle.reset(key)
    db.session.commit()  # persiste migração de hash legado, se houver
    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': token_service.issue(user),
    }
