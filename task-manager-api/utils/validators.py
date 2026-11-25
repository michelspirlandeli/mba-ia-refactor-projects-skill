"""Validação de payloads centralizada. Tipos errados → 400 (nunca 500)."""
from config import (
    DATE_FORMAT, DEFAULT_PRIORITY, DEFAULT_ROLE, MAX_CATEGORY_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH,
    MAX_NAME_LENGTH, MAX_PAGE_SIZE, MAX_PRIORITY, MAX_TAGS_LENGTH, MAX_TITLE_LENGTH, MIN_PASSWORD_LENGTH,
    MIN_PRIORITY, MIN_TITLE_LENGTH, STATUS_PENDING, VALID_ROLES, VALID_STATUSES,
)
from errors import ValidationError
from utils.helpers import is_valid_color, is_valid_email, parse_date


def require_payload(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def _required_text(value, message, max_length):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(message)
    if len(value) > max_length:
        raise ValidationError(f'{message.split(" é ")[0]} muito longo')
    return value


def _optional_text(value, field, max_length=None):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f'{field} deve ser texto')
    if max_length is not None and len(value) > max_length:
        raise ValidationError(f'{field} muito longo')
    return value


def _optional_id(value, field):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f'{field} inválido')
    return value


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
    if not isinstance(value, str):
        raise ValidationError(error_message)
    parsed = parse_date(value, DATE_FORMAT)
    if parsed is None:
        raise ValidationError(error_message)
    return parsed


def _tags(value):
    if value is None:
        return None
    if isinstance(value, list):
        if not all(isinstance(tag, (str, int, float)) and not isinstance(tag, bool) for tag in value):
            raise ValidationError('Tags devem ser texto')
        value = ','.join(str(tag) for tag in value)
    elif not isinstance(value, str):
        raise ValidationError('Tags devem ser uma lista ou texto separado por vírgulas')
    if len(value) > MAX_TAGS_LENGTH:
        raise ValidationError('Tags muito longas')
    return value


def validate_task(data, partial=False):
    """Retorna dict com os campos válidos. `partial=True` para updates (só campos presentes)."""
    require_payload(data)
    result = {}

    if not partial or 'title' in data:
        result['title'] = _title(data.get('title'))
    if 'description' in data or not partial:
        result['description'] = _optional_text(data.get('description', ''), 'Descrição')
    if 'status' in data or not partial:
        result['status'] = _status(data.get('status', STATUS_PENDING))
    if 'priority' in data or not partial:
        result['priority'] = _priority(data.get('priority', DEFAULT_PRIORITY))
    if 'user_id' in data or not partial:
        result['user_id'] = _optional_id(data.get('user_id'), 'user_id')
    if 'category_id' in data or not partial:
        result['category_id'] = _optional_id(data.get('category_id'), 'category_id')
    if 'due_date' in data:
        message = 'Formato de data inválido' if partial else 'Formato de data inválido. Use YYYY-MM-DD'
        result['due_date'] = _due_date(data['due_date'], message)
    if 'tags' in data and (partial or data['tags']):
        result['tags'] = _tags(data['tags'])
    return result


def _password(value, message):
    if not isinstance(value, str) or len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)
    return value


def _email(value):
    if not isinstance(value, str) or len(value) > MAX_EMAIL_LENGTH or not is_valid_email(value):
        raise ValidationError('Email inválido')
    return value


def validate_new_user(data):
    require_payload(data)
    name, email, password = data.get('name'), data.get('email'), data.get('password')
    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    return {
        'name': _required_text(name, 'Nome é obrigatório', MAX_NAME_LENGTH),
        'email': _email(email),
        'password': _password(password, f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres'),
        'role': validate_role(data.get('role', DEFAULT_ROLE)),
    }


def validate_role(role):
    if role not in VALID_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_user_update(data):
    require_payload(data)
    result = {}
    if 'name' in data:
        result['name'] = _required_text(data['name'], 'Nome é obrigatório', MAX_NAME_LENGTH)
    if 'email' in data:
        result['email'] = _email(data['email'])
    if 'password' in data:
        result['password'] = _password(data['password'], 'Senha muito curta')
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
        result['name'] = _required_text(data.get('name'), 'Nome é obrigatório', MAX_NAME_LENGTH)
    if 'description' in data or not partial:
        result['description'] = _optional_text(data.get('description', ''), 'Descrição',
                                               MAX_CATEGORY_DESCRIPTION_LENGTH)
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


def parse_pagination(page, per_page):
    """Paginação opcional: sem `page`, devolve None (lista completa — contrato original)."""
    page = parse_int_param(page, 'page')
    if page is None:
        return None
    per_page = parse_int_param(per_page, 'per_page') or MAX_PAGE_SIZE
    if page < 1 or not 1 <= per_page <= MAX_PAGE_SIZE:
        raise ValidationError(f'Paginação inválida (page >= 1, 1 <= per_page <= {MAX_PAGE_SIZE})')
    return page, per_page
