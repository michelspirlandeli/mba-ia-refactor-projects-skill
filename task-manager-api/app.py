"""Entry point e composition root (application factory)."""
import logging

from flask import Flask
from flask_cors import CORS

from config import Config
from database import db
from middlewares.auth import register_auth
from middlewares.error_handler import register_error_handlers
from routes import register_routes
from services.auth_service import LoginThrottle, TokenService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _register_services(app):
    """Instâncias únicas por aplicação, injetadas nas views/controllers via app.extensions."""
    app.extensions['token_service'] = TokenService(app.config['SECRET_KEY'], app.config['TOKEN_MAX_AGE_SECONDS'])
    app.extensions['login_throttle'] = LoginThrottle(app.config['LOGIN_MAX_FAILURES'],
                                                     app.config['LOGIN_WINDOW_SECONDS'])
    app.extensions['notification_service'] = NotificationService.from_config(app.config)


def create_app(config_object=Config):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    app = Flask(__name__)
    app.config.from_object(config_object)

    origins = [origin.strip() for origin in app.config['CORS_ORIGINS'].split(',') if origin.strip()]
    if origins:
        CORS(app, origins=origins)
    db.init_app(app)
    _register_services(app)
    register_auth(app)
    register_routes(app)
    register_error_handlers(app)

    with app.app_context():
        import models  # noqa: F401  (registra as tabelas no metadata)
        db.create_all()

    if not app.config['AUTH_REQUIRED']:
        logger.warning('AUTH_REQUIRED=false: autenticação e autorização DESLIGADAS (use apenas em desenvolvimento)')
    return app


if __name__ == '__main__':
    application = create_app()
    application.run(host=application.config['HOST'], port=application.config['PORT'],
                    debug=application.config['DEBUG'])
