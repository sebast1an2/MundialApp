import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'polla-mundialera-2026-super-secret-key')
    
    # Database URL configuration
    db_url = os.environ.get('DATABASE_URL', 'postgresql+psycopg://predict:Predict123@localhost:5433/Predicciones')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    SQLALCHEMY_DATABASE_URI = db_url or ('sqlite:///' + os.path.join(basedir, 'predicciones.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin credentials (change in production via env vars)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin2026')
