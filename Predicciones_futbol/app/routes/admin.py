from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from app import db
from app.models import (Team, Event, Group, GroupTeam, Phase,
                        Match, Participant, Prediction, Score, ScoringConfig)
from app.routes.auth import require_admin
from app.services.seeder import seed_teams
from app.services.scoring import calculate_match_scores, recalculate_all_event_scores
from app.services.standings import calculate_event_group_standings

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@admin_bp.route('/')
@require_admin
def dashboard():
    total_events = Event.query.count()
    total_teams = Team.query.count()
    active_events = Event.query.filter_by(status='active').all()
    recent_results = Match.query.filter_by(is_finished=True)\
                                .order_by(Match.id.desc()).limit(5).all()
    total_participants = Participant.query.count()
    total_predictions = Prediction.query.count()
    return render_template('admin/dashboard.html',
                           total_events=total_events,
                           total_teams=total_teams,
                           active_events=active_events,
                           recent_results=recent_results,
                           total_participants=total_participants,
                           total_predictions=total_predictions)


# ─── TEAMS ───────────────────────────────────────────────────────────────────

@admin_bp.route('/teams')
@require_admin
def teams():
    filter_type = request.args.get('type', 'all')
    q = request.args.get('q', '').strip()
    query = Team.query
    if filter_type in ('national', 'club'):
        query = query.filter_by(team_type=filter_type)
    if q:
        query = query.filter(Team.name.ilike(f'%{q}%'))
    all_teams = query.order_by(Team.name).all()
    return render_template('admin/teams.html', teams=all_teams,
                           filter_type=filter_type, q=q)


@admin_bp.route('/teams/new', methods=['GET', 'POST'])
@require_admin
def teams_new():
    if request.method == 'POST':
        team = Team(
            name=request.form['name'].strip(),
            short_name=request.form.get('short_name', '').strip().upper(),
            team_type=request.form['team_type'],
            flag_emoji=request.form.get('flag_emoji', '🏴').strip(),
            country_code=request.form.get('country_code', '').strip().upper(),
        )
        db.session.add(team)
        db.session.commit()
        flash(f'Equipo "{team.name}" creado correctamente.', 'success')
        return redirect(url_for('admin.teams'))
    return render_template('admin/team_form.html', team=None)


@admin_bp.route('/teams/<int:team_id>/edit', methods=['GET', 'POST'])
@require_admin
def teams_edit(team_id):
    team = Team.query.get_or_404(team_id)
    if request.method == 'POST':
        team.name = request.form['name'].strip()
        team.short_name = request.form.get('short_name', '').strip().upper()
        team.team_type = request.form['team_type']
        team.flag_emoji = request.form.get('flag_emoji', '🏴').strip()
        team.country_code = request.form.get('country_code', '').strip().upper()
        db.session.commit()
        flash(f'Equipo "{team.name}" actualizado.', 'success')
        return redirect(url_for('admin.teams'))
    return render_template('admin/team_form.html', team=team)


@admin_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@require_admin
def teams_delete(team_id):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    flash(f'Equipo "{team.name}" eliminado.', 'info')
    return redirect(url_for('admin.teams'))


@admin_bp.route('/teams/seed', methods=['POST'])
@require_admin
def teams_seed():
    added = seed_teams()
    flash(f'Carga inicial completada: {added} equipos añadidos.', 'success')
    return redirect(url_for('admin.teams'))


# ─── EVENTS ──────────────────────────────────────────────────────────────────

@admin_bp.route('/events')
@require_admin
def events():
    all_events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template('admin/events.html', events=all_events)


@admin_bp.route('/events/new', methods=['GET', 'POST'])
@require_admin
def events_new():
    if request.method == 'POST':
        event = Event(
            name=request.form['name'].strip(),
            tournament_type=request.form.get('tournament_type', 'world_cup'),
            description=request.form.get('description', '').strip(),
            logo_emoji=request.form.get('logo_emoji', '🏆').strip(),
        )
        db.session.add(event)
        db.session.flush()  # get event.id before commit
        ScoringConfig.create_defaults(event.id)
        flash(f'Evento "{event.name}" creado.', 'success')
        return redirect(url_for('admin.event_detail', event_id=event.id))
    return render_template('admin/event_form.html', event=None)


@admin_bp.route('/events/<int:event_id>')
@require_admin
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    phases = Phase.query.filter_by(event_id=event_id).order_by(Phase.phase_order).all()
    groups = Group.query.filter_by(event_id=event_id).order_by(Group.name).all()
    participants_count = Participant.query.filter_by(event_id=event_id).count()
    matches_total = Match.query.join(Phase).filter(Phase.event_id == event_id).count()
    matches_finished = Match.query.join(Phase).filter(
        Phase.event_id == event_id, Match.is_finished == True).count()
    return render_template('admin/event_detail.html',
                           event=event, phases=phases, groups=groups,
                           participants_count=participants_count,
                           matches_total=matches_total,
                           matches_finished=matches_finished)


@admin_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@require_admin
def events_edit(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        event.name = request.form['name'].strip()
        event.tournament_type = request.form.get('tournament_type', 'world_cup')
        event.description = request.form.get('description', '').strip()
        event.logo_emoji = request.form.get('logo_emoji', '🏆').strip()
        event.status = request.form.get('status', 'draft')
        event.can_view_others_predictions = bool(request.form.get('can_view_others_predictions'))
        db.session.commit()
        flash('Evento actualizado.', 'success')
        return redirect(url_for('admin.event_detail', event_id=event_id))
    return render_template('admin/event_form.html', event=event)


@admin_bp.route('/events/<int:event_id>/delete', methods=['POST'])
@require_admin
def events_delete(event_id):
    event = Event.query.get_or_404(event_id)
    name = event.name

    # Manual cascade to avoid ORM conflicts between relationships
    phase_ids = [p.id for p in Phase.query.filter_by(event_id=event_id).all()]
    match_ids = [m.id for m in Match.query.filter(
        Match.phase_id.in_(phase_ids)).all()] if phase_ids else []
    participant_ids = [p.id for p in Participant.query.filter_by(event_id=event_id).all()]
    group_ids = [g.id for g in Group.query.filter_by(event_id=event_id).all()]

    if match_ids:
        Score.query.filter(Score.match_id.in_(match_ids)).delete(synchronize_session=False)
        Prediction.query.filter(Prediction.match_id.in_(match_ids)).delete(synchronize_session=False)
        Match.query.filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
    if phase_ids:
        Phase.query.filter(Phase.id.in_(phase_ids)).delete(synchronize_session=False)
    if group_ids:
        GroupTeam.query.filter(GroupTeam.group_id.in_(group_ids)).delete(synchronize_session=False)
        Group.query.filter(Group.id.in_(group_ids)).delete(synchronize_session=False)
    if participant_ids:
        Participant.query.filter(Participant.id.in_(participant_ids)).delete(synchronize_session=False)
    ScoringConfig.query.filter_by(event_id=event_id).delete(synchronize_session=False)

    db.session.delete(event)
    db.session.commit()
    flash(f'Evento "{name}" y todos sus datos fueron eliminados correctamente.', 'info')
    return redirect(url_for('admin.events'))


# ─── GROUPS ──────────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/groups')
@require_admin
def groups(event_id):
    event = Event.query.get_or_404(event_id)
    all_groups = Group.query.filter_by(event_id=event_id).order_by(Group.name).all()

    groups_with_teams = []
    for g in all_groups:
        gts = GroupTeam.query.filter_by(group_id=g.id).all()
        teams_in_group = [gt.team for gt in gts]
        groups_with_teams.append({'group': g, 'teams': teams_in_group})

    # Auto-filter teams by tournament type
    type_to_team_type = {
        'world_cup':    'national',
        'copa_america': 'national',
        'champions':    'club',
    }
    team_type_filter = type_to_team_type.get(event.tournament_type)  # None → show all

    # Get all teams currently assigned to ANY group in this event
    assigned_team_ids = [gt.team_id for g in all_groups for gt in GroupTeam.query.filter_by(group_id=g.id).all()]

    team_query = Team.query
    if team_type_filter:
        team_query = team_query.filter_by(team_type=team_type_filter)
    
    # Exclude teams already assigned to other groups
    if assigned_team_ids:
        team_query = team_query.filter(~Team.id.in_(assigned_team_ids))
        
    all_filtered_teams = team_query.order_by(Team.name).all()

    return render_template('admin/groups.html',
                           event=event,
                           groups_with_teams=groups_with_teams,
                           all_filtered_teams=all_filtered_teams,
                           team_type_filter=team_type_filter)


@admin_bp.route('/events/<int:event_id>/groups/new', methods=['POST'])
@require_admin
def groups_new(event_id):
    event = Event.query.get_or_404(event_id)
    name = request.form.get('name', '').strip().upper()
    if not name:
        flash('El nombre del grupo es requerido.', 'danger')
    elif Group.query.filter_by(event_id=event_id, name=name).first():
        flash(f'El grupo "{name}" ya existe.', 'warning')
    else:
        g = Group(event_id=event_id, name=name)
        db.session.add(g)
        db.session.commit()
        flash(f'Grupo {name} creado.', 'success')
    return redirect(url_for('admin.groups', event_id=event_id))


@admin_bp.route('/groups/<int:group_id>/teams', methods=['POST'])
@require_admin
def group_teams_update(group_id):
    group = Group.query.get_or_404(group_id)
    team_ids = request.form.getlist('team_ids')
    
    # Check if any team is already in ANOTHER group in this event
    other_groups = Group.query.filter(Group.event_id == group.event_id, Group.id != group_id).all()
    other_group_ids = [g.id for g in other_groups]
    if other_group_ids:
        conflicts = GroupTeam.query.filter(GroupTeam.group_id.in_(other_group_ids), GroupTeam.team_id.in_(team_ids)).all()
        if conflicts:
            flash('Error: Uno o más equipos ya están asignados a otro grupo en este evento.', 'danger')
            return redirect(url_for('admin.groups', event_id=group.event_id))

    # Remove existing assignments
    GroupTeam.query.filter_by(group_id=group_id).delete()
    for i, tid in enumerate(team_ids):
        db.session.add(GroupTeam(group_id=group_id, team_id=int(tid), seed_order=i))
    db.session.commit()
    flash(f'Equipos del Grupo {group.name} actualizados.', 'success')
    return redirect(url_for('admin.groups', event_id=group.event_id))


@admin_bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@require_admin
def groups_delete(group_id):
    group = Group.query.get_or_404(group_id)
    event_id = group.event_id
    
    # Manual cascade to safely remove related matches, predictions, scores, and group teams
    match_ids = [m.id for m in Match.query.filter_by(group_id=group_id).all()]
    if match_ids:
        Score.query.filter(Score.match_id.in_(match_ids)).delete(synchronize_session=False)
        Prediction.query.filter(Prediction.match_id.in_(match_ids)).delete(synchronize_session=False)
        Match.query.filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
    
    GroupTeam.query.filter_by(group_id=group_id).delete(synchronize_session=False)
    
    db.session.delete(group)
    db.session.commit()
    flash(f'Grupo {group.name} eliminado.', 'info')
    return redirect(url_for('admin.groups', event_id=event_id))

@admin_bp.route('/groups/<int:group_id>/generate_matches', methods=['POST'])
@require_admin
def groups_generate_matches(group_id):
    group = Group.query.get_or_404(group_id)
    event = group.event
    
    phase = Phase.query.filter(Phase.event_id == event.id, Phase.phase_order == 1).first()
    if not phase:
        phase = Phase(event_id=event.id, name="Fase de Grupos", phase_order=1)
        db.session.add(phase)
        db.session.commit()
        
    teams = [gt.team for gt in GroupTeam.query.filter_by(group_id=group.id).order_by(GroupTeam.seed_order).all()]
    if len(teams) < 2:
        flash('El grupo debe tener al menos 2 equipos para generar partidos.', 'warning')
        return redirect(url_for('admin.groups', event_id=event.id))
        
    import itertools
    matches = list(itertools.combinations(teams, 2))
    
    existing = Match.query.filter_by(group_id=group.id).all()
    existing_pairs = set()
    for m in existing:
        existing_pairs.add((m.home_team_id, m.away_team_id))
        existing_pairs.add((m.away_team_id, m.home_team_id))
        
    added = 0
    for home, away in matches:
        if (home.id, away.id) not in existing_pairs:
            new_match = Match(phase_id=phase.id, group_id=group.id, 
                              home_team_id=home.id, away_team_id=away.id,
                              match_label=f'Grupo {group.name}')
            db.session.add(new_match)
            added += 1
            
    db.session.commit()
    flash(f'Se generaron {added} partidos para el Grupo {group.name}.', 'success')
    return redirect(url_for('admin.matches', event_id=event.id, phase_id=phase.id))



# ─── PHASES ──────────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/phases')
@require_admin
def phases(event_id):
    event = Event.query.get_or_404(event_id)
    all_phases = Phase.query.filter_by(event_id=event_id)\
                            .order_by(Phase.phase_order).all()
    return render_template('admin/phases.html', event=event, phases=all_phases)


@admin_bp.route('/events/<int:event_id>/phases/new', methods=['POST'])
@require_admin
def phases_new(event_id):
    event = Event.query.get_or_404(event_id)
    name = request.form.get('name', '').strip()
    order = request.form.get('phase_order', 1)
    if not name:
        flash('El nombre de la fase es requerido.', 'danger')
    else:
        p = Phase(event_id=event_id, name=name, phase_order=int(order))
        db.session.add(p)
        db.session.commit()
        flash(f'Fase "{name}" creada.', 'success')
    return redirect(url_for('admin.phases', event_id=event_id))


@admin_bp.route('/phases/<int:phase_id>/edit', methods=['GET', 'POST'])
@require_admin
def phases_edit(phase_id):
    phase = Phase.query.get_or_404(phase_id)
    if request.method == 'POST':
        phase.name = request.form['name'].strip()
        phase.phase_order = int(request.form.get('phase_order', phase.phase_order))
        db.session.commit()
        flash('Fase actualizada.', 'success')
        return redirect(url_for('admin.phases', event_id=phase.event_id))
    return render_template('admin/phase_form.html', phase=phase)


@admin_bp.route('/phases/<int:phase_id>/toggle', methods=['POST'])
@require_admin
def phases_toggle(phase_id):
    phase = Phase.query.get_or_404(phase_id)
    phase.is_prediction_open = not phase.is_prediction_open
    db.session.commit()
    state = 'ABIERTA' if phase.is_prediction_open else 'CERRADA'
    flash(f'Fase "{phase.name}" ahora está {state} para predicciones.', 'success')
    return redirect(url_for('admin.phases', event_id=phase.event_id))


@admin_bp.route('/phases/<int:phase_id>/delete', methods=['POST'])
@require_admin
def phases_delete(phase_id):
    phase = Phase.query.get_or_404(phase_id)
    event_id = phase.event_id
    name = phase.name

    match_ids = [m.id for m in phase.matches.all()]
    if match_ids:
        Score.query.filter(Score.match_id.in_(match_ids)).delete(synchronize_session=False)
        Prediction.query.filter(Prediction.match_id.in_(match_ids)).delete(synchronize_session=False)
        Match.query.filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
    
    # Also delete predictions linked directly to the phase just in case
    Prediction.query.filter_by(phase_id=phase.id).delete(synchronize_session=False)

    db.session.delete(phase)
    db.session.commit()
    flash(f'Fase "{name}" y todos sus partidos eliminados correctamente.', 'info')
    return redirect(url_for('admin.phases', event_id=event_id))


def get_available_teams_for_phase(event_id, phase):
    """
    Returns a list of Team objects that are eligible to participate in the given phase.
    Logic:
    - Phase order 1 or name contains 'grupo': All teams assigned to groups in the event.
    - Subsequent phases: Winners/Qualified teams from the previous phase.
    """
    if not phase:
        return []

    if phase.phase_order == 1 or 'grupo' in phase.name.lower():
        groups = Group.query.filter_by(event_id=event_id).all()
        group_ids = [g.id for g in groups]
        if not group_ids:
            return []
        team_ids = [gt.team_id for gt in GroupTeam.query.filter(GroupTeam.group_id.in_(group_ids)).all()]
        return Team.query.filter(Team.id.in_(team_ids)).order_by(Team.name).all()
    
    # Knockout: Previous phase winners
    prev_phase = Phase.query.filter_by(event_id=event_id, phase_order=phase.phase_order - 1).first()
    if not prev_phase:
        return []
    
    available_teams = []
    if prev_phase.phase_order == 1 or 'grupo' in prev_phase.name.lower():
        # From groups
        standings = calculate_event_group_standings(event_id)
        qualified_list = []
        for g_obj, g_standings in standings.items():
            for row in g_standings[:2]:
                qualified_list.append(row['team'])
        # Unique and sorted
        team_ids = list(set([t.id for t in qualified_list]))
        available_teams = Team.query.filter(Team.id.in_(team_ids)).order_by(Team.name).all()
    else:
        # From knockout
        winners_ids = []
        prev_matches = Match.query.filter_by(phase_id=prev_phase.id, is_finished=True).all()
        for m in prev_matches:
            res = m.get_result()
            if res == 'home':
                winners_ids.append(m.home_team_id)
            elif res == 'away':
                winners_ids.append(m.away_team_id)
        if winners_ids:
            available_teams = Team.query.filter(Team.id.in_(list(set(winners_ids)))).order_by(Team.name).all()
            
    return available_teams


# ─── MATCHES ─────────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/matches')
@require_admin
def matches(event_id):
    event = Event.query.get_or_404(event_id)
    phase_id = request.args.get('phase_id', type=int)
    phases_list = Phase.query.filter_by(event_id=event_id)\
                             .order_by(Phase.phase_order).all()
    selected_phase = None
    matches_list = []
    if phase_id:
        selected_phase = Phase.query.get(phase_id)
        matches_list = Match.query.filter_by(phase_id=phase_id)\
                                  .order_by(Match.match_date).all()
    elif phases_list:
        selected_phase = phases_list[0]
        matches_list = Match.query.filter_by(phase_id=selected_phase.id)\
                                  .order_by(Match.match_date).all()

    groups_list = Group.query.filter_by(event_id=event_id).order_by(Group.name).all()
    
    # --- Dynamic Team Filtering ---
    available_teams = []
    is_knockout = False
    
    if selected_phase:
        available_teams = get_available_teams_for_phase(event_id, selected_phase)
        is_knockout = not (selected_phase.phase_order == 1 or 'grupo' in selected_phase.name.lower())

    # Map teams to groups (for the JS filter in group phase)
    team_group_map = {}
    if groups_list:
        all_gts = GroupTeam.query.filter(GroupTeam.group_id.in_([g.id for g in groups_list])).all()
        for gt in all_gts:
            team_group_map[gt.team_id] = gt.group_id

    return render_template('admin/matches.html',
                           event=event,
                           phases=phases_list,
                           selected_phase=selected_phase,
                           matches=matches_list,
                           groups=groups_list,
                           all_teams=available_teams,
                           team_group_map=team_group_map,
                           is_knockout=is_knockout)


@admin_bp.route('/events/<int:event_id>/matches/new', methods=['POST'])
@require_admin
def matches_new(event_id):
    phase_id = request.form.get('phase_id', type=int)
    home_id = request.form.get('home_team_id', type=int)
    away_id = request.form.get('away_team_id', type=int)
    group_id = request.form.get('group_id', type=int) or None
    match_date_str = request.form.get('match_date', '').strip()

    phase = Phase.query.get(phase_id)
    is_group_phase = ('grupo' in phase.name.lower()) or (phase.phase_order == 1)

    if is_group_phase and not group_id:
        flash('El grupo es obligatorio para esta fase.', 'danger')
        return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))

    label = ''
    if group_id:
        group = Group.query.get(group_id)
        label = f'Grupo {group.name}'
    else:
        label = phase.name

    from datetime import datetime as dt
    match_date = None
    if match_date_str:
        try:
            match_date = dt.strptime(match_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass

    if not phase_id or not home_id or not away_id:
        flash('Fase, equipo local y visitante son obligatorios.', 'danger')
    elif home_id == away_id:
        flash('El equipo local y visitante no pueden ser el mismo.', 'danger')
    else:
        # Security check: Are these teams available for this phase?
        available = get_available_teams_for_phase(event_id, phase)
        avail_ids = [t.id for t in available]
        if home_id not in avail_ids or away_id not in avail_ids:
            flash('Uno de los equipos seleccionados no es válido para esta fase (no ha clasificado).', 'danger')
        else:
            # Additional check: if group_id is provided, both teams must belong to that group
            if group_id:
                group_teams = [gt.team_id for gt in GroupTeam.query.filter_by(group_id=group_id).all()]
                if home_id not in group_teams or away_id not in group_teams:
                    flash('Error: Ambos equipos deben pertenecer al grupo seleccionado.', 'danger')
                    return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))

            m = Match(phase_id=phase_id, home_team_id=home_id, away_team_id=away_id,
                      group_id=group_id, match_label=label, match_date=match_date)
            db.session.add(m)
            db.session.commit()
            flash('Partido creado correctamente.', 'success')

    return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))


@admin_bp.route('/matches/<int:match_id>/delete', methods=['POST'])
@require_admin
def matches_delete(match_id):
    match = Match.query.get_or_404(match_id)
    event_id = match.phase.event_id
    phase_id = match.phase_id
    db.session.delete(match)
    db.session.commit()
    flash('Partido eliminado.', 'info')
    return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))


# ─── RESULTS ─────────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/results')
@require_admin
def results(event_id):
    event = Event.query.get_or_404(event_id)
    phase_id = request.args.get('phase_id', type=int)
    phases_list = Phase.query.filter_by(event_id=event_id)\
                             .order_by(Phase.phase_order).all()
    selected_phase = None
    matches_list = []
    if phase_id:
        selected_phase = Phase.query.get(phase_id)
    elif phases_list:
        selected_phase = phases_list[0]
        phase_id = selected_phase.id

    if selected_phase:
        matches_list = Match.query.filter_by(phase_id=selected_phase.id)\
                                  .order_by(Match.match_date).all()

    return render_template('admin/results.html',
                           event=event,
                           phases=phases_list,
                           selected_phase=selected_phase,
                           matches=matches_list)


@admin_bp.route('/matches/<int:match_id>/result', methods=['POST'])
@require_admin
def matches_result(match_id):
    match = Match.query.get_or_404(match_id)
    home_score = request.form.get('home_score', type=int)
    away_score = request.form.get('away_score', type=int)
    penalty_winner_id = request.form.get('penalty_winner_id', type=int) or None
    clear = request.form.get('clear_result')

    event_id = match.phase.event_id
    phase_id = match.phase_id

    if match.phase.is_prediction_open:
        flash('No puedes ingresar resultados mientras la fase de predicciones esté abierta.', 'danger')
        return redirect(url_for('admin.results', event_id=event_id, phase_id=phase_id))

    if clear:
        match.home_score = None
        match.away_score = None
        match.penalty_winner_id = None
        match.is_finished = False
        db.session.commit()
        flash('Resultado borrado.', 'info')
    elif home_score is not None and away_score is not None:
        match.home_score = home_score
        match.away_score = away_score
        match.penalty_winner_id = penalty_winner_id
        match.is_finished = True
        db.session.commit()
        updated = calculate_match_scores(match_id)
        flash(f'Resultado guardado. {updated} predicciones puntuadas.', 'success')
    else:
        flash('Debes ingresar ambos marcadores.', 'danger')

    return redirect(url_for('admin.results', event_id=event_id, phase_id=phase_id))


# ─── SCORING CONFIG ───────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/scoring', methods=['GET', 'POST'])
@require_admin
def scoring_config(event_id):
    event = Event.query.get_or_404(event_id)
    configs = ScoringConfig.query.filter_by(event_id=event_id).all()

    if request.method == 'POST':
        for cfg in configs:
            cfg.points_value = request.form.get(f'points_{cfg.score_type}', type=int, default=cfg.points_value)
            cfg.is_active = bool(request.form.get(f'active_{cfg.score_type}'))
        db.session.commit()
        # Recalculate all scores with new config
        total = recalculate_all_event_scores(event_id)
        flash(f'Configuración guardada. {total} predicciones recalculadas.', 'success')
        return redirect(url_for('admin.scoring_config', event_id=event_id))

    return render_template('admin/scoring_config.html', event=event, configs=configs)


# ─── PARTICIPANTS ─────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/participants')
@require_admin
def participants(event_id):
    event = Event.query.get_or_404(event_id)
    all_participants = Participant.query.filter_by(event_id=event_id)\
                                       .order_by(Participant.total_points.desc()).all()
    return render_template('admin/participants.html',
                           event=event, participants=all_participants)


@admin_bp.route('/participants/<int:participant_id>')
@require_admin
def participant_detail(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    event = participant.event
    phases = Phase.query.filter_by(event_id=event.id).order_by(Phase.phase_order).all()

    phase_data = []
    for phase in phases:
        preds = (Prediction.query
                 .filter_by(participant_id=participant_id, phase_id=phase.id)
                 .join(Match)
                 .order_by(Match.match_date)
                 .all())
        
        pred_list = []
        for p in preds:
            score = Score.query.filter_by(
                participant_id=participant_id,
                match_id=p.match_id
            ).first()
            
            pred_list.append({
                'prediction': p,
                'match': p.match,
                'points': score.points_earned if score else None,
                'score_type': score.score_type if score else None
            })
            
        phase_data.append({'phase': phase, 'predictions': pred_list})

    return render_template('admin/participant_detail.html',
                           participant=participant,
                           event=event,
                           phase_data=phase_data)


# ─── RANKING ─────────────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/ranking')
@require_admin
def ranking(event_id):
    event = Event.query.get_or_404(event_id)
    all_participants = Participant.query.filter_by(event_id=event_id)\
                                       .order_by(Participant.total_points.desc(),
                                                 Participant.created_at).all()
    return render_template('admin/ranking.html',
                           event=event, participants=all_participants)
