import sqlite3
import os

db_path = 'predicciones.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Try to add the column
        cursor.execute("ALTER TABLE events ADD COLUMN can_view_others_predictions BOOLEAN DEFAULT 1")
        conn.commit()
        print("Column 'can_view_others_predictions' added successfully to 'events' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'can_view_others_predictions' already exists.")
        else:
            print(f"An error occurred: {e}")
    finally:
        conn.close()
else:
    print(f"Database {db_path} not found.")
