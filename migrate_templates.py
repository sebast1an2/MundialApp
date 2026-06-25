"""
Migración: Módulo de Plantillas de Torneo

Ejecutar ANTES de levantar la app con el nuevo código:
    python migrate_templates.py

Crea las 3 nuevas tablas y agrega template_id a events.
Es idempotente: puede ejecutarse varias veces sin daño.
"""

import os
import sys

# Cargar .env si existe (sin depender de python-dotenv)
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL no está definida.")
    sys.exit(1)

# Normalizar prefijo para psycopg3
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Convertir a URL de psycopg puro (sin SQLAlchemy prefix)
raw_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)

try:
    import psycopg
except ImportError:
    print("[ERROR] psycopg no está instalado. Activa el venv y ejecuta: pip install psycopg")
    sys.exit(1)

MIGRATIONS = [
    # 1. Tabla de plantillas
    """
    CREATE TABLE IF NOT EXISTS event_templates (
        id                 SERIAL PRIMARY KEY,
        name               VARCHAR(200) NOT NULL,
        description        TEXT,
        logo_emoji         VARCHAR(10)  DEFAULT '📋',
        is_active          BOOLEAN      DEFAULT TRUE,
        uses_bracket       BOOLEAN      DEFAULT FALSE,
        allows_group_stage BOOLEAN      DEFAULT TRUE,
        allows_knockout    BOOLEAN      DEFAULT TRUE,
        created_at         TIMESTAMP    DEFAULT NOW()
    )
    """,
    # 2. Fases de plantilla
    """
    CREATE TABLE IF NOT EXISTS template_phases (
        id               SERIAL PRIMARY KEY,
        template_id      INTEGER NOT NULL REFERENCES event_templates(id) ON DELETE CASCADE,
        name             VARCHAR(100) NOT NULL,
        phase_order      INTEGER      NOT NULL DEFAULT 1,
        phase_type       VARCHAR(20)  DEFAULT 'group',
        teams_qualify    INTEGER,
        is_bracket_round BOOLEAN      DEFAULT FALSE,
        created_at       TIMESTAMP    DEFAULT NOW()
    )
    """,
    # 3. Scoring de plantilla
    """
    CREATE TABLE IF NOT EXISTS template_scoring_configs (
        id           SERIAL PRIMARY KEY,
        template_id  INTEGER NOT NULL REFERENCES event_templates(id) ON DELETE CASCADE,
        score_type   VARCHAR(30) NOT NULL,
        points_value INTEGER     DEFAULT 0,
        is_active    BOOLEAN     DEFAULT TRUE,
        description  VARCHAR(200),
        UNIQUE (template_id, score_type)
    )
    """,
    # 4. Columna template_id en events (nullable, existentes quedan en NULL)
    """
    ALTER TABLE events
        ADD COLUMN IF NOT EXISTS template_id INTEGER
        REFERENCES event_templates(id) ON DELETE SET NULL
    """,
]

def run():
    print(f"Conectando a la base de datos...")
    try:
        conn = psycopg.connect(raw_url)
    except Exception as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()

    labels = [
        "Crear tabla event_templates",
        "Crear tabla template_phases",
        "Crear tabla template_scoring_configs",
        "Agregar columna events.template_id",
    ]

    print()
    for i, (sql, label) in enumerate(zip(MIGRATIONS, labels), 1):
        try:
            cur.execute(sql)
            print(f"  [{i}/{len(MIGRATIONS)}] OK — {label}")
        except Exception as e:
            print(f"  [{i}/{len(MIGRATIONS)}] ERROR — {label}: {e}")
            conn.close()
            sys.exit(1)

    cur.close()
    conn.close()
    print("\nMigración completada exitosamente.")
    print("Ya puedes ejecutar: python run.py\n")

if __name__ == '__main__':
    run()
