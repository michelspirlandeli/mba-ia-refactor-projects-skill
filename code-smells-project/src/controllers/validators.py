"""Validações de entrada reutilizadas pelos controllers."""
from src.middlewares.error_handler import ValidationError


def exigir_payload(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def exigir_numero(valor, nome_campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(f"{nome_campo} deve ser numérico")
    return valor


def exigir_inteiro_positivo(valor, nome_campo):
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValidationError(f"{nome_campo} deve ser um inteiro positivo")
    return valor


def numero_opcional(valor, nome_campo):
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"{nome_campo} inválido")
