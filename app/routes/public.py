from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from app import db
from app.models import (Event, Phase, Match, Participant,
                        Prediction, Score, Group)
from app.services.standings import calculate_event_group_standings, calculate_top_scoring_teams

public_bp = Blueprint('public', __name__)


# ─── HOME ─────────────────────────────────────────────────────────────────────

@public_bp.route('/')
def home():
    active_events = Event.query.filter_by(status='active').order_by(Event.created_at.desc()).all()
    all_events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template('public/home.html',
                           active_events=active_events,
                           all_events=all_events)


# ─── EVENT PAGE ───────────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Validation gatekeeper
    participant_id = session.get(f'participant_event_{event_id}')
    if not participant_id:
        return redirect(url_for('public.validate_participant', event_id=event_id))
    
    participant = Participant.query.get(participant_id)
    if not participant:
        session.pop(f'participant_event_{event_id}', None)
        return redirect(url_for('public.validate_participant', event_id=event_id))

    phases = Phase.query.filter_by(event_id=event_id).order_by(Phase.phase_order).all()
    open_phase = event.get_active_phase()
    has_predicted = participant.has_predicted_phase(open_phase.id) if (participant and open_phase) else False

    # Top 10 for the public ranking preview
    top_participants = (Participant.query
                        .filter_by(event_id=event_id)
                        .order_by(Participant.total_points.desc(), Participant.created_at)
                        .limit(10).all())

    total_participants = Participant.query.filter_by(event_id=event_id).count()
    matches_finished = (Match.query.join(Phase)
                        .filter(Phase.event_id == event_id, Match.is_finished == True)
                        .count())

    # Get results for the new section
    all_matches = (Match.query.join(Phase)
                   .filter(Phase.event_id == event_id)
                   .order_by(Phase.phase_order, Match.match_date)
                   .all())

    # Top scoring teams
    top_teams = calculate_top_scoring_teams(event_id, limit=5)

    return render_template('public/event.html',
                           event=event,
                           phases=phases,
                           open_phase=open_phase,
                           participant=participant,
                           has_predicted=has_predicted,
                           top_participants=top_participants,
                           total_participants=total_participants,
                           matches_finished=matches_finished,
                           all_matches=all_matches,
                           top_teams=top_teams)


# ─── VALIDATE PARTICIPANT (GATEKEEPER) ────────────────────────────────────────
@public_bp.route('/evento/<int:event_id>/validar', methods=['GET', 'POST'])
def validate_participant(event_id):
    event = Event.query.get_or_404(event_id)
    open_phase = event.get_active_phase()
    
    if request.method == 'POST':
        cedula = request.form.get('cedula', '').strip()
        name = request.form.get('name', '').strip()
        
        if not cedula:
            flash('La cédula es obligatoria.', 'danger')
            return render_template('public/validate.html', event=event, step='cedula')
            
        participant = Participant.query.filter_by(cedula=cedula, event_id=event_id).first()
        
        if participant:
            # Caso 1: Ya tiene participación
            session[f'participant_event_{event_id}'] = participant.id
            flash(f'¡Bienvenido de nuevo, {participant.name}!', 'success')
            return redirect(url_for('public.event_detail', event_id=event_id))
        else:
            # Caso 2 y 3: No tiene participación
            if not open_phase:
                # Caso 3: Fase cerrada
                flash('Las predicciones para esta fase ya están cerradas y no estás registrado.', 'warning')
                return render_template('public/validate.html', event=event, step='closed')
            
            # Caso 2: Permitir registro si hay fase abierta
            if not name:
                # Falta el nombre para el nuevo registro
                return render_template('public/validate.html', event=event, step='name', cedula=cedula)
            
            # Crear participante
            new_participant = Participant(cedula=cedula, name=name, event_id=event_id)
            db.session.add(new_participant)
            db.session.commit()
            session[f'participant_event_{event_id}'] = new_participant.id
            flash('Registro completado. ¡Ya puedes participar!', 'success')
            return redirect(url_for('public.event_detail', event_id=event_id))

    return render_template('public/validate.html', event=event, step='cedula')


# ─── PARTICIPATE ──────────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/participar', methods=['GET', 'POST'])
def participate(event_id):
    event = Event.query.get_or_404(event_id)
    open_phase = event.get_active_phase()

    if not open_phase:
        flash('No hay ninguna fase abierta para predicciones actualmente.', 'warning')
        return redirect(url_for('public.event_detail', event_id=event_id))

    participant_id = session.get(f'participant_event_{event_id}')
    if not participant_id:
        return redirect(url_for('public.validate_participant', event_id=event_id))
    
    participant = Participant.query.get(participant_id)
    if not participant:
        session.pop(f'participant_event_{event_id}', None)
        return redirect(url_for('public.validate_participant', event_id=event_id))

    if participant.has_predicted_phase(open_phase.id):
        flash(f'Ya realizaste tus predicciones para "{open_phase.name}".', 'info')
        return redirect(url_for('public.my_predictions',
                               event_id=event_id, cedula=participant.cedula))

    return redirect(url_for('public.predictions_form',
                            event_id=event_id, cedula=participant.cedula))


# ─── PREDICTIONS FORM ─────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/predicciones/<cedula>')
def predictions_form(event_id, cedula):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(
        cedula=cedula, event_id=event_id).first_or_404()
    
    # Session check
    if session.get(f'participant_event_{event_id}') != participant.id:
        flash('No tienes permiso para acceder a estas predicciones.', 'danger')
        return redirect(url_for('public.event_detail', event_id=event_id))

    open_phase = event.get_active_phase()

    if not open_phase:
        flash('No hay ninguna fase de predicción abierta.', 'warning')
        return redirect(url_for('public.event_detail', event_id=event_id))

    if participant.has_predicted_phase(open_phase.id):
        flash('Ya realizaste tus predicciones para esta fase.', 'info')
        return redirect(url_for('public.my_predictions',
                                event_id=event_id, cedula=cedula))

    matches = (Match.query.filter_by(phase_id=open_phase.id)
               .order_by(Match.match_date, Match.id).all())

    if not matches:
        flash('Esta fase no tiene partidos cargados aún.', 'warning')
        return redirect(url_for('public.event_detail', event_id=event_id))

    return render_template('public/predictions_form.html',
                           event=event, participant=participant,
                           phase=open_phase, matches=matches)


@public_bp.route('/evento/<int:event_id>/guardar-predicciones', methods=['POST'])
def save_predictions(event_id):
    event = Event.query.get_or_404(event_id)
    cedula = request.form.get('cedula', '').strip()
    phase_id = request.form.get('phase_id', type=int)

    participant = Participant.query.filter_by(
        cedula=cedula, event_id=event_id).first()
    phase = Phase.query.get(phase_id)

    if not participant or not phase:
        flash('Error: datos inválidos.', 'danger')
        return redirect(url_for('public.event_detail', event_id=event_id))

    if not phase.is_prediction_open:
        flash('Esta fase ya no está abierta para predicciones.', 'danger')
        return redirect(url_for('public.event_detail', event_id=event_id))

    if participant.has_predicted_phase(phase_id):
        flash('Ya realizaste tus predicciones para esta fase.', 'warning')
        return redirect(url_for('public.my_predictions',
                                event_id=event_id, cedula=cedula))

    matches = Match.query.filter_by(phase_id=phase_id).all()
    saved = 0
    errors = []

    for match in matches:
        home_raw = request.form.get(f'home_{match.id}', '').strip()
        away_raw = request.form.get(f'away_{match.id}', '').strip()

        if match.is_locked:
            if home_raw != '' or away_raw != '':
                errors.append(f'El partido {match.home_team.name} vs {match.away_team.name} está bloqueado.')
            continue

        if home_raw == '' or away_raw == '':
            errors.append(f'Falta predicción para {match.home_team.name} vs {match.away_team.name}')
            continue

        try:
            home_pred = int(home_raw)
            away_pred = int(away_raw)
            if home_pred < 0 or away_pred < 0:
                raise ValueError
        except ValueError:
            errors.append(f'Predicción inválida para {match.home_team.name} vs {match.away_team.name}')
            continue

        pred = Prediction(
            participant_id=participant.id,
            match_id=match.id,
            phase_id=phase_id,
            home_pred=home_pred,
            away_pred=away_pred,
        )
        db.session.add(pred)
        saved += 1

    if errors:
        db.session.rollback()
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('public.predictions_form',
                                event_id=event_id, cedula=cedula))

    db.session.commit()
    flash(f'¡Predicciones guardadas! ({saved} partidos). '
          'Ya no podrás modificarlas.', 'success')
    return redirect(url_for('public.my_predictions',
                            event_id=event_id, cedula=cedula))


# ─── MY PREDICTIONS ───────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/mis-predicciones/<cedula>')
def my_predictions(event_id, cedula):
    event = Event.query.get_or_404(event_id)
    participant = Participant.query.filter_by(
        cedula=cedula, event_id=event_id).first_or_404()
    
    # Check if viewing self or if viewing others is allowed
    is_self = session.get(f'participant_event_{event_id}') == participant.id
    if not is_self and not event.can_view_others_predictions:
        flash('No tienes permiso para ver las predicciones de otros participantes.', 'warning')
        return redirect(url_for('public.event_detail', event_id=event_id))

    phases = Phase.query.filter_by(event_id=event_id).order_by(Phase.phase_order).all()

    phase_data = []
    for phase in phases:
        preds = (Prediction.query
                 .filter_by(participant_id=participant.id, phase_id=phase.id)
                 .join(Match).order_by(Match.match_date, Match.id)
                 .all())
        if not preds:
            continue

        pred_with_score = []
        phase_points = 0
        for pred in preds:
            score = Score.query.filter_by(
                participant_id=participant.id,
                match_id=pred.match_id
            ).first()
            pts = score.points_earned if score else None
            stype = score.score_type if score else None
            phase_points += (pts or 0)
            pred_with_score.append({
                'prediction': pred,
                'match': pred.match,
                'points': pts,
                'score_type': stype,
            })

        phase_data.append({
            'phase': phase,
            'predictions': pred_with_score,
            'phase_points': phase_points,
        })

    # Most recent phase first
    phase_data.reverse()

    # Ranking position
    ranked = (Participant.query.filter_by(event_id=event_id)
              .order_by(Participant.total_points.desc(), Participant.created_at)
              .all())
    position = next((i + 1 for i, p in enumerate(ranked) if p.id == participant.id), None)
    total_participants = len(ranked)

    return render_template('public/my_predictions.html',
                           event=event,
                           participant=participant,
                           phase_data=phase_data,
                           position=position,
                           total_participants=total_participants)


# ─── PUBLIC RANKING ───────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/ranking')
def ranking(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.can_view_others_predictions:
        flash('La visualización del ranking de otros participantes está desactivada.', 'info')
        return redirect(url_for('public.event_detail', event_id=event_id))

    current_participant_id = session.get(f'participant_event_{event_id}')

    all_participants = (Participant.query.filter_by(event_id=event_id)
                        .order_by(Participant.total_points.desc(), Participant.created_at)
                        .all())
    return render_template('public/ranking.html',
                           event=event,
                           participants=all_participants,
                           current_participant_id=current_participant_id)


# ─── COMPARE PREDICTIONS ──────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/comparar/<other_cedula>')
def compare_predictions(event_id, other_cedula):
    event = Event.query.get_or_404(event_id)

    # Gate: feature only available when others' predictions are visible
    if not event.can_view_others_predictions:
        flash('La comparación de predicciones no está disponible en este evento.', 'warning')
        return redirect(url_for('public.event_detail', event_id=event_id))

    # Require the logged-in participant
    my_id = session.get(f'participant_event_{event_id}')
    if not my_id:
        return redirect(url_for('public.validate_participant', event_id=event_id))

    me = Participant.query.get_or_404(my_id)
    other = Participant.query.filter_by(cedula=other_cedula, event_id=event_id).first_or_404()

    # Can't compare with yourself
    if me.id == other.id:
        return redirect(url_for('public.my_predictions', event_id=event_id, cedula=me.cedula))

    # Build comparison data: one entry per phase, each containing per-match rows
    phases = Phase.query.filter_by(event_id=event_id).order_by(Phase.phase_order.desc()).all()

    comparison_data = []
    for phase in phases:
        matches = (Match.query.filter_by(phase_id=phase.id)
                   .order_by(Match.match_date, Match.id).all())
        if not matches:
            continue

        # Index predictions by match_id for both participants
        def pred_map(participant_id):
            preds = Prediction.query.filter_by(
                participant_id=participant_id, phase_id=phase.id).all()
            return {p.match_id: p for p in preds}

        my_preds    = pred_map(me.id)
        other_preds = pred_map(other.id)

        # Only include phases where at least one participant has predicted
        if not my_preds and not other_preds:
            continue

        rows = []
        for match in matches:
            my_p    = my_preds.get(match.id)
            other_p = other_preds.get(match.id)
            if not my_p and not other_p:
                continue
            rows.append({
                'match':   match,
                'my_pred':    my_p,
                'other_pred': other_p,
            })

        if rows:
            comparison_data.append({'phase': phase, 'rows': rows})

    return render_template('public/compare.html',
                           event=event,
                           me=me,
                           other=other,
                           comparison_data=comparison_data)


# ─── GROUP STANDINGS ──────────────────────────────────────────────────────────

@public_bp.route('/evento/<int:event_id>/grupos')
def group_standings(event_id):
    event = Event.query.get_or_404(event_id)
    standings_by_group = calculate_event_group_standings(event_id)
    return render_template('public/group_standings.html',
                           event=event,
                           standings_by_group=standings_by_group)
