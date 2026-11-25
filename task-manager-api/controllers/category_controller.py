"""Casos de uso de categorias (antes misturados em report_routes.py)."""
from sqlalchemy import func

from config import DEFAULT_COLOR
from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from utils.validators import validate_category


def get_category_or_404(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')
    return category


def list_categories():
    task_counts = dict(db.session.execute(
        db.select(Task.category_id, func.count()).group_by(Task.category_id)
    ).all())
    categories = db.session.execute(db.select(Category).order_by(Category.id)).scalars()
    return [{**c.to_dict(), 'task_count': task_counts.get(c.id, 0)} for c in categories]


def create_category(payload):
    fields = validate_category(payload)
    category = Category(color=fields.pop('color', DEFAULT_COLOR), **fields)
    db.session.add(category)
    db.session.commit()
    return category.to_dict()


def update_category(category_id, payload):
    category = get_category_or_404(category_id)
    for name, value in validate_category(payload, partial=True).items():
        setattr(category, name, value)
    db.session.commit()
    return category.to_dict()


def delete_category(category_id):
    category = get_category_or_404(category_id)
    # Desvincula as tasks antes de remover (antes ficavam com category_id órfão).
    db.session.execute(db.update(Task).where(Task.category_id == category_id).values(category_id=None))
    db.session.delete(category)
    db.session.commit()
