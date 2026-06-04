# ⚽ Predicciones Fútbol — Sistema de Polla Mundialera

Un sistema profesional y dinámico de predicciones de fútbol (Polla/Quiniela) construido con **Flask**, **SQLite** y **Bootstrap 5**. Diseñado para gestionar torneos complejos, desde fases de grupos hasta finales eliminatorias, con un sistema de puntuación automatizado y una interfaz premium.

## 🚀 Características Principales

### 👤 Experiencia del Participante (Pública)
*   **Validación por Cédula:** Acceso seguro sin necesidad de contraseñas complejas, permitiendo a los usuarios entrar solo con su identificación.
*   **Gestión de Predicciones:** Interfaz intuitiva para predecir marcadores en tiempo real para las fases activas.
*   **Ranking Dinámico:** Tabla de posiciones actualizada al instante según los resultados reales cargados.
*   **Visualización de Otros:** Opción (configurable por el administrador) para ver las predicciones de otros participantes una vez cerrada la fase.

### 🛠 Panel Administrativo
*   **Gestión Integral de Eventos:** Creación y edición de torneos con soporte para múltiples tipos (Mundial, Champions, Ligas).
*   **Control de Fases:** Apertura y cierre manual de periodos de predicción.
*   **Lógica de Avance Inteligente:** El sistema filtra automáticamente los equipos para fases eliminatorias basados en resultados previos (Clasificados de grupos y ganadores de llaves).
*   **Soporte de Penales:** Gestión completa de desempates en fases eliminatorias.
*   **Configuración de Puntos:** Sistema flexible para asignar puntos por marcador exacto o acierto de ganador.
*   **Modales Premium:** Confirmaciones de acciones críticas mediante una interfaz personalizada para evitar errores accidentales.

## 💻 Tech Stack

*   **Backend:** Python 3.x + Flask
*   **Base de Datos:** SQLite + SQLAlchemy (ORM)
*   **Frontend:** HTML5, CSS3 (Vanilla + Custom Properties), JavaScript (Vanilla)
*   **UI Framework:** Bootstrap 5.3 + Bootstrap Icons
*   **Fuentes:** Google Fonts (Inter, Outfit)

## 📂 Estructura del Proyecto

```text
├── app/
│   ├── models.py          # Definición de modelos SQLAlchemy (Event, Match, Prediction, etc.)
│   ├── routes/            # Blueprints (admin.py, public.py, auth.py)
│   ├── services/          # Lógica de negocio (standings.py, scoring.py, seeder.py)
│   ├── static/            # Recursos estáticos (css/custom.css, js/app.js)
│   └── templates/         # Plantillas Jinja2 organizadas por módulos
├── instance/              # Instancia local (configuraciones sensibles)
├── predicciones.db        # Base de Datos SQLite
├── run.py                 # Punto de entrada de la aplicación
├── config.py              # Configuraciones globales de Flask
└── README.md              # Documentación técnica
```

## ⚙️ Configuración e Instalación

### 1. Requisitos Previos
*   Python 3.8 o superior instalado.

### 2. Instalación de Dependencias
```bash
pip install flask flask-sqlalchemy
```

### 3. Ejecución en Desarrollo
```bash
python run.py
```
La aplicación estará disponible en `http://127.0.0.1:5000`.

### 4. Credenciales de Administrador
Por defecto (configurables en `config.py`):
*   **Usuario:** `admin`
*   **Contraseña:** `admin2026`

## 🧠 Lógica de Puntuación

El sistema calcula puntos automáticamente cada vez que se guarda un resultado real:
1.  **Marcador Exacto:** Puntos máximos si el usuario predijo los goles exactos de ambos equipos.
2.  **Ganador/Empate:** Puntos parciales si el usuario acertó el resultado (ej. ganó Local) pero no el marcador exacto.
3.  **Sin Acierto:** 0 puntos.

*Nota: Los valores de puntos son editables por el administrador en la sección "Puntuación" de cada evento.*

## 🛠 Mejoras Técnicas Recientes

*   **Centralización de Confirmaciones:** Implementación de un sistema global de modales Bootstrap para todas las acciones de eliminación, eliminando la dependencia de `window.confirm()`.
*   **Avance Dinámico (Brackets):** Refactorización del módulo de creación de partidos para filtrar equipos clasificados automáticamente, reduciendo errores administrativos.
*   **Manejo de Empates en Knockout:** Adición de campo `penalty_winner_id` para gestionar desempates en fases eliminatorias.
*   **Optimización SEO:** Implementación de Meta Tags descriptivos, estructura semántica de encabezados y títulos dinámicos por página.

---
**Desarrollado por Antigravity AI**
*Documentación generada el 10 de Mayo de 2026.*
