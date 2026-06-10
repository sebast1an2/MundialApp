from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from config import Config
import os
from whitenoise import WhiteNoise
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


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
    csrf.init_app(app)
    limiter.init_app(app)

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

    # Manejo de proxy (ej. Render) para que request.remote_addr y Rate Limiting funcionen correctamente
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app
