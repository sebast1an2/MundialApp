import sqlite3
import os

db_path = 'predicciones.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the event ID
cursor.execute("SELECT id, name FROM events WHERE name LIKE '%mundial%'")
events = cursor.fetchall()
print("Events found:", events)

for event_id, event_name in events:
    print(f"\n--- Analysis for Event: {event_name} (ID: {event_id}) ---")
    
    # Get phases
    cursor.execute("SELECT id, name, phase_order FROM phases WHERE event_id = ? ORDER BY phase_order", (event_id,))
    phases = cursor.fetchall()
    print("Phases:", phases)
    
    for p_id, p_name, p_order in phases:
        # Get matches for this phase
        cursor.execute("""
            SELECT m.id, t1.name, t2.name, m.home_score, m.away_score, m.is_finished
            FROM matches m
            JOIN teams t1 ON m.home_team_id = t1.id
            JOIN teams t2 ON m.away_team_id = t2.id
            WHERE m.phase_id = ?
        """, (p_id,))
        matches = cursor.fetchall()
        print(f"  Matches in {p_name} (ID: {p_id}): {matches}")

conn.close()
