"""Casos de uso de usuários e autenticação."""
import hmac
import logging
import re

from werkzeug.security import check_password_hash, generate_password_hash

from src.config.settings import TIPO_USUARIO_PADRAO
from src.controllers.validators import exigir_payload, exigir_texto
from src.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from src.models import usuario_model

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Prefixos dos hashes gerados por werkzeug (scrypt/pbkdf2).
HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def listar():
    return usuario_model.listar()


def obter(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados):
    exigir_payload(dados)
    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    exigir_texto(nome, "Nome")
    exigir_texto(senha, "Senha")
    if not isinstance(email, str) or not EMAIL_REGEX.match(email):
        raise ValidationError("Email inválido")
    if usuario_model.email_existe(email):
        raise ConflictError("Email já cadastrado")

    try:
        usuario_id = usuario_model.criar(nome, email, generate_password_hash(senha), TIPO_USUARIO_PADRAO)
    except usuario_model.EmailDuplicado:
        raise ConflictError("Email já cadastrado")  # corrida entre duas requisições simultâneas
    logger.info("Usuário criado id=%s", usuario_id)
    return usuario_id


def _senha_confere(usuario, senha):
    armazenada = usuario["senha"] or ""
    if armazenada.startswith(HASH_PREFIXES):
        return check_password_hash(armazenada, senha)
    # Bancos legados guardavam a senha em texto puro: valida uma vez e migra para hash.
    if hmac.compare_digest(armazenada, senha):
        usuario_model.atualizar_senha(usuario["id"], generate_password_hash(senha))
        return True
    return False


def autenticar(dados):
    exigir_payload(dados)
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    if not isinstance(email, str) or not isinstance(senha, str):
        raise UnauthorizedError("Email ou senha inválidos")

    usuario = usuario_model.buscar_credenciais_por_email(email)
    if not usuario or not _senha_confere(usuario, senha):
        logger.info("Falha de login")
        raise UnauthorizedError("Email ou senha inválidos")

    logger.info("Login bem-sucedido usuario_id=%s", usuario["id"])
    return {"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"], "tipo": usuario["tipo"]}
