"""Rotas de sistema: índice, health check e administração."""
from flask import Blueprint, current_app, jsonify

from src.controllers import sistema_controller
from src.middlewares.auth import require_admin

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify(sistema_controller.indice(current_app.config["API_VERSION"]))


@sistema_bp.get("/health")
def health_check():
    return jsonify(sistema_controller.health(current_app.config["API_VERSION"], current_app.config["APP_ENV"])), 200


@sistema_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    sistema_controller.resetar_banco()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200

# POST /admin/query (execução de SQL arbitrário) foi removido intencionalmente — ver audit-project-1 #3.
