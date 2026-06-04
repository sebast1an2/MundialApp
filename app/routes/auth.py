from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask import current_app

auth_bp = Blueprint('auth', __name__)


def is_admin():
    return session.get('is_admin', False)


def require_admin(f):
    """Decorator to protect admin routes."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin():
            flash('Debes iniciar sesión como administrador.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)

    return decorated


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if is_admin():
        return redirect(url_for('admin.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if (username == current_app.config['ADMIN_USERNAME'] and
                password == current_app.config['ADMIN_PASSWORD']):
            session['is_admin'] = True
            session.permanent = True
            flash('Bienvenido, administrador.', 'success')
            next_url = request.args.get('next') or url_for('admin.dashboard')
            return redirect(next_url)
        else:
            error = 'Credenciales incorrectas. Inténtalo de nuevo.'

    return render_template('auth/login.html', error=error)


@auth_bp.route('/admin/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))
