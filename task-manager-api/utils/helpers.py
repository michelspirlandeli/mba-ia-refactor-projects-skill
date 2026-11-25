"""Funções utilitárias puras (sem dependência de Flask/banco)."""
import re
from datetime import datetime, timezone

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
COLOR_REGEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def utcnow():
    """UTC "naive" (compatível com as colunas DateTime existentes) sem usar o deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def is_valid_email(email):
    return isinstance(email, str) and bool(EMAIL_REGEX.match(email))


def is_valid_color(color):
    return isinstance(color, str) and bool(COLOR_REGEX.match(color))


def parse_date(value, fmt):
    try:
        return datetime.strptime(value, fmt)
    except (TypeError, ValueError):
        return None
