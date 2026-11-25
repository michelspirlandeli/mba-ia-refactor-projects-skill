"""Validações de entrada reutilizadas pelos controllers (tipos errados → 400, nunca 500)."""
from src.exceptions import ValidationError


def exigir_payload(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def exigir_texto(valor, nome_campo):
    """Texto obrigatório e não vazio."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValidationError(f"{nome_campo} é obrigatório e deve ser texto")
    return valor


def texto_opcional(valor, nome_campo):
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValidationError(f"{nome_campo} deve ser texto")
    return valor


def exigir_numero(valor, nome_campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValidationError(f"{nome_campo} deve ser numérico")
    return valor


def exigir_inteiro(valor, nome_campo):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValidationError(f"{nome_campo} deve ser um número inteiro")
    return valor


def exigir_inteiro_positivo(valor, nome_campo):
    if exigir_inteiro(valor, nome_campo) <= 0:
        raise ValidationError(f"{nome_campo} deve ser um inteiro positivo")
    return valor


def numero_opcional(valor, nome_campo):
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"{nome_campo} inválido")
