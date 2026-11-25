"""Casos de uso de sistema: índice, health check e administração."""
import logging

from flask import current_app

from src.models import pedido_model, produto_model, usuario_model

logger = logging.getLogger(__name__)


def indice():
    return {
        "mensagem": "Bem-vindo à API da Loja",
        "versao": current_app.config["API_VERSION"],
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    }


def health():
    # Não expõe segredos, caminho do banco nem flags de debug (antes vazavam aqui).
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produto_model.contar(),
            "usuarios": usuario_model.contar(),
            "pedidos": pedido_model.contar(),
        },
        "versao": current_app.config["API_VERSION"],
        "ambiente": current_app.config["APP_ENV"],
    }


def resetar_banco():
    pedido_model.limpar_tudo()
    logger.warning("Banco de dados resetado via /admin/reset-db")
