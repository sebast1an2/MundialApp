# Manual Técnico - Polla Mundialera 2026

Este documento proporciona una descripción general de la arquitectura, configuración y funcionamiento interno de la aplicación web "Polla Mundialera 2026".

## 1. Stack Tecnológico

La aplicación está construida utilizando un stack moderno basado en Python para el backend y tecnologías web estándar para el frontend.

*   **Backend:** Python 3.x
*   **Framework Web:** Flask 3.0.3
*   **ORM (Manejo de Base de Datos):** SQLAlchemy 2.0.49 (vía Flask-SQLAlchemy)
*   **Base de Datos:** SQLite (Desarrollo) / PostgreSQL (Producción, vía `psycopg` 3.x)
*   **Frontend:** HTML5, CSS3 (Custom + Variables), JavaScript (Vanilla)
*   **Framework UI:** Bootstrap 5.3.3 (vía CDN)
*   **Servidor WSGI:** Gunicorn (Producción)
*   **Archivos Estáticos:** WhiteNoise (optimización y caché estáticos en producción)
*   **Motor de Plantillas:** Jinja2

---

## 2. Arquitectura y Estructura del Proyecto

El proyecto sigue el patrón arquitectónico **MVC (Model-View-Controller)** adaptado al ecosistema de Flask mediante *Blueprints*.

```text
c:\Antigravity\Predicciones\
├── app/
│   ├── __init__.py          # Inicialización de la app (App Factory) y configuración
│   ├── models.py            # Modelos de SQLAlchemy (Base de datos)
│   ├── routes/              # Controladores (Blueprints)
│   │   ├── admin.py         # Rutas protegidas del panel administrativo
│   │   ├── auth.py          # Autenticación del administrador
│   │   └── public.py        # Rutas públicas y de participantes
│   ├── services/            # Lógica de negocio encapsulada
│   │   └── standings.py     # Cálculos complejos (Ranking, Tablas de grupos)
│   ├── static/              # Archivos estáticos (CSS, JS, Imágenes)
│   └── templates/           # Plantillas HTML (Jinja2)
│       ├── admin/           # Vistas del administrador
│       ├── auth/            # Vista de login
│       └── public/          # Vistas públicas (Evento, Predicciones, Ranking)
├── config.py                # Variables de configuración por entorno
├── requirements.txt         # Dependencias del proyecto
└── run.py                   # Script de arranque del servidor de desarrollo
```

---

## 3. Modelos de Base de Datos (Relaciones)

El esquema de base de datos está diseñado para ser relacional y garantizar la integridad de los datos de los torneos.

> [!NOTE]
> Todos los modelos heredan de `db.Model` de SQLAlchemy.

*   **`Team`**: Catálogo global de equipos (clubes o selecciones). Independiente de los eventos.
*   **`Event`**: Representa un torneo específico (ej. "Mundial 2026 Empresas"). Contiene configuración financiera (`participation_fee`, `prize_first`, `nequi_number`).
*   **`Group` & `GroupTeam`**: Define los grupos dentro de un evento (A, B, C...) y los equipos que pertenecen a cada uno, incluyendo el orden de siembra.
*   **`Phase`**: Etapas del torneo (Grupos, Octavos, Cuartos). Controla la apertura y cierre de predicciones mediante flags booleanos (`is_prediction_open`).
*   **`Match`**: Partidos específicos entre dos `Team` asociados a una `Phase`. Almacena el resultado real.
*   **`Participant`**: Usuarios inscritos en un `Event`. Se identifican por `cedula`. Almacena el estado financiero (`payment_confirmed`).
*   **`Prediction`**: El pronóstico de un `Participant` para un `Match` específico.
*   **`Score`**: Registro de puntos ganados por un `Participant` en un `Match` (Calculado tras finalizar el partido).
*   **`ScoringConfig`**: Reglas de puntuación dinámicas por evento (Puntos por marcador exacto, ganador, etc.).

---

## 4. Flujos Principales y Lógica de Negocio

### 4.1. Autenticación y Autorización
*   **Administrador**: Validado contra variables de entorno/configuración global (`ADMIN_USERNAME`, `ADMIN_PASSWORD`). Mantiene el estado en una sesión de servidor cifrada (`session['is_admin']`). Rutas protegidas con el decorador `@require_admin`.
*   **Participantes**: "Soft-login" basado en la cédula. Se valida la existencia en la base de datos y se almacena `participant_event_{event_id}` en la sesión.

### 4.2. Motor de Puntuación
La asignación de puntos se dispara manualmente desde el panel de administrador ("Calcular Puntos").
1.  Itera sobre todos los `Match` finalizados en una fase.
2.  Compara `home_score` y `away_score` reales contra los pronósticos en la tabla `Prediction`.
3.  Asigna puntos basándose en `ScoringConfig` (Ej: 3 puntos por marcador exacto, 1 punto por atinar el ganador).
4.  Genera registros en la tabla `Score` y actualiza el `total_points` del `Participant`.

### 4.3. Restricciones de Predicción
Un participante solo puede enviar o modificar predicciones si la fase correspondiente tiene `is_prediction_open == True`. Una vez el administrador cierra la fase, el formulario de predicción se bloquea.

---

## 5. Decisiones de Diseño y Optimizaciones

*   **Optimización de Consultas**: Las vistas críticas (como el Dashboard de Admin y el Ranking Público) utilizan *Eager Loading* para evitar el problema de consultas N+1 en SQLAlchemy.
*   **Gestión de Estáticos**: Implementación de `WhiteNoise` en `__init__.py`. Esto permite que la aplicación sirva sus propios archivos estáticos eficientemente en producción sin requerir un Nginx proxy inverso (ideal para despliegues en PaaS como Heroku o Render).
*   **Mobile-First Degradation**: La UI usa Bootstrap 5 con clases utilitarias (`d-lg-none`, `d-none d-lg-block`) para reorganizar jerárquicamente la información en móviles (priorizando el ranking) sin renderizar DOM innecesario.
*   **Protección de Cascada (Cascade Deletes)**: Configurada a nivel de SQLAlchemy. Eliminar un participante borra automáticamente sus predicciones y scores. Eliminar un evento borra absolutamente todo su ecosistema.

---

## 6. Variables de Entorno (Configuración)

Para desplegar la aplicación, el entorno debe proveer las siguientes variables (definidas en `config.py`):

| Variable | Descripción | Default (Dev) |
| :--- | :--- | :--- |
| `FLASK_APP` | Punto de entrada de la app | `run.py` |
| `SECRET_KEY` | Semilla para firmar las cookies de sesión | `'dev-secret-key-123'` |
| `DATABASE_URL` | String de conexión a la BD (PostgreSQL/SQLite) | `sqlite:///app.db` |
| `ADMIN_USERNAME` | Usuario del panel administrativo | `'admin'` |
| `ADMIN_PASSWORD` | Contraseña del panel administrativo | `'admin123'` |

> [!WARNING]
> En producción, `SECRET_KEY`, `ADMIN_USERNAME` y `ADMIN_PASSWORD` **deben** ser variables de entorno seguras y únicas, nunca expuestas en el código fuente.

---

## 7. Comandos Frecuentes de Mantenimiento

*   **Arrancar en desarrollo**:
    ```bash
    python run.py
    ```
*   **Arrancar en producción (Gunicorn)**:
    ```bash
    gunicorn "app:create_app()" -w 4 -b 0.0.0.0:8000
    ```
*   **Generar base de datos limpia**:
    La aplicación detecta automáticamente la ausencia de tablas y ejecuta `db.create_all()` al arrancar en el contexto de la aplicación.
