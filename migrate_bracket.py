"""
Migración: Infraestructura de Bracket Eliminatorio

Ejecutar ANTES de levantar la app con el nuevo código:
    python migrate_bracket.py

Cambios en la tabla matches:
  1-2. home_team_id / away_team_id → nullable  (DROP NOT NULL)
  3.   home_source_match_id  INTEGER REFERENCES matches(id)
  4.   away_source_match_id  INTEGER REFERENCES matches(id)
  5.   home_source_outcome   VARCHAR(10) DEFAULT 'winner'
  6.   away_source_outcome   VARCHAR(10) DEFAULT 'winner'
  7.   bracket_position      INTEGER

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

raw_url = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)

try:
    import psycopg
except ImportError:
    print("[ERROR] psycopg no está instalado. Activa el venv y ejecuta: pip install psycopg")
    sys.exit(1)

MIGRATIONS = [
    # 1. home_team_id nullable (ya existente como NOT NULL — DROP CONSTRAINT)
    (
        "home_team_id nullable",
        "ALTER TABLE matches ALTER COLUMN home_team_id DROP NOT NULL",
    ),
    # 2. away_team_id nullable
    (
        "away_team_id nullable",
        "ALTER TABLE matches ALTER COLUMN away_team_id DROP NOT NULL",
    ),
    # 3. Referencia al partido de origen del equipo local
    (
        "ADD home_source_match_id",
        """ALTER TABLE matches
           ADD COLUMN IF NOT EXISTS home_source_match_id INTEGER
           REFERENCES matches(id) ON DELETE SET NULL""",
    ),
    # 4. Referencia al partido de origen del equipo visitante
    (
        "ADD away_source_match_id",
        """ALTER TABLE matches
           ADD COLUMN IF NOT EXISTS away_source_match_id INTEGER
           REFERENCES matches(id) ON DELETE SET NULL""",
    ),
    # 5. Resultado esperado del partido de origen (local)
    (
        "ADD home_source_outcome",
        """ALTER TABLE matches
           ADD COLUMN IF NOT EXISTS home_source_outcome VARCHAR(10) DEFAULT 'winner'""",
    ),
    # 6. Resultado esperado del partido de origen (visitante)
    (
        "ADD away_source_outcome",
        """ALTER TABLE matches
           ADD COLUMN IF NOT EXISTS away_source_outcome VARCHAR(10) DEFAULT 'winner'""",
    ),
    # 7. Posición en el bracket para ordenar visualmente
    (
        "ADD bracket_position",
        """ALTER TABLE matches
           ADD COLUMN IF NOT EXISTS bracket_position INTEGER""",
    ),
]


def column_is_nullable(cur, column):
    """Devuelve True si la columna en matches ya es nullable."""
    cur.execute(
        """SELECT is_nullable FROM information_schema.columns
           WHERE table_name = 'matches' AND column_name = %s""",
        (column,),
    )
    row = cur.fetchone()
    return row and row[0] == 'YES'


def run():
    print("Conectando a la base de datos...")
    try:
        conn = psycopg.connect(raw_url)
    except Exception as e:
        print(f"[ERROR] No se pudo conectar: {e}")
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()

    print()
    total = len(MIGRATIONS)
    for i, (label, sql) in enumerate(MIGRATIONS, 1):
        # Las sentencias DROP NOT NULL fallan si la columna ya es nullable;
        # detectamos eso y las saltamos.
        if 'DROP NOT NULL' in sql:
            col = 'home_team_id' if 'home_team_id' in sql else 'away_team_id'
            if column_is_nullable(cur, col):
                print(f"  [{i}/{total}] SKIP — {label} (ya es nullable)")
                continue

        try:
            cur.execute(sql)
            print(f"  [{i}/{total}] OK   — {label}")
        except Exception as e:
            print(f"  [{i}/{total}] ERROR — {label}: {e}")
            conn.close()
            sys.exit(1)

    cur.close()
    conn.close()
    print("\nMigración de bracket completada exitosamente.")
    print("Ya puedes ejecutar: python run.py\n")


if __name__ == '__main__':
    run()
