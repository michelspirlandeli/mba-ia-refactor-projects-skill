"""Casos de uso de usuários e autenticação."""
import logging

from flask import current_app, g
from sqlalchemy import func

from database import db
from middlewares.auth import issue_token
from middlewares.error_handler import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from models.task import Task
from models.user import User
from utils.helpers import utcnow
from utils.validators import require_payload, validate_new_user, validate_role, validate_user_update

logger = logging.getLogger(__name__)


def get_user_or_404(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    return user


def _ensure_can_assign_role(role):
    """Com AUTH_REQUIRED ativo, só um admin autenticado pode atribuir roles privilegiados."""
    if role == 'user' or not current_app.config['AUTH_REQUIRED']:
        return
    current = g.get('current_user')
    if current is None or not current.is_admin():
        raise ForbiddenError('Apenas administradores podem atribuir este role')


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


def create_user(payload):
    fields = validate_new_user(payload)
    if db.session.execute(db.select(User).filter_by(email=fields['email'])).scalar():
        raise ConflictError('Email já cadastrado')
    validate_role(fields['role'])
    _ensure_can_assign_role(fields['role'])

    user = User(name=fields['name'], email=fields['email'], role=fields['role'])
    user.set_password(fields['password'])
    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado id=%s', user.id)
    return user.to_dict()


def update_user(user_id, payload):
    user = get_user_or_404(user_id)
    fields = validate_user_update(payload)

    if 'email' in fields:
        existing = db.session.execute(db.select(User).filter_by(email=fields['email'])).scalar()
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
    if 'role' in fields:
        _ensure_can_assign_role(fields['role'])

    password = fields.pop('password', None)
    if password:
        user.set_password(password)
    for name, value in fields.items():
        setattr(user, name, value)
    db.session.commit()
    return user.to_dict()


def delete_user(user_id):
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
    return [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'created_at': str(task.created_at),
            'due_date': str(task.due_date) if task.due_date else None,
            'overdue': task.is_overdue(now),
        }
        for task in tasks
    ]


def login(payload):
    require_payload(payload)
    email, password = payload.get('email'), payload.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
    if not user or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')
    if not user.active:
        raise ForbiddenError('Usuário inativo')

    db.session.commit()  # persiste migração de hash legado, se houver
    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user),
    }
