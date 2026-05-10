import psycopg
try:
    conn = psycopg.connect("host=localhost dbname=Predicciones user=postgres")
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
