from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.sistema_routes import sistema_bp
from src.views.usuario_routes import usuario_bp


def register_routes(app):
    for blueprint in (sistema_bp, produto_bp, usuario_bp, pedido_bp):
        app.register_blueprint(blueprint)
