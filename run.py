from dotenv import load_dotenv

# Carga el archivo .env si existe (solo tiene efecto en desarrollo local).
# En producción (Render) no existe .env, por lo que esta llamada es inofensiva.
load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
