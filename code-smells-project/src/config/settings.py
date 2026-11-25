"""Configuração da aplicação: tudo que varia por ambiente vem de variáveis de ambiente."""
import os
import secrets


def _env_bool(name, default="false"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Segredos: nunca literais no código. Sem SECRET_KEY no ambiente, gera uma chave efêmera (dev).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    # Token para rotas /admin/*. Vazio = rotas admin desabilitadas (403). Fail-closed.
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
    # Origens CORS separadas por vírgula. Vazio = CORS desabilitado (mesma origem apenas).
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")
    APP_ENV = os.environ.get("APP_ENV", "desenvolvimento")
    # Dados de demonstração só são criados em ambiente de desenvolvimento.
    # Senhas do seed vêm do ambiente; se ausentes, são geradas aleatoriamente e exibidas no log do boot.
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "")
    SEED_DEMO_PASSWORD = os.environ.get("SEED_DEMO_PASSWORD", "")
    API_VERSION = "1.0.0"


# --- Regras de domínio (constantes nomeadas, antes "magic numbers") ---
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
CATEGORIA_PADRAO = "geral"

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, "enviado", "entregue", STATUS_CANCELADO)
STATUS_PEDIDO_INICIAL = STATUS_PENDENTE

AMBIENTES_DEV = ("desenvolvimento", "development", "dev", "local")

TIPO_USUARIO_PADRAO = "cliente"

# Faixas de desconto do relatório de vendas: (faturamento acima de, taxa)
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))
