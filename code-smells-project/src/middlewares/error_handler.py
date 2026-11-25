"""Tratamento de erros centralizado: exceções de domínio → JSON padronizado."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.exceptions import AppError

logger = logging.getLogger(__name__)


def _error_response(message, status_code):
    return jsonify({"erro": message, "sucesso": False}), status_code


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return _error_response(err.message, err.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return _error_response(err.description or err.name, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro não tratado: %s", err)
        return _error_response("Erro interno do servidor", 500)
