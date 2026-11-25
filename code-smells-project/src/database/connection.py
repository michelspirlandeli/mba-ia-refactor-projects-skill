"""Conexão SQLite por request (flask.g), criação de schema, seed de desenvolvimento e reset."""
import logging
import secrets
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

from src.config.settings import AMBIENTES_DEV, STATUS_PEDIDO_INICIAL, TIPO_USUARIO_PADRAO

logger = logging.getLogger(__name__)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    descricao TEXT,
    preco REAL,
    estoque INTEGER,
    categoria TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    email TEXT,
    senha TEXT,
    tipo TEXT DEFAULT '{TIPO_USUARIO_PADRAO}',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    status TEXT DEFAULT '{STATUS_PEDIDO_INICIAL}',
    total REAL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER,
    produto_id INTEGER,
    quantidade INTEGER,
    preco_unitario REAL
);
"""

# Garante email único também em bancos já existentes (criado à parte para tolerar duplicatas legadas).
INDICE_EMAIL_UNICO = "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)"

PRODUTOS_SEED = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Usuários de demonstração: (nome, email, tipo). Senhas vêm do ambiente (ver Config.SEED_*_PASSWORD).
ADMIN_SEED = ("Admin", "admin@loja.com", "admin")
CLIENTES_SEED = [
    ("João Silva", "joao@email.com", TIPO_USUARIO_PADRAO),
    ("Maria Santos", "maria@email.com", TIPO_USUARIO_PADRAO),
]


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    """Retorna a conexão do request atual (uma por request, fechada no teardown)."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _senha_seed(configurada, rotulo):
    if configurada:
        return configurada
    gerada = secrets.token_urlsafe(12)
    logger.warning("Seed de desenvolvimento: senha gerada para %s = %s (defina no .env para fixar)", rotulo, gerada)
    return gerada


def _seed_desenvolvimento(conn, config):
    conn.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        PRODUTOS_SEED,
    )
    senha_admin = _senha_seed(config["SEED_ADMIN_PASSWORD"], ADMIN_SEED[1])
    senha_demo = _senha_seed(config["SEED_DEMO_PASSWORD"], "clientes de demonstração")
    usuarios = [(*ADMIN_SEED[:2], generate_password_hash(senha_admin), ADMIN_SEED[2])]
    usuarios += [(nome, email, generate_password_hash(senha_demo), tipo) for nome, email, tipo in CLIENTES_SEED]
    conn.executemany("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)", usuarios)


def init_db(app):
    """Cria o schema e, só em desenvolvimento, popula dados de demonstração se o banco estiver vazio."""
    conn = _connect(app.config["DATABASE_PATH"])
    try:
        with conn:
            conn.executescript(SCHEMA)
            try:
                conn.execute(INDICE_EMAIL_UNICO)
            except sqlite3.IntegrityError:
                logger.warning("Há emails duplicados no banco; índice único não criado (unicidade só no controller)")
            vazio = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0
            if vazio and app.config["APP_ENV"] in AMBIENTES_DEV:
                _seed_desenvolvimento(conn, app.config)
    finally:
        conn.close()
    app.teardown_appcontext(close_db)


def limpar_dados():
    """Remove todos os registros de todas as tabelas (usado por /admin/reset-db)."""
    db = get_db()
    with db:
        for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
            db.execute(f"DELETE FROM {tabela}")  # nomes fixos, sem entrada do usuário
