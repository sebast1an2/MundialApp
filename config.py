import os
import sys

basedir = os.path.abspath(os.path.dirname(__file__))


def _require_env(name: str) -> str:
    """
    Lee una variable de entorno obligatoria.
    Si no está definida, termina la aplicación con un mensaje claro
    en lugar de arrancar con credenciales inseguras por defecto.
    """
    value = os.environ.get(name)
    if not value:
        print(
            f"\n[CONFIG ERROR] La variable de entorno '{name}' no está definida.\n"
            f"  → Configúrala en Render (Environment > Add Environment Variable)\n"
            f"  → Consulta el archivo .env.example para la lista completa.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


class Config:
    # ── Seguridad de sesión ────────────────────────────────────────────────────
    # Obligatoria: genera una clave aleatoria segura con:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY = _require_env('SECRET_KEY')

    # ── Base de datos ──────────────────────────────────────────────────────────
    # Obligatoria: URL de conexión PostgreSQL completa
    # Formato: postgresql+psycopg://user:password@host:port/dbname
    # En Render/Supabase se obtiene del panel de la base de datos.
    _db_url = _require_env('DATABASE_URL')

    # Normalizar el prefijo para compatibilidad con psycopg3
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif _db_url.startswith("postgresql://") and not _db_url.startswith("postgresql+psycopg://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Credenciales del panel administrador ──────────────────────────────────
    # Obligatorias: definir en Render como variables de entorno seguras.
    ADMIN_USERNAME = _require_env('ADMIN_USERNAME')
    ADMIN_PASSWORD = _require_env('ADMIN_PASSWORD')
