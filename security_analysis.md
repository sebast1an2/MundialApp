# 🔐 Análisis de Seguridad — MundialApp

> **Solo análisis — sin modificaciones al código.**  
> Enfocado en: validación de formularios, inputs, inyección XSS/SQL, y control de acceso.

---

## Resumen ejecutivo

| # | Hallazgo | Severidad | Área |
|---|---|---|---|
| 1 | Secretos hardcodeados en `config.py` | 🔴 Alta | Configuración |
| 2 | Ausencia de protección CSRF en formularios | 🔴 Alta | Todos los formularios |
| 3 | `cedula` y `name` sin validación de longitud/formato en servidor | 🟡 Media | `public.py` |
| 4 | Open Redirect en el login del admin | 🟡 Media | `auth.py` |
| 5 | Enumeración de cédulas (user enumeration) | 🟡 Media | `public.py` |
| 6 | Sin límite máximo real en inputs de marcador (backend) | 🟡 Media | `public.py` |
| 7 | Cédula expuesta en la URL | 🟡 Media | `public.py` |
| 8 | Sin rate limiting en login ni en formularios públicos | 🟠 Media-Alta | `auth.py`, `public.py` |

---

## 1. 🔴 Secretos hardcodeados en `config.py`

**Archivo:** [`config.py`](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/config.py#L7-L22)

```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'polla-mundialera-2026-super-secret-key')  # ← fallback público
db_url = os.environ.get('DATABASE_URL', 'postgresql+psycopg://predict:Predict123@localhost:5433/Predicciones')  # ← credenciales DB
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'troquel')   # ← usuario admin visible
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'troquel2026*')  # ← contraseña admin visible
```

**Riesgo:** Si el repositorio es público o accede alguien no autorizado al código fuente, tiene inmediatamente:
- La `SECRET_KEY` → puede falsificar cookies de sesión
- Las credenciales de la base de datos
- Las credenciales del panel admin

**Corrección sugerida:**  
Usar exclusivamente variables de entorno o un archivo `.env` **excluido del `.gitignore`**. Los valores por defecto nunca deben contener credenciales reales.

---

## 2. 🔴 Ausencia de protección CSRF en todos los formularios

**Archivos afectados:**
- [`auth/login.html`](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/templates/auth/login.html#L21) — Login admin
- [`public/validate.html`](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/templates/public/validate.html) — Cédula y registro
- [`public/predictions_form.html`](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/templates/public/predictions_form.html#L18) — Predicciones
- Todos los formularios admin (`team_form`, `event_form`, `phase_form`, etc.)

**Riesgo:** Ningún formulario incluye un token CSRF. Esto permite ataques de tipo **Cross-Site Request Forgery**: una página maliciosa externa puede hacer que un administrador autenticado ejecute acciones sin saberlo (crear eventos, eliminar participantes, guardar resultados falsos).

```html
<!-- Ejemplo: login.html — sin token CSRF -->
<form method="POST" action="{{ url_for('auth.login') }}">
  <!-- No hay <input type="hidden" name="csrf_token" value="..."> -->
```

**Corrección sugerida:**  
Instalar `Flask-WTF` e integrar `CSRFProtect`. Es una sola línea de configuración y agrega `{{ form.hidden_tag() }}` o `{{ csrf_token() }}` a cada formulario.

---

## 3. 🟡 `cedula` y `name` sin validación de longitud/formato en servidor

**Archivo:** [`public.py` líneas 82–109](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/public.py#L82-L109)

```python
cedula = request.form.get('cedula', '').strip()
name   = request.form.get('name', '').strip()

if not cedula:  # ← solo valida que no esté vacío
    flash('La cédula es obligatoria.', 'danger')
```

**Riesgos identificados:**

| Problema | Descripción |
|---|---|
| Sin límite de longitud | Un atacante puede enviar 10.000 caracteres como cédula — llegan directo al ORM |
| Sin validación de tipo | La cédula acepta letras, símbolos, HTML — debería ser solo numérica |
| `name` sin restricción | Acepta cualquier string; aunque Jinja2 escapa el HTML en templates, el dato queda tal cual en DB |
| `cedula` en campo hidden del form | `<input type="hidden" name="cedula" value="{{ cedula }}">` repropaga la cédula del usuario, que podría ser manipulada en el POST siguiente |

**Lo que SÍ está bien:**  
Flask-SQLAlchemy usa queries parametrizadas → la **inyección SQL directa está prevenida**. Jinja2 escapa por defecto → **XSS en templates está en gran medida prevenido**.

**Corrección sugerida:**  
Agregar validaciones en el backend antes de tocar la base de datos:
```python
import re
if not re.match(r'^\d{6,12}$', cedula):
    flash('Cédula inválida. Solo se permiten números (6–12 dígitos).', 'danger')
if len(name) > 100 or len(name) < 2:
    flash('Nombre inválido.', 'danger')
```

---

## 4. 🟡 Open Redirect en el login de admin

**Archivo:** [`auth.py` líneas 40–41](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones\MundialApp\app\routes\auth.py#L40-L41)

```python
next_url = request.args.get('next') or url_for('admin.dashboard')
return redirect(next_url)
```

**Riesgo:** El parámetro `?next=` **no está validado**. Un atacante puede construir un enlace de phishing:
```
https://tuapp.com/admin/login?next=https://sitio-malicioso.com
```
Si el admin hace clic en ese enlace e inicia sesión, es redirigido automáticamente al sitio externo, lo que puede usarse para robo de sesión o credenciales.

**Corrección sugerida:**
```python
from urllib.parse import urlparse, urljoin

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

next_url = request.args.get('next')
if not next_url or not is_safe_url(next_url):
    next_url = url_for('admin.dashboard')
return redirect(next_url)
```

---

## 5. 🟡 Enumeración de cédulas (user enumeration)

**Archivo:** [`public.py` líneas 91–113](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/public.py#L91-L113)

```python
participant = Participant.query.filter_by(cedula=cedula, event_id=event_id).first()

if participant:
    flash(f'¡Bienvenido de nuevo, {participant.name}!', 'success')  # ← revela que existe
    ...
else:
    # revela que NO existe → permite al atacante descubrir qué cédulas están registradas
    if not open_phase:
        flash('Las predicciones para esta fase ya están cerradas y no estás registrado.', 'warning')
```

**Riesgo:** Los mensajes de respuesta permiten distinguir si una cédula está registrada o no, lo que facilita ataques de enumeración de usuarios. En un contexto con datos personales (cédula + nombre), esto puede considerarse una filtración de información sensible.

**Corrección sugerida:**  
Usar mensajes genéricos que no diferencien si el usuario existe o no, cuando la fase está cerrada:
> "No pudimos procesar tu solicitud. Si ya participaste, intenta de nuevo más tarde."

---

## 6. 🟡 Sin validación de límite máximo real en marcadores (backend)

**Archivo:** [`public.py` líneas 219–226](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/public.py#L219-L226)

```python
home_pred = int(home_raw)
away_pred = int(away_raw)
if home_pred < 0 or away_pred < 0:  # ← solo valida que no sean negativos
    raise ValueError
```

El HTML usa `max="99"`, pero ese límite **es solo del lado del cliente** y puede bypassearse fácilmente con cualquier herramienta (curl, Postman, DevTools).

**Riesgo:** Un usuario puede guardar una predicción de `9999 - 9999`, que no tiene sentido en un partido de fútbol y podría afectar visualizaciones o cálculos.

**Corrección sugerida:**
```python
MAX_SCORE = 99
if not (0 <= home_pred <= MAX_SCORE and 0 <= away_pred <= MAX_SCORE):
    errors.append(f'Marcador fuera de rango para {match.home_team.name} vs {match.away_team.name}')
```

---

## 7. 🟡 Cédula expuesta en la URL

**Archivo:** [`public.py` líneas 150–181](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/public.py#L150-L181)

```python
@public_bp.route('/evento/<int:event_id>/predicciones/<cedula>')
@public_bp.route('/evento/<int:event_id>/mis-predicciones/<cedula>')
```

URLs resultantes:
```
/evento/1/predicciones/1234567890
/evento/1/mis-predicciones/1234567890
```

**Riesgo:** La cédula (número de identificación personal) queda expuesta en la URL del navegador, aparece en los logs del servidor web, historial del navegador, y cabeceras HTTP Referer. Esto puede constituir una **filtración de datos personales** (PII) especialmente en contextos legales colombianos (Ley 1581 de 2012 - Habeas Data).

**Corrección sugerida:**  
Usar el `participant_id` (número interno, sin valor personal) en la URL en lugar de la cédula:
```python
@public_bp.route('/evento/<int:event_id>/predicciones/<int:participant_id>')
```

---

## 8. 🟠 Sin rate limiting en login ni en formularios públicos

**Archivos:**
- [`auth.py` línea 25](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/auth.py#L25) — Login admin
- [`public.py` línea 76](file:///c:/Users/Programador.ti2/Desktop/DATA/Sf_git/Predicciones/MundialApp/app/routes/public.py#L76) — Formulario cédula

**Riesgo:**
- **Login admin**: Sin límite de intentos, es vulnerable a ataques de fuerza bruta. Un atacante puede probar miles de contraseñas automáticamente.
- **Formulario público de cédula**: Sin límite de intentos, puede usarse para enumerar masivamente cédulas registradas.

**Corrección sugerida:**  
Instalar `Flask-Limiter`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login(): ...
```

---

## Resumen de lo que está BIEN ✅

| Aspecto | Detalle |
|---|---|
| ✅ Inyección SQL | SQLAlchemy ORM con queries parametrizadas — no hay SQL crudo |
| ✅ XSS en templates | Jinja2 escapa HTML por defecto en todas las variables `{{ }}` |
| ✅ Control de acceso admin | `@require_admin` en todas las rutas del panel |
| ✅ Verificación de sesión en predicciones | `session.get(f'participant_event_{event_id}')` antes de operar |
| ✅ Acceso cruzado entre participantes | Verificación de ownership antes de mostrar predicciones ajenas |
| ✅ Marcadores negativos | Rechazados en backend (`if home_pred < 0`) |
| ✅ Doble predicción | `has_predicted_phase()` previene predicciones duplicadas |
| ✅ Borrado en cascada | Eliminación segura de eventos, fases y grupos con sus datos relacionados |

---

## Prioridad de corrección recomendada

```
1. [CRÍTICO]  Mover credenciales a variables de entorno / .env
2. [CRÍTICO]  Implementar protección CSRF (Flask-WTF, 1 hora de trabajo)
3. [MEDIO]    Rate limiting en login admin (Flask-Limiter, 30 min)
4. [MEDIO]    Validación de formato/longitud de cédula y nombre en backend
5. [MEDIO]    Corregir Open Redirect en parámetro `?next=`
6. [BAJO]     Reemplazar cédula por ID interno en URLs
7. [BAJO]     Agregar límite máximo de marcador en backend (MAX=99)
8. [BAJO]     Revisar mensajes para evitar enumeración de usuarios
```
