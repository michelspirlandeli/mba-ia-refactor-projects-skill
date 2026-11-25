"""Acesso a dados de usuários. A senha (hash) nunca sai deste módulo nas consultas públicas."""
import sqlite3

from src.database.connection import get_db

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")


class EmailDuplicado(Exception):
    pass


def _to_public_dict(row):
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def listar():
    rows = get_db().execute("SELECT * FROM usuarios").fetchall()
    return [_to_public_dict(r) for r in rows]


def buscar_por_id(usuario_id):
    row = get_db().execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return _to_public_dict(row) if row else None


def buscar_credenciais_por_email(email):
    """Retorna a linha completa (inclui hash da senha) — uso exclusivo da autenticação."""
    return get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()


def existe(usuario_id):
    return get_db().execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is not None


def email_existe(email):
    return get_db().execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone() is not None


def criar(nome, email, senha_hash, tipo):
    db = get_db()
    try:
        with db:
            cursor = db.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, senha_hash, tipo),
            )
    except sqlite3.IntegrityError as exc:  # índice único idx_usuarios_email
        raise EmailDuplicado(email) from exc
    return cursor.lastrowid


def atualizar_senha(usuario_id, senha_hash):
    db = get_db()
    with db:
        db.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (senha_hash, usuario_id))


def contar():
    return get_db().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
