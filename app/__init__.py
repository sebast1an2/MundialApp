from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
from whitenoise import WhiteNoise

db = SQLAlchemy()


def format_currency(value):
    """Jinja2 filter: formats an integer as currency with thousands separator."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Register custom Jinja2 filters
    app.jinja_env.filters['format_currency'] = format_currency

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    with app.app_context():
        db.create_all()

    # Configurar WhiteNoise para servir archivos estáticos de forma eficiente en producción
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(app.root_path, 'static'), prefix='static/')

    return app
