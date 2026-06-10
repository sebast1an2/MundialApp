# ⚽ MundialApp — Sistema de Predicciones de Fútbol

Una aplicación web profesional de tipo **polla/quiniela** construida con **Flask** y **PostgreSQL**, diseñada para gestionar torneos de fútbol completos: desde la fase de grupos hasta las rondas eliminatorias, con puntuación automática, ranking en tiempo real e interfaz premium.

> Actualmente en producción para el **Mundial 2026** (12 grupos, 48 equipos, 104 partidos).

---

## 🚀 Características Principales

### 👤 Experiencia del Participante (Pública)

| Funcionalidad | Descripción |
|---|---|
| **Validación por Cédula** | Acceso sin contraseña usando solo la cédula de identidad. Flujo de 3 pasos: verificar → registrar (si es nuevo) → acceder |
| **Predicciones por Fase** | Formulario para ingresar marcadores (goles local y visitante) de todos los partidos de la fase activa, de una sola vez |
| **Predicciones inmutables** | Una vez enviadas, las predicciones no pueden modificarse para garantizar integridad |
| **Ranking Público** | Tabla de posiciones ordenada por puntos, con posición personal resaltada |
| **Mis Predicciones** | Vista detallada por fase con resultado real, predicción y puntos obtenidos por partido |
| **Tabla de Grupos** | Standings en tiempo real (PJ, PG, PE, PP, GF, GC, DIF, PTS) calculados desde los resultados reales |
| **Top Goleadores** | Equipos con más goles anotados en el torneo (entre todos los partidos finalizados) |
| **Control de visibilidad** | El administrador puede activar/desactivar la opción de ver predicciones de otros participantes |

### 🛠 Panel Administrativo (`/admin`)

| Sección | Funcionalidad |
|---|---|
| **Dashboard** | Resumen global: eventos activos, equipos, participantes, predicciones totales y últimos resultados |
| **Equipos** | CRUD completo. Filtro por tipo (selección / club). Carga masiva automática con `Seed` |
| **Eventos** | Creación de torneos (Mundial, Copa América, Champions, Custom). Estado: `draft` → `active` → `finished` |
| **Grupos** | Asignación de equipos por grupo con validación de duplicados entre grupos. Generación automática de fixture por grupo |
| **Fases** | Control manual de apertura/cierre de predicciones por fase. Soporte multi-fase con orden configurable |
| **Partidos** | Creación manual de partidos con filtrado inteligente de equipos según la fase (grupos o eliminatoria) |
| **Resultados** | Ingreso del marcador real. Soporte de penales (`penalty_winner_id`) para eliminatorias. Bloqueo si la fase de predicciones sigue abierta |
| **Puntuación** | Configuración de puntos por evento (marcador exacto, ganador correcto). Recalculación global al guardar |
| **Participantes** | Lista ordenada por puntos. Vista de detalle con historial de predicciones por fase |
| **Ranking Admin** | Vista administrativa del ranking final del torneo |

---

## 🧠 Lógica de Puntuación

El sistema calcula puntos automáticamente cada vez que se guarda un resultado:

1. **Marcador Exacto** → Puntos máximos (default: **3 pts**). El usuario predijo exactamente `X-Y`.
2. **Ganador/Empate correcto** → Puntos parciales (default: **1 pt**). Acertó el resultado (local gana, empate, visitante gana) pero no el marcador exacto.
3. **Sin acierto** → **0 pts**.

> Los valores son **configurables por evento** desde el panel admin. Un cambio en la config dispara una recalculación automática de todos los scores del evento.

### Lógica de Penales

En fases eliminatorias, si el marcador en 90 min está empatado, se registra un `penalty_winner_id`. El método `Match.get_result()` resuelve el ganador usando este campo, afectando el cálculo de puntos de las predicciones.

---

## 🏗 Arquitectura & Tech Stack

```
Backend:    Python 3.x + Flask 3.0.3
ORM:        SQLAlchemy 2.0 (Flask-SQLAlchemy 3.1)
Base de datos: PostgreSQL (psycopg 3) — fallback SQLite en local
Frontend:   HTML5 + CSS Vanilla (custom.css) + JavaScript Vanilla
UI:         Bootstrap 5.3 + Bootstrap Icons
Fuentes:    Google Fonts (Inter, Outfit)
Estáticos:  WhiteNoise (producción)
Servidor:   Gunicorn (producción)
```

---

## 📂 Estructura del Proyecto

```text
Predicciones/
├── app/
│   ├── __init__.py            # Factory function, registro de Blueprints, WhiteNoise
│   ├── models.py              # Modelos SQLAlchemy (Team, Event, Group, Phase, Match,
│   │                          #   Participant, Prediction, Score, ScoringConfig)
│   ├── routes/
│   │   ├── admin.py           # Blueprint /admin — CRUD completo (730 líneas)
│   │   ├── auth.py            # Blueprint auth — login/logout admin, decorador require_admin
│   │   └── public.py          # Blueprint público — participantes, predicciones, ranking
│   ├── services/
│   │   ├── scoring.py         # Cálculo y upsert de puntos por partido y evento
│   │   ├── standings.py       # Tabla de grupos en tiempo real + top goleadores
│   │   └── seeder.py          # Catálogo inicial: ~90 selecciones + ~30 clubes
│   ├── static/
│   │   ├── css/custom.css     # Hoja de estilos completa (~19 KB)
│   │   └── js/app.js          # Lógica JS: modales de confirmación, validaciones
│   └── templates/
│       ├── base.html           # Layout público
│       ├── admin_base.html     # Layout admin
│       ├── admin/              # 15 templates de administración
│       ├── auth/               # login.html
│       └── public/             # 8 templates públicos
├── config.py                  # Config Flask: SECRET_KEY, DB URL, credenciales admin
├── run.py                     # Punto de entrada (Flask dev server)
├── migrate_to_postgres.py     # Script de migración SQLite → PostgreSQL
├── update_matches_v2.py       # Utilidad: carga y actualiza fechas del fixture del Mundial 2026
├── seed_matches.py            # Utilidad: siembra de partidos de fase de grupos
├── fix_db.py                  # Utilidad: correcciones puntuales de BD
├── test_db_conn.py            # Test de conexión a PostgreSQL
├── test_delete_phase.py       # Test de eliminación de fase con cascada
├── predicciones.db            # Base de datos SQLite (fallback / desarrollo local)
└── requirements.txt           # Dependencias del proyecto
```

---

## ⚙️ Configuración e Instalación

### Requisitos Previos
- Python 3.8+
- PostgreSQL 14+ (o usar SQLite en modo desarrollo)

### Variables de Entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://predict:Predict123@localhost:5433/Predicciones` | URL de conexión a PostgreSQL |
| `SECRET_KEY` | `polla-mundialera-2026-super-secret-key` | Llave de sesión Flask |
| `ADMIN_USERNAME` | `admin` | Usuario administrador |
| `ADMIN_PASSWORD` | `admin2026` | Contraseña administrador |

> ⚠️ **Producción:** Configura estas variables como variables de entorno reales. No uses los valores por defecto.

### Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar en desarrollo
python run.py
# → http://127.0.0.1:5000
```

### Producción con Gunicorn

```bash
gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 4
```

### Migración SQLite → PostgreSQL

Si ya tienes datos en SQLite y quieres pasarlos a PostgreSQL:

```bash
python migrate_to_postgres.py
```

> El script migra las tablas en orden de dependencias y corrige las secuencias de auto-incremento en PostgreSQL.

---

## 🔑 Acceso Administrativo

- URL: `http://localhost:5000/admin/login`
- **Usuario:** `admin`
- **Contraseña:** `admin2026`

---

## 🗺 Flujo de Uso

```
Admin crea Evento → Crea Grupos → Asigna Equipos a Grupos
  → Genera partidos (automático por grupo o manual para eliminatorias)
  → Crea Fases y abre predicciones (toggle manual)
  → Participantes acceden por cédula y predicen marcadores
  → Admin cierra fase de predicciones
  → Admin ingresa resultados reales → Puntos calculados automáticamente
  → Ranking actualizado en tiempo real
```

---

## 🔄 Utilidades de Carga de Datos

| Script | Propósito |
|---|---|
| `seed_matches.py` | Siembra inicial de partidos del fixture de grupos |
| `update_matches_v2.py` | Actualiza fechas/horas de los 80 partidos de la fase de grupos del Mundial 2026 con normalización de nombres |
| `fix_db.py` | Correcciones puntuales de consistencia en la base de datos |
| `test_db_conn.py` | Verifica la conexión activa con PostgreSQL |

---

## 📦 Dependencias Principales

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.49
psycopg==3.2.10          # Driver PostgreSQL (psycopg v3)
psycopg-binary==3.2.10
WhiteNoise               # Servicio de estáticos en producción
gunicorn                 # Servidor WSGI para producción
Werkzeug==3.0.3
Jinja2==3.1.6
```

---

## 🔒 Seguridad

- Las rutas `/admin/*` están protegidas con el decorador `@require_admin` que valida la sesión Flask.
- Los participantes no tienen contraseña; se identifican por cédula + sesión de navegador.
- La visibilidad de predicciones ajenas es controlable por evento (`can_view_others_predictions`).
- Los resultados no pueden ingresarse mientras una fase de predicciones esté abierta (doble bloqueo).

---

*Documentación actualizada al 9 de junio de 2026 · Desarrollado con Antigravity AI*
