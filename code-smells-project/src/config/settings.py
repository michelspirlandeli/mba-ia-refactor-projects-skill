"""Configuração da aplicação: tudo que varia por ambiente vem de variáveis de ambiente."""
import os
import secrets


def _env_bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Segredos: nunca literais no código. Sem SECRET_KEY no ambiente, gera uma chave efêmera (dev).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    # Token para rotas /admin/*. Vazio = rotas admin abertas (comportamento legado, apenas para dev).
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
    APP_ENV = os.environ.get("APP_ENV", "desenvolvimento")
    API_VERSION = "1.0.0"


# --- Regras de domínio (constantes nomeadas, antes "magic numbers") ---
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"

STATUS_PEDIDO_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
STATUS_PEDIDO_INICIAL = "pendente"

TIPO_USUARIO_PADRAO = "cliente"

# Faixas de desconto do relatório de vendas: (faturamento acima de, taxa)
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))
