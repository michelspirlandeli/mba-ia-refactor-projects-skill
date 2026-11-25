"""Composition root: monta a aplicação a partir de config, banco, rotas e middlewares."""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Config
from src.database.connection import init_db
from src.middlewares.error_handler import register_error_handlers
from src.views import register_routes


def create_app(config_object=Config):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    init_db(app)
    register_routes(app)
    register_error_handlers(app)
    return app
