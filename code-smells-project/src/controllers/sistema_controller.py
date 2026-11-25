"""Casos de uso de sistema: índice, health check e administração.

Não depende do Flask: os valores de configuração chegam por parâmetro (injetados pela view).
"""
import logging

from src.database.connection import limpar_dados
from src.models import pedido_model, produto_model, usuario_model

logger = logging.getLogger(__name__)


def indice(versao):
    return {
        "mensagem": "Bem-vindo à API da Loja",
        "versao": versao,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    }


def health(versao, ambiente):
    # Não expõe segredos, caminho do banco nem flags de debug (antes vazavam aqui).
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produto_model.contar(),
            "usuarios": usuario_model.contar(),
            "pedidos": pedido_model.contar(),
        },
        "versao": versao,
        "ambiente": ambiente,
    }


def resetar_banco():
    limpar_dados()
    logger.warning("Banco de dados resetado via /admin/reset-db")
