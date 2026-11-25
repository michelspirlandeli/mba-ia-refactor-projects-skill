"""Casos de uso de tasks."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import CLOSED_STATUSES, STATUS_DONE, VALID_STATUSES
from database import db
from errors import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from services import authorization_service as authz
from utils.helpers import calculate_percentage, utcnow
from utils.validators import parse_int_param, parse_pagination, validate_task

logger = logging.getLogger(__name__)


def get_task_or_404(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return task


def overdue_filter(now):
    """Mesma regra de Task.is_overdue, mas executada no banco."""
    return db.and_(Task.due_date.is_not(None), Task.due_date < now, Task.status.not_in(CLOSED_STATUSES))


def _ensure_references(fields):
    if fields.get('user_id') and not db.session.get(User, fields['user_id']):
        raise NotFoundError('Usuário não encontrado')
    if fields.get('category_id') and not db.session.get(Category, fields['category_id']):
        raise NotFoundError('Categoria não encontrada')


def list_tasks(page=None, per_page=None):
    # Usuário e categoria carregados no mesmo SELECT (antes: 2 queries extras por task).
    stmt = db.select(Task).options(joinedload(Task.user), joinedload(Task.category)).order_by(Task.id)
    pagination = parse_pagination(page, per_page)
    if pagination:
        page, per_page = pagination
        stmt = stmt.limit(per_page).offset((page - 1) * per_page)
    tasks = db.session.execute(stmt).scalars().all()
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


def create_task(payload, actor, notifier):
    fields = validate_task(payload)
    authz.ensure_can_assign_task(actor, fields.get('user_id'))
    _ensure_references(fields)

    task = Task(**fields)
    db.session.add(task)
    db.session.commit()
    logger.info('Task criada id=%s', task.id)

    if task.user_id:
        notifier.notify_task_assigned(task.user, task)  # assíncrono: não bloqueia a resposta
    return task.to_dict()


def update_task(task_id, payload, actor):
    task = get_task_or_404(task_id)
    authz.ensure_can_modify_task(actor, task)
    fields = validate_task(payload, partial=True)
    if 'user_id' in fields:
        authz.ensure_can_assign_task(actor, fields['user_id'])
    _ensure_references(fields)

    for name, value in fields.items():
        setattr(task, name, value)
    task.updated_at = utcnow()
    db.session.commit()
    logger.info('Task atualizada id=%s', task.id)
    return task.to_dict()


def delete_task(task_id, actor):
    task = get_task_or_404(task_id)
    authz.ensure_can_modify_task(actor, task)
    db.session.delete(task)
    db.session.commit()
    logger.info('Task deletada id=%s', task_id)


def search_tasks(query, status, priority, user_id):
    stmt = db.select(Task).order_by(Task.id)
    if query:
        # autoescape: % e _ digitados pelo usuário são literais, não curingas.
        stmt = stmt.where(db.or_(Task.title.contains(query, autoescape=True),
                                 Task.description.contains(query, autoescape=True)))
    if status:
        stmt = stmt.where(Task.status == status)
    priority = parse_int_param(priority, 'priority')
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    user_id = parse_int_param(user_id, 'user_id')
    if user_id is not None:
        stmt = stmt.where(Task.user_id == user_id)
    return [task.to_dict() for task in db.session.execute(stmt).scalars()]


def count_by_status(*conditions):
    stmt = db.select(Task.status, func.count()).where(*conditions).group_by(Task.status)
    counts = dict(db.session.execute(stmt).all())
    return {status: counts.get(status, 0) for status in VALID_STATUSES}


def count_overdue(*conditions, now=None):
    now = now or utcnow()
    return db.session.scalar(db.select(func.count(Task.id)).where(overdue_filter(now), *conditions))


def task_stats():
    by_status = count_by_status()
    total = sum(by_status.values())
    return {
        'total': total,
        **by_status,
        'overdue': count_overdue(),
        'completion_rate': calculate_percentage(by_status[STATUS_DONE], total),
    }
