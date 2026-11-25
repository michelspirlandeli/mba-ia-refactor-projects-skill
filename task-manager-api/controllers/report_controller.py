"""Relatórios de produtividade (agregações feitas no banco)."""
from datetime import timedelta

from sqlalchemy import case, func

from config import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS, STATUS_DONE
from controllers.task_controller import count_by_status, count_overdue, overdue_filter
from controllers.user_controller import get_user_or_404
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from services import authorization_service as authz
from utils.helpers import calculate_percentage, utcnow

USER_REPORT_FIELDS = ('id', 'name', 'email')


def _count_if(condition):
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def _overdue_tasks(now):
    tasks = db.session.execute(db.select(Task).where(overdue_filter(now)).order_by(Task.id)).scalars()
    return [
        {
            'id': task.id,
            'title': task.title,
            'due_date': str(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in tasks
    ]


def _user_productivity():
    rows = db.session.execute(
        db.select(User.id, User.name, func.count(Task.id), _count_if(Task.status == STATUS_DONE))
        .outerjoin(Task, Task.user_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
    ).all()
    return [
        {
            'user_id': user_id,
            'user_name': name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, total),
        }
        for user_id, name, total, completed in rows
    ]


def summary_report(actor):
    authz.ensure_privileged(actor)
    now = utcnow()
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)

    # Contagens gerais e atividade recente em uma única query (antes: 5 COUNTs separados).
    totals = db.session.execute(db.select(
        db.select(func.count(Task.id)).scalar_subquery(),
        db.select(func.count(User.id)).scalar_subquery(),
        db.select(func.count(Category.id)).scalar_subquery(),
        db.select(_count_if(Task.created_at >= since)).scalar_subquery(),
        db.select(_count_if(db.and_(Task.status == STATUS_DONE, Task.updated_at >= since))).scalar_subquery(),
    )).one()
    total_tasks, total_users, total_categories, created_recently, completed_recently = totals

    by_priority = dict(db.session.execute(db.select(Task.priority, func.count()).group_by(Task.priority)).all())
    overdue = _overdue_tasks(now)

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': total_tasks,
            'total_users': total_users,
            'total_categories': total_categories,
        },
        'tasks_by_status': count_by_status(),
        'tasks_by_priority': {label: by_priority.get(p, 0) for p, label in PRIORITY_LABELS.items()},
        'overdue': {'count': len(overdue), 'tasks': overdue},
        'recent_activity': {
            'tasks_created_last_7_days': created_recently,
            'tasks_completed_last_7_days': completed_recently,
        },
        'user_productivity': _user_productivity(),
    }


def user_report(user_id, actor):
    authz.ensure_self_or_privileged(actor, user_id)
    user = get_user_or_404(user_id)
    owned = Task.user_id == user_id

    counts = count_by_status(owned)
    total = sum(counts.values())
    high_priority = db.session.scalar(
        db.select(func.count(Task.id)).where(owned, Task.priority <= HIGH_PRIORITY_MAX))

    user_data = user.to_dict()
    return {
        'user': {field: user_data[field] for field in USER_REPORT_FIELDS},
        'statistics': {
            'total_tasks': total,
            **counts,
            'overdue': count_overdue(owned),
            'high_priority': high_priority,
            'completion_rate': calculate_percentage(counts[STATUS_DONE], total),
        },
    }
