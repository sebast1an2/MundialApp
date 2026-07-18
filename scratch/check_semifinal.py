import sqlite3

conn = sqlite3.connect('predicciones.db')
cur = conn.cursor()

# Partidos de Semifinal terminados
cur.execute("""
    SELECT m.id, m.match_label, p.name AS phase, m.is_finished
    FROM matches m
    JOIN phases p ON m.phase_id = p.id
    WHERE LOWER(p.name) = 'semifinal'
    ORDER BY m.id
""")
matches = cur.fetchall()
print("=== Partidos de SEMIFINAL ===")
for r in matches:
    print(r)

# Scores con bonus '+final' que NO son de la fase Final
cur.execute("""
    SELECT s.id, s.participant_id, s.match_id, s.points_earned, s.score_type,
           p.name AS phase_name
    FROM scores s
    JOIN matches m ON s.match_id = m.id
    JOIN phases p ON m.phase_id = p.id
    WHERE s.score_type LIKE '%+final%'
    ORDER BY p.name, s.match_id
""")
scores = cur.fetchall()
print("\n=== Scores con bonus '+final' (por fase) ===")
for r in scores:
    tag = " <<< INCORRECTO" if r[5].lower() != 'final' else ""
    print(r, tag)

conn.close()
