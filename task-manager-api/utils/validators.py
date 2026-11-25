"""Validação de payloads centralizada (antes copiada entre create/update)."""
from config import (
    DATE_FORMAT, DEFAULT_PRIORITY, MAX_PRIORITY, MAX_TITLE_LENGTH, MIN_PASSWORD_LENGTH,
    MIN_PRIORITY, MIN_TITLE_LENGTH, VALID_ROLES, VALID_STATUSES,
)
from middlewares.error_handler import ValidationError
from utils.helpers import is_valid_color, is_valid_email, parse_date


def require_payload(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def _title(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError('Título é obrigatório')
    value = value.strip()
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return value


def _priority(value):
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
    return value


def _status(value):
    if value not in VALID_STATUSES:
        raise ValidationError('Status inválido')
    return value


def _due_date(value, error_message):
    if not value:
        return None
    parsed = parse_date(value, DATE_FORMAT)
    if parsed is None:
        raise ValidationError(error_message)
    return parsed


def _tags(value):
    if isinstance(value, list):
        return ','.join(str(tag) for tag in value)
    return value


def validate_task(data, partial=False):
    """Retorna dict com os campos válidos. `partial=True` para updates (só campos presentes)."""
    require_payload(data)
    result = {}

    if not partial or 'title' in data:
        result['title'] = _title(data.get('title'))
    if 'description' in data or not partial:
        result['description'] = data.get('description', '')
    if 'status' in data or not partial:
        result['status'] = _status(data.get('status', 'pending'))
    if 'priority' in data or not partial:
        result['priority'] = _priority(data.get('priority', DEFAULT_PRIORITY))
    if 'user_id' in data or not partial:
        result['user_id'] = data.get('user_id')
    if 'category_id' in data or not partial:
        result['category_id'] = data.get('category_id')
    if 'due_date' in data:
        message = 'Formato de data inválido' if partial else 'Formato de data inválido. Use YYYY-MM-DD'
        result['due_date'] = _due_date(data['due_date'], message)
    if 'tags' in data and (partial or data['tags']):
        result['tags'] = _tags(data['tags'])
    return result


def validate_new_user(data):
    require_payload(data)
    name, email, password = data.get('name'), data.get('email'), data.get('password')
    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    if not is_valid_email(email):
        raise ValidationError('Email inválido')
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    return {'name': name, 'email': email, 'password': password, 'role': data.get('role', 'user')}


def validate_role(role):
    if role not in VALID_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_user_update(data):
    require_payload(data)
    result = {}
    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            raise ValidationError('Nome é obrigatório')
        result['name'] = data['name']
    if 'email' in data:
        if not is_valid_email(data['email']):
            raise ValidationError('Email inválido')
        result['email'] = data['email']
    if 'password' in data:
        if not isinstance(data['password'], str) or len(data['password']) < MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha muito curta')
        result['password'] = data['password']
    if 'role' in data:
        result['role'] = validate_role(data['role'])
    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise ValidationError('Campo active deve ser booleano')
        result['active'] = data['active']
    return result


def validate_category(data, partial=False):
    require_payload(data)
    result = {}
    if not partial or 'name' in data:
        if not data.get('name'):
            raise ValidationError('Nome é obrigatório')
        result['name'] = data['name']
    if 'description' in data or not partial:
        result['description'] = data.get('description', '')
    if 'color' in data:
        if not is_valid_color(data['color']):
            raise ValidationError('Cor inválida. Use o formato #RRGGBB')
        result['color'] = data['color']
    return result


def parse_int_param(value, name):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'Parâmetro {name} inválido')
