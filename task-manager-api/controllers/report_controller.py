"""Relatórios de produtividade (agregações no banco em vez de N queries)."""
from datetime import timedelta

from sqlalchemy import case, func

from config import HIGH_PRIORITY_MAX, PRIORITY_LABELS, RECENT_ACTIVITY_DAYS
from controllers.task_controller import count_by_status
from controllers.user_controller import get_user_or_404
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import calculate_percentage, utcnow


def _overdue_tasks(now):
    tasks = db.session.execute(db.select(Task).order_by(Task.id)).scalars()
    return [
        {
            'id': task.id,
            'title': task.title,
            'due_date': str(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in tasks if task.is_overdue(now)
    ]


def _user_productivity():
    done = func.sum(case((Task.status == 'done', 1), else_=0))
    rows = db.session.execute(
        db.select(User.id, User.name, func.count(Task.id), func.coalesce(done, 0))
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


def summary_report():
    now = utcnow()
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    by_priority = dict(db.session.execute(db.select(Task.priority, func.count()).group_by(Task.priority)).all())
    overdue = _overdue_tasks(now)

    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': db.session.scalar(db.select(func.count(Task.id))),
            'total_users': db.session.scalar(db.select(func.count(User.id))),
            'total_categories': db.session.scalar(db.select(func.count(Category.id))),
        },
        'tasks_by_status': count_by_status(),
        'tasks_by_priority': {label: by_priority.get(p, 0) for p, label in PRIORITY_LABELS.items()},
        'overdue': {'count': len(overdue), 'tasks': overdue},
        'recent_activity': {
            'tasks_created_last_7_days': db.session.scalar(
                db.select(func.count(Task.id)).where(Task.created_at >= since)),
            'tasks_completed_last_7_days': db.session.scalar(
                db.select(func.count(Task.id)).where(Task.status == 'done', Task.updated_at >= since)),
        },
        'user_productivity': _user_productivity(),
    }


def user_report(user_id):
    user = get_user_or_404(user_id)
    tasks = db.session.execute(db.select(Task).where(Task.user_id == user_id)).scalars().all()
    now = utcnow()

    counts = {status: 0 for status in ('done', 'pending', 'in_progress', 'cancelled')}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
    total = len(tasks)

    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': total,
            **counts,
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            'completion_rate': calculate_percentage(counts['done'], total),
        },
    }
