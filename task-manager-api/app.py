"""Entry point e composition root (application factory)."""
import logging

from flask import Flask
from flask_cors import CORS

from config import Config
from database import db
from middlewares.auth import register_auth
from middlewares.error_handler import register_error_handlers
from routes import register_routes


def create_app(config_object=Config):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app = Flask(__name__)
    app.config.from_object(config_object)

    CORS(app, origins=app.config['CORS_ORIGINS'])
    db.init_app(app)
    register_auth(app)
    register_routes(app)
    register_error_handlers(app)

    with app.app_context():
        import models  # noqa: F401  (registra as tabelas no metadata)
        db.create_all()

    return app


if __name__ == '__main__':
    application = create_app()
    application.run(host=application.config['HOST'], port=application.config['PORT'],
                    debug=application.config['DEBUG'])
