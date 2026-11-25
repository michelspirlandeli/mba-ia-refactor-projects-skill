"""Casos de uso de tasks."""
import logging

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import VALID_STATUSES
from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from services.notification_service import NotificationService
from utils.helpers import calculate_percentage, utcnow
from utils.validators import parse_int_param, validate_task

logger = logging.getLogger(__name__)


def get_task_or_404(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return task


def _ensure_references(fields):
    if fields.get('user_id') and not db.session.get(User, fields['user_id']):
        raise NotFoundError('Usuário não encontrado')
    if fields.get('category_id') and not db.session.get(Category, fields['category_id']):
        raise NotFoundError('Categoria não encontrada')


def list_tasks():
    # Usuário e categoria carregados no mesmo SELECT (antes: 2 queries extras por task).
    tasks = db.session.execute(
        db.select(Task).options(joinedload(Task.user), joinedload(Task.category)).order_by(Task.id)
    ).scalars().all()
    now = utcnow()
    result = []
    for task in tasks:
        data = task.to_dict()
        data['overdue'] = task.is_overdue(now)
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id):
    task = get_task_or_404(task_id)
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data


def create_task(payload):
    fields = validate_task(payload)
    _ensure_references(fields)

    task = Task(**fields)
    db.session.add(task)
    db.session.commit()
    logger.info('Task criada id=%s', task.id)

    if task.user_id:
        NotificationService.from_config(current_app.config).notify_task_assigned(task.user, task)
    return task.to_dict()


def update_task(task_id, payload):
    task = get_task_or_404(task_id)
    fields = validate_task(payload, partial=True)
    _ensure_references(fields)

    for name, value in fields.items():
        setattr(task, name, value)
    task.updated_at = utcnow()
    db.session.commit()
    logger.info('Task atualizada id=%s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = get_task_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    logger.info('Task deletada id=%s', task_id)


def search_tasks(query, status, priority, user_id):
    stmt = db.select(Task).order_by(Task.id)
    if query:
        stmt = stmt.where(db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%')))
    if status:
        stmt = stmt.where(Task.status == status)
    priority = parse_int_param(priority, 'priority')
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    user_id = parse_int_param(user_id, 'user_id')
    if user_id is not None:
        stmt = stmt.where(Task.user_id == user_id)
    return [task.to_dict() for task in db.session.execute(stmt).scalars()]


def count_by_status():
    counts = dict(db.session.execute(db.select(Task.status, func.count()).group_by(Task.status)).all())
    return {status: counts.get(status, 0) for status in VALID_STATUSES}


def count_overdue():
    now = utcnow()
    return sum(1 for task in db.session.execute(db.select(Task)).scalars() if task.is_overdue(now))


def task_stats():
    by_status = count_by_status()
    total = sum(by_status.values())
    return {
        'total': total,
        **by_status,
        'overdue': count_overdue(),
        'completion_rate': calculate_percentage(by_status['done'], total),
    }
