"""Popula o banco com dados de demonstração (APAGA os dados existentes). Somente fora de produção.

Senhas dos usuários de demonstração: variável SEED_PASSWORD; se ausente, uma senha aleatória
é gerada e exibida no final.
"""
import os
import secrets
import sys
from datetime import timedelta

from app import create_app
from config import PRODUCTION_ENVS, ROLE_ADMIN, ROLE_MANAGER, ROLE_USER
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import utcnow

USERS = [
    {'key': 'joao', 'name': 'João Silva', 'email': 'joao@email.com', 'role': ROLE_ADMIN},
    {'key': 'maria', 'name': 'Maria Santos', 'email': 'maria@email.com', 'role': ROLE_USER},
    {'key': 'pedro', 'name': 'Pedro Oliveira', 'email': 'pedro@email.com', 'role': ROLE_MANAGER},
]

CATEGORIES = [
    {'key': 'backend', 'name': 'Backend', 'description': 'Tarefas de backend', 'color': '#3498db'},
    {'key': 'frontend', 'name': 'Frontend', 'description': 'Tarefas de frontend', 'color': '#2ecc71'},
    {'key': 'devops', 'name': 'DevOps', 'description': 'Tarefas de infraestrutura', 'color': '#e74c3c'},
    {'key': 'bug', 'name': 'Bug', 'description': 'Correção de bugs', 'color': '#e67e22'},
]

# due_in_days: negativo = atrasada; None = sem prazo.
TASKS = [
    ('Implementar autenticação JWT', 'Adicionar autenticação real com JWT', 'pending', 1, 'joao', 'backend', -3, None),
    ('Criar tela de login', 'Tela de login responsiva', 'in_progress', 2, 'maria', 'frontend', 5, None),
    ('Configurar CI/CD', 'Pipeline com GitHub Actions', 'done', 2, 'pedro', 'devops', None, 'devops,ci,github'),
    ('Corrigir bug no filtro de busca', 'Filtro não funciona com caracteres especiais', 'pending', 1, 'joao', 'bug', -1, None),
    ('Adicionar paginação na API', 'Endpoints retornam todos os registros', 'pending', 3, 'joao', 'backend', 10, None),
    ('Escrever testes unitários', 'Cobertura mínima de 80%', 'pending', 2, 'maria', 'backend', None, None),
    ('Documentar API com Swagger', 'Gerar documentação automática', 'cancelled', 4, 'pedro', 'backend', None, None),
    ('Refatorar models', 'Melhorar organização dos models', 'in_progress', 3, 'maria', 'backend', None, 'refactor,tech-debt'),
    ('Configurar monitoramento', 'Prometheus + Grafana', 'pending', 4, 'pedro', 'devops', 20, None),
    ('Melhorar validações de input', 'Usar marshmallow ou pydantic', 'pending', 3, 'joao', 'backend', None, 'improvement,validation'),
]


def seed_data():
    app = create_app()
    if app.config['APP_ENV'] in PRODUCTION_ENVS:
        sys.exit('seed.py apaga todos os dados e não roda com APP_ENV de produção.')

    password = os.environ.get('SEED_PASSWORD') or secrets.token_urlsafe(12)

    with app.app_context():
        db.session.execute(db.delete(Task))
        db.session.execute(db.delete(User))
        db.session.execute(db.delete(Category))
        db.session.commit()

        users = {}
        for spec in USERS:
            user = User(name=spec['name'], email=spec['email'], role=spec['role'])
            user.set_password(password)
            db.session.add(user)
            users[spec['key']] = user

        categories = {}
        for spec in CATEGORIES:
            category = Category(name=spec['name'], description=spec['description'], color=spec['color'])
            db.session.add(category)
            categories[spec['key']] = category
        db.session.flush()  # gera os ids usados nas tasks

        now = utcnow()
        for title, description, status, priority, owner, category_key, due_in_days, tags in TASKS:
            db.session.add(Task(
                title=title,
                description=description,
                status=status,
                priority=priority,
                user_id=users[owner].id,
                category_id=categories[category_key].id,
                due_date=now + timedelta(days=due_in_days) if due_in_days is not None else None,
                tags=tags,
            ))
        db.session.commit()

        print('Seed concluído com sucesso!')
        print(f"  {db.session.scalar(db.select(db.func.count(User.id)))} usuários")
        print(f"  {db.session.scalar(db.select(db.func.count(Category.id)))} categorias")
        print(f"  {db.session.scalar(db.select(db.func.count(Task.id)))} tasks")
        if not os.environ.get('SEED_PASSWORD'):
            print(f"  Senha gerada para os usuários de demonstração: {password}")


if __name__ == '__main__':
    seed_data()
