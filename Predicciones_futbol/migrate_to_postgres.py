import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
from app import create_app, db
from app.models import *

# Configuration
SQLITE_URL = 'sqlite:///predicciones.db'
POSTGRES_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg://postgres:PassSecure!@localhost/Predicciones')

def migrate():
    print(f"Iniciando migracion de {SQLITE_URL} a {POSTGRES_URL}...")
    
    # 1. Engines
    sqlite_engine = create_engine(SQLITE_URL)
    postgres_engine = create_engine(POSTGRES_URL)
    
    # 2. Create Schema in Postgres
    print("Creando esquema en PostgreSQL...")
    db.metadata.create_all(postgres_engine)
    
    # 3. Sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()
    
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    
    # 4. Tables in Order (Dependencies first)
    tables = [
        Team,
        Event,
        ScoringConfig,
        Phase,
        Group,
        GroupTeam,
        Match,
        Participant,
        Prediction,
        Score
    ]
    
    try:
        for table in tables:
            table_name = table.__tablename__
            print(f"Migrando tabla: {table_name}...")
            
            # Fetch all from SQLite
            items = sqlite_session.query(table).all()
            print(f"   Encontrados {len(items)} registros.")
            
            # Copy to Postgres
            for item in items:
                # Expunge from sqlite session to avoid conflicts
                sqlite_session.expunge(item)
                # Make transient (remove identity state)
                from sqlalchemy.orm import make_transient
                make_transient(item)
                # Add to postgres
                postgres_session.add(item)
            
            postgres_session.commit()
            print(f"   OK: {table_name} migrada correctamente.")
            
        print("\nMigracion de datos completada con exito.")
        
        # 5. Fix Postgres Sequences (important for Auto-increment)
        print("Ajustando secuencias de IDs en PostgreSQL...")
        with postgres_engine.connect() as conn:
            for table in tables:
                table_name = table.__tablename__
                # SQL to reset sequence to max(id)
                sql = text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1), max(id) IS NOT NULL) FROM {table_name};")
                conn.execute(sql)
                conn.commit()
        print("Secuencias ajustadas.")

    except Exception as e:
        postgres_session.rollback()
        print(f"❌ Error durante la migración: {e}")
        raise e
    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    # Ensure we are in the app context if needed
    app = create_app()
    with app.app_context():
        migrate()
