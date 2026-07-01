from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from app import db
from app.models import (Team, Event, Group, GroupTeam, Phase,
                        Match, Participant, Prediction, Score, ScoringConfig,
                        EventTemplate, TemplatePhase, TemplateScoringConfig)
from app.routes.auth import require_admin
from app.services.seeder import seed_teams
from app.services.scoring import calculate_match_scores, recalculate_all_event_scores
from app.services.standings import calculate_event_group_standings, get_best_third_place_teams
from app.services.bracket import advance_bracket

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
        template_id = request.form.get('template_id', type=int) or None
        event = Event(
            name=request.form['name'].strip(),
            tournament_type=request.form.get('tournament_type', 'world_cup'),
            description=request.form.get('description', '').strip(),
            logo_emoji=request.form.get('logo_emoji', '🏆').strip(),
            template_id=template_id,
        )
        db.session.add(event)
        db.session.flush()

        template = EventTemplate.query.get(template_id) if template_id else None

        # Scoring: use template values if defined, otherwise fall back to system defaults
        template_scorings = template.scoring_configs.all() if template else []
        if template_scorings:
            for tc in template_scorings:
                db.session.add(ScoringConfig(
                    event_id=event.id, score_type=tc.score_type,
                    points_value=tc.points_value, is_active=tc.is_active,
                    description=tc.description,
                ))
        else:
            for d in ScoringConfig._DEFAULTS:
                db.session.add(ScoringConfig(event_id=event.id, **d))

        # Phases: pre-populate from template if it has them
        template_phases = template.get_phases_ordered() if template else []
        for tp in template_phases:
            db.session.add(Phase(
                event_id=event.id, name=tp.name, phase_order=tp.phase_order,
            ))

        db.session.commit()

        if template:
            flash(f'Evento "{event.name}" creado con la plantilla "{template.name}".', 'success')
        else:
            flash(f'Evento "{event.name}" creado.', 'success')
        return redirect(url_for('admin.event_detail', event_id=event.id))

    active_templates = EventTemplate.query.filter_by(is_active=True)\
                                          .order_by(EventTemplate.name).all()
    return render_template('admin/event_form.html', event=None, templates=active_templates)


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
        event.qualifies_third_place = bool(request.form.get('qualifies_third_place'))

        def _parse_int_field(name, default=0):
            raw = request.form.get(name, str(default)).strip()
            try:
                return max(0, int(float(raw))) if raw else default
            except (ValueError, TypeError):
                return default

        event.third_place_slots     = _parse_int_field('third_place_slots', default=0)
        event.participation_fee = _parse_int_field('participation_fee')
        event.prize_type        = request.form.get('prize_type', 'money')
        if event.prize_type not in ('money', 'percentage'):
            event.prize_type = 'money'
        event.prize_first       = _parse_int_field('prize_first')
        event.prize_second      = _parse_int_field('prize_second')
        event.prize_third       = _parse_int_field('prize_third')

        # Validar que los porcentajes no superen 100
        if event.prize_type == 'percentage':
            total_pct = int(event.prize_first or 0) + int(event.prize_second or 0) + int(event.prize_third or 0)
            if total_pct > 100:
                flash(
                    f'Error: la suma de los porcentajes no puede superar el 100% '
                    f'(actualmente suma {total_pct}%). Corrígelos antes de guardar.',
                    'danger'
                )
                return render_template('admin/event_form.html', event=event)

        event.nequi_number      = request.form.get('nequi_number', '').strip()[:20]

        # Fecha límite de pago (opcional)
        deadline_str = request.form.get('payment_deadline', '').strip()
        if deadline_str:
            from datetime import date as _date
            try:
                event.payment_deadline = _date.fromisoformat(deadline_str)
            except ValueError:
                event.payment_deadline = None
        else:
            event.payment_deadline = None

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
    # getlist() devuelve strings; PostgreSQL requiere integers en .in_()
    # (psycopg.errors.UndefinedFunction: operator does not exist: integer = character varying)
    team_ids = [int(tid) for tid in request.form.getlist('team_ids') if tid.isdigit()]
    
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
    Returns a list of Team objects eligible to participate in the given phase.
    - Group phase ('grupo' in name): teams assigned to event groups.
    - Knockout with no previous phase: ALL teams in catalog (knockout-only events).
    - Knockout with group prev phase: qualified teams from standings.
    - Knockout with knockout prev phase: winners from finished matches.
    """
    if not phase:
        return []

    # ── Group phase: teams come from event groups ──────────────────────────
    if 'grupo' in phase.name.lower():
        groups = Group.query.filter_by(event_id=event_id).all()
        group_ids = [g.id for g in groups]
        if not group_ids:
            return []
        team_ids = [gt.team_id for gt in GroupTeam.query.filter(GroupTeam.group_id.in_(group_ids)).all()]
        return Team.query.filter(Team.id.in_(team_ids)).order_by(Team.name).all()

    # ── Knockout phase ─────────────────────────────────────────────────────
    prev_phase = Phase.query.filter_by(
        event_id=event_id, phase_order=phase.phase_order - 1
    ).first()

    # No previous phase → knockout-only event (e.g. "16vos de final" as first phase).
    # Allow admin to pick from the full team catalog.
    if not prev_phase:
        return Team.query.order_by(Team.name).all()

    available_teams = []

    if 'grupo' in prev_phase.name.lower():
        # Previous phase was groups → use standings to get qualified teams
        standings = calculate_event_group_standings(event_id)
        qualified_list = []
        for g_obj, g_standings in standings.items():
            for row in g_standings[:2]:
                qualified_list.append(row['team'])

        from app.models import Event as _Event
        _event = _Event.query.get(event_id)
        if _event and _event.qualifies_third_place and (_event.third_place_slots or 0) > 0:
            best_thirds = get_best_third_place_teams(event_id, _event.third_place_slots)
            qualified_list.extend(best_thirds)

        team_ids = list(set([t.id for t in qualified_list]))
        available_teams = Team.query.filter(Team.id.in_(team_ids)).order_by(Team.name).all()
    else:
        # Previous phase was also knockout.
        #
        # Base pool — ALWAYS include all teams that participated in prev_phase.
        # This ensures the admin always sees the full set of eligible teams
        # when adding a new match, regardless of how many matches in this phase
        # already have fixture (source) links configured.
        #
        # Additionally, if existing matches in this phase have fixture connections
        # (home_source_match_id / away_source_match_id), also include teams from
        # those upstream source matches (e.g. upstream TBD or already-finished
        # matches), so the full candidate pool is always available.
        #
        # NOTE: advance_bracket uses FK links directly and never calls this
        # function, so this change has no effect on automatic bracket advancement.

        all_team_ids = set()

        # ── Step 1: always seed pool with ALL teams from the previous phase ──
        prev_matches = Match.query.filter_by(phase_id=prev_phase.id).all()
        upstream_source_ids = set()
        for m in prev_matches:
            if m.home_team_id: all_team_ids.add(m.home_team_id)
            if m.away_team_id: all_team_ids.add(m.away_team_id)
            if m.home_source_match_id: upstream_source_ids.add(m.home_source_match_id)
            if m.away_source_match_id: upstream_source_ids.add(m.away_source_match_id)

        # Walk one level further back (e.g. TBD slots in prev_phase fed by upstream matches)
        if upstream_source_ids:
            for m in Match.query.filter(Match.id.in_(upstream_source_ids)).all():
                if m.home_team_id: all_team_ids.add(m.home_team_id)
                if m.away_team_id: all_team_ids.add(m.away_team_id)

        # ── Step 2: also add teams from fixture-linked source matches in THIS phase ──
        # (covers cases where an existing match points to a source not yet in prev_phase)
        this_phase_matches = Match.query.filter_by(phase_id=phase.id).all()
        linked_source_ids  = set()
        needs_winner       = False
        needs_loser        = False

        for cm in this_phase_matches:
            if cm.home_source_match_id:
                linked_source_ids.add(cm.home_source_match_id)
                if (cm.home_source_outcome or 'winner') == 'loser':
                    needs_loser = True
                else:
                    needs_winner = True
            if cm.away_source_match_id:
                linked_source_ids.add(cm.away_source_match_id)
                if (cm.away_source_outcome or 'winner') == 'loser':
                    needs_loser = True
                else:
                    needs_winner = True

        if linked_source_ids:
            source_matches = Match.query.filter(Match.id.in_(linked_source_ids)).all()
            for m in source_matches:
                if not m.is_finished:
                    if m.home_team_id: all_team_ids.add(m.home_team_id)
                    if m.away_team_id: all_team_ids.add(m.away_team_id)
                else:
                    result = m.get_result()
                    w = m.home_team_id if result == 'home' else (
                        m.away_team_id if result == 'away' else None)
                    l = m.away_team_id if result == 'home' else (
                        m.home_team_id if result == 'away' else None)
                    if needs_winner and w: all_team_ids.add(w)
                    if needs_loser  and l: all_team_ids.add(l)

        if all_team_ids:
            available_teams = Team.query.filter(
                Team.id.in_(list(all_team_ids))
            ).order_by(Team.name).all()

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
        is_knockout = 'grupo' not in selected_phase.name.lower()

    # Map teams to groups (for the JS filter in group phase)
    team_group_map = {}
    if groups_list:
        all_gts = GroupTeam.query.filter(GroupTeam.group_id.in_([g.id for g in groups_list])).all()
        for gt in all_gts:
            team_group_map[gt.team_id] = gt.group_id

    # Bracket infrastructure: matches from the previous phase available as sources
    bracket_source_matches = []
    if is_knockout and selected_phase:
        prev_phase = Phase.query.filter_by(
            event_id=event_id, phase_order=selected_phase.phase_order - 1
        ).first()
        if prev_phase:
            bracket_source_matches = Match.query.filter_by(phase_id=prev_phase.id)\
                .order_by(Match.bracket_position, Match.match_date).all()

    return render_template('admin/matches.html',
                           event=event,
                           phases=phases_list,
                           selected_phase=selected_phase,
                           matches=matches_list,
                           groups=groups_list,
                           all_teams=available_teams,
                           team_group_map=team_group_map,
                           is_knockout=is_knockout,
                           bracket_source_matches=bracket_source_matches)


@admin_bp.route('/events/<int:event_id>/matches/new', methods=['POST'])
@require_admin
def matches_new(event_id):
    phase_id       = request.form.get('phase_id',       type=int)
    home_id        = request.form.get('home_team_id',   type=int) or None
    away_id        = request.form.get('away_team_id',   type=int) or None
    group_id       = request.form.get('group_id',       type=int) or None
    match_date_str = request.form.get('match_date', '').strip()

    # Bracket infrastructure fields (all optional)
    home_source_id      = request.form.get('home_source_match_id', type=int) or None
    away_source_id      = request.form.get('away_source_match_id', type=int) or None
    home_source_outcome = request.form.get('home_source_outcome') or 'winner'
    away_source_outcome = request.form.get('away_source_outcome') or 'winner'
    bracket_position    = request.form.get('bracket_position',    type=int) or None

    phase = Phase.query.get(phase_id)
    if not phase:
        flash('Fase no encontrada.', 'danger')
        return redirect(url_for('admin.matches', event_id=event_id))

    is_group_phase = 'grupo' in phase.name.lower()

    from datetime import datetime as dt
    match_date = None
    if match_date_str:
        try:
            match_date = dt.strptime(match_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass

    if group_id:
        group = Group.query.get(group_id)
        label = f'Grupo {group.name}' if group else phase.name
    else:
        label = phase.name

    # ── Validaciones ──────────────────────────────────────────────────────────
    if is_group_phase:
        # Comportamiento original: grupo y ambos equipos obligatorios
        if not group_id:
            flash('El grupo es obligatorio para esta fase.', 'danger')
            return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))
        if not home_id or not away_id:
            flash('Fase de grupos: los equipos local y visitante son obligatorios.', 'danger')
            return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))

    # Mismo equipo en ambos slots solo aplica si están los dos definidos
    if home_id and away_id and home_id == away_id:
        flash('El equipo local y visitante no pueden ser el mismo.', 'danger')
        return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))

    # Validación de disponibilidad de equipos: solo si ambos están presentes
    if home_id and away_id:
        available = get_available_teams_for_phase(event_id, phase)
        avail_ids = [t.id for t in available]
        if home_id not in avail_ids or away_id not in avail_ids:
            flash('Uno de los equipos seleccionados no es válido para esta fase (no ha clasificado).', 'danger')
            return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))
        if group_id:
            group_team_ids = [gt.team_id for gt in GroupTeam.query.filter_by(group_id=group_id).all()]
            if home_id not in group_team_ids or away_id not in group_team_ids:
                flash('Error: Ambos equipos deben pertenecer al grupo seleccionado.', 'danger')
                return redirect(url_for('admin.matches', event_id=event_id, phase_id=phase_id))

    m = Match(
        phase_id=phase_id,
        home_team_id=home_id,
        away_team_id=away_id,
        group_id=group_id,
        match_label=label,
        match_date=match_date,
        home_source_match_id=home_source_id,
        away_source_match_id=away_source_id,
        home_source_outcome=home_source_outcome,
        away_source_outcome=away_source_outcome,
        bracket_position=bracket_position,
    )
    db.session.add(m)
    db.session.commit()

    if home_id and away_id:
        flash('Partido creado correctamente.', 'success')
    else:
        flash('Slot de bracket creado (TBD). Los equipos se completarán al definirse los clasificados.', 'success')

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


@admin_bp.route('/matches/<int:match_id>/toggle-lock', methods=['POST'])
@require_admin
def matches_toggle_lock(match_id):
    match = Match.query.get_or_404(match_id)
    match.is_locked = not match.is_locked
    db.session.commit()
    state = 'bloqueado' if match.is_locked else 'desbloqueado'
    flash(f'El partido ha sido {state} para predicciones.', 'success')
    return redirect(url_for('admin.matches', event_id=match.phase.event_id, phase_id=match.phase_id))


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
        # Excluir partidos TBD (sin equipos definidos) — no se puede cargar resultado en ellos
        matches_list = Match.query.filter_by(phase_id=selected_phase.id)\
                                  .filter(Match.home_team_id.isnot(None),
                                          Match.away_team_id.isnot(None))\
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

    if not match.home_team_id or not match.away_team_id:
        flash('No se puede registrar resultado: los equipos de este partido aún no están definidos (TBD).', 'danger')
        return redirect(url_for('admin.results', event_id=event_id, phase_id=phase_id))

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

        # Bracket advancement — only fires when bracket source links exist;
        # legacy events without bracket config are completely unaffected.
        adv = advance_bracket(match)
        if adv['slots_filled'] > 0:
            bracket_msg = (
                f' {adv["slots_filled"]} equipo(s) avanzaron automáticamente en el bracket.'
            )
        elif adv['skipped_draw'] > 0:
            bracket_msg = (
                ' Avance pendiente: el partido terminó en empate — '
                'ingresa el ganador de penales para avanzar el bracket.'
            )
        else:
            bracket_msg = ''

        flash(f'Resultado guardado. {updated} predicciones puntuadas.{bracket_msg}', 'success')
    else:
        flash('Debes ingresar ambos marcadores.', 'danger')

    return redirect(url_for('admin.results', event_id=event_id, phase_id=phase_id))


# ─── SCORING CONFIG ───────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/scoring', methods=['GET', 'POST'])
@require_admin
def scoring_config(event_id):
    event = Event.query.get_or_404(event_id)
    configs = ScoringConfig.query.filter_by(event_id=event_id).all()

    # Auto-seed correct_penalty_winner for events created before this feature existed
    existing_types = {c.score_type for c in configs}
    if 'correct_penalty_winner' not in existing_types:
        db.session.add(ScoringConfig(
            event_id=event_id,
            score_type='correct_penalty_winner',
            points_value=1,
            is_active=True,
            description='Bonus: adivinaste qué equipo clasifica en penales (solo en empates de eliminatoria)',
        ))
        db.session.commit()
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
    filter_val = request.args.get('filter', 'all')  # 'all' | 'pending' | 'paid' | 'predicted' | 'no_predicted'
    all_participants = Participant.query.filter_by(event_id=event_id)\
                                       .order_by(Participant.total_points.desc()).all()

    # Build a set of participant IDs that have at least one prediction in this event.
    # Uses a single DB query over the existing Prediction table — no schema changes.
    participant_ids_in_event = [p.id for p in all_participants]
    if participant_ids_in_event:
        rows = (db.session.query(Prediction.participant_id)
                .filter(Prediction.participant_id.in_(participant_ids_in_event))
                .distinct()
                .all())
        participants_with_predictions = {row[0] for row in rows}
    else:
        participants_with_predictions = set()

    if filter_val == 'pending':
        display_participants = [p for p in all_participants if not p.payment_confirmed]
    elif filter_val == 'paid':
        display_participants = [p for p in all_participants if p.payment_confirmed]
    elif filter_val == 'predicted':
        display_participants = [p for p in all_participants if p.id in participants_with_predictions]
    elif filter_val == 'no_predicted':
        display_participants = [p for p in all_participants if p.id not in participants_with_predictions]
    else:
        display_participants = all_participants

    return render_template('admin/participants.html',
                           event=event,
                           participants=all_participants,
                           display_participants=display_participants,
                           participants_with_predictions=participants_with_predictions,
                           filter=filter_val)


@admin_bp.route('/participants/<int:participant_id>/toggle-payment', methods=['POST'])
@require_admin
def toggle_payment(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    participant.payment_confirmed = not participant.payment_confirmed
    db.session.commit()
    state = 'confirmado' if participant.payment_confirmed else 'pendiente'
    flash(f'Pago de "{participant.name}" marcado como {state}.', 'success')
    redirect_filter = request.form.get('redirect_filter', 'all')
    return redirect(url_for('admin.participants',
                            event_id=participant.event_id,
                            filter=redirect_filter))


@admin_bp.route('/participants/<int:participant_id>/delete', methods=['POST'])
@require_admin
def delete_participant(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    event_id = participant.event_id
    name = participant.name

    # Eliminate scores and predictions explicitly (belt-and-suspenders with cascade)
    match_ids = [p.match_id for p in Prediction.query.filter_by(participant_id=participant_id).all()]
    Score.query.filter_by(participant_id=participant_id).delete(synchronize_session=False)
    Prediction.query.filter_by(participant_id=participant_id).delete(synchronize_session=False)
    db.session.delete(participant)
    db.session.commit()

    # Recalculate totals for remaining participants in the event so stats stay consistent
    from app.services.scoring import recalculate_participant_totals
    recalculate_participant_totals(event_id)

    redirect_filter = request.form.get('redirect_filter', 'all')
    flash(f'Participante "{name}" eliminado junto con todas sus predicciones y puntuaciones.', 'info')
    return redirect(url_for('admin.participants', event_id=event_id, filter=redirect_filter))


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


# ─── TEMPLATES ───────────────────────────────────────────────────────────────

@admin_bp.route('/templates')
@require_admin
def templates():
    all_templates = EventTemplate.query.order_by(EventTemplate.created_at.desc()).all()
    return render_template('admin/templates.html', templates=all_templates)


@admin_bp.route('/templates/new', methods=['GET', 'POST'])
@require_admin
def templates_new():
    if request.method == 'POST':
        template = EventTemplate(
            name=request.form['name'].strip(),
            description=request.form.get('description', '').strip(),
            logo_emoji=request.form.get('logo_emoji', '📋').strip(),
            uses_bracket=bool(request.form.get('uses_bracket')),
            allows_group_stage=bool(request.form.get('allows_group_stage')),
            allows_knockout=bool(request.form.get('allows_knockout')),
        )
        db.session.add(template)
        db.session.flush()
        TemplateScoringConfig.create_defaults(template.id)
        flash(f'Plantilla "{template.name}" creada con puntuación por defecto.', 'success')
        return redirect(url_for('admin.template_detail', template_id=template.id))
    return render_template('admin/template_form.html', template=None)


@admin_bp.route('/templates/<int:template_id>')
@require_admin
def template_detail(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    phases = template.get_phases_ordered()
    scoring_configs = template.scoring_configs.all()
    events_using = Event.query.filter_by(template_id=template_id).count()
    return render_template('admin/template_detail.html',
                           template=template,
                           phases=phases,
                           scoring_configs=scoring_configs,
                           events_using=events_using)


@admin_bp.route('/templates/<int:template_id>/edit', methods=['GET', 'POST'])
@require_admin
def templates_edit(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    if request.method == 'POST':
        template.name = request.form['name'].strip()
        template.description = request.form.get('description', '').strip()
        template.logo_emoji = request.form.get('logo_emoji', '📋').strip()
        template.is_active = bool(request.form.get('is_active'))
        template.uses_bracket = bool(request.form.get('uses_bracket'))
        template.allows_group_stage = bool(request.form.get('allows_group_stage'))
        template.allows_knockout = bool(request.form.get('allows_knockout'))
        db.session.commit()
        flash('Plantilla actualizada.', 'success')
        return redirect(url_for('admin.template_detail', template_id=template_id))
    return render_template('admin/template_form.html', template=template)


@admin_bp.route('/templates/<int:template_id>/toggle', methods=['POST'])
@require_admin
def templates_toggle(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    template.is_active = not template.is_active
    db.session.commit()
    state = 'activada' if template.is_active else 'desactivada'
    flash(f'Plantilla "{template.name}" {state}.', 'success')
    return redirect(url_for('admin.templates'))


@admin_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@require_admin
def templates_delete(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    name = template.name
    events_count = Event.query.filter_by(template_id=template_id).count()
    # ON DELETE SET NULL in the DB handles the FK on events automatically
    db.session.delete(template)
    db.session.commit()
    if events_count:
        flash(f'Plantilla "{name}" eliminada. Los {events_count} evento(s) asociados continúan funcionando normalmente.', 'info')
    else:
        flash(f'Plantilla "{name}" eliminada.', 'info')
    return redirect(url_for('admin.templates'))


# ── Template phases ───────────────────────────────────────────────────────────

@admin_bp.route('/templates/<int:template_id>/phases', methods=['POST'])
@require_admin
def template_phases_new(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    name = request.form.get('name', '').strip()
    order = request.form.get('phase_order', type=int, default=1)
    phase_type = request.form.get('phase_type', 'group')
    teams_qualify = request.form.get('teams_qualify', type=int) or None
    is_bracket_round = bool(request.form.get('is_bracket_round'))

    if not name:
        flash('El nombre de la fase es requerido.', 'danger')
    else:
        db.session.add(TemplatePhase(
            template_id=template_id, name=name, phase_order=order,
            phase_type=phase_type, teams_qualify=teams_qualify,
            is_bracket_round=is_bracket_round,
        ))
        db.session.commit()
        flash(f'Fase "{name}" añadida a la plantilla.', 'success')
    return redirect(url_for('admin.template_detail', template_id=template_id))


@admin_bp.route('/template-phases/<int:phase_id>/delete', methods=['POST'])
@require_admin
def template_phases_delete(phase_id):
    phase = TemplatePhase.query.get_or_404(phase_id)
    template_id = phase.template_id
    name = phase.name
    db.session.delete(phase)
    db.session.commit()
    flash(f'Fase "{name}" eliminada de la plantilla.', 'info')
    return redirect(url_for('admin.template_detail', template_id=template_id))


# ─── BRACKET CONFIG ──────────────────────────────────────────────────────────

@admin_bp.route('/events/<int:event_id>/bracket')
@require_admin
def bracket(event_id):
    event = Event.query.get_or_404(event_id)
    all_phases = Phase.query.filter_by(event_id=event_id)\
                            .order_by(Phase.phase_order).all()

    # Knockout phases: all phases not labeled as group stage
    ko_phases = [p for p in all_phases if 'grupo' not in p.name.lower()]

    if not ko_phases:
        return render_template('admin/bracket.html',
                               event=event, phase_data=[], match_by_id={}, teams_by_id={})

    ko_phase_ids    = [p.id for p in ko_phases]
    phase_order_by_id = {p.id: p.phase_order for p in ko_phases}
    phase_name_by_id  = {p.id: p.name        for p in ko_phases}

    # Load all knockout matches in one query
    all_ko_matches = Match.query\
        .filter(Match.phase_id.in_(ko_phase_ids))\
        .order_by(Match.phase_id, Match.bracket_position, Match.match_date)\
        .all()
    match_by_id = {m.id: m for m in all_ko_matches}

    # Batch-load teams referenced in knockout matches (avoid N+1)
    team_ids = {m.home_team_id for m in all_ko_matches if m.home_team_id} | \
               {m.away_team_id for m in all_ko_matches if m.away_team_id}
    teams_by_id = {t.id: t for t in Team.query.filter(Team.id.in_(team_ids)).all()} \
                  if team_ids else {}

    def _team_short(team_id):
        t = teams_by_id.get(team_id)
        if not t:
            return 'TBD'
        return t.short_name or t.name[:3].upper()

    def _match_opt_label(m):
        home = _team_short(m.home_team_id)
        away = _team_short(m.away_team_id)
        lbl  = m.match_label or f'#{m.id}'
        return f'{phase_name_by_id.get(m.phase_id, "?")} · {lbl} ({home} vs {away})'

    # Organize data per phase
    matches_by_phase_id = {}
    for m in all_ko_matches:
        matches_by_phase_id.setdefault(m.phase_id, []).append(m)

    phase_data = []
    for phase in ko_phases:
        phase_matches = sorted(
            matches_by_phase_id.get(phase.id, []),
            key=lambda m: (m.bracket_position or 9999, str(m.match_date or ''))
        )
        # Source options: knockout matches from phases with LOWER phase_order
        source_opts = [
            {'id': m.id, 'label': _match_opt_label(m)}
            for m in all_ko_matches
            if phase_order_by_id.get(m.phase_id, 0) < phase.phase_order
        ]
        source_opts.sort(key=lambda o: o['label'])

        phase_data.append({
            'phase':       phase,
            'matches':     phase_matches,
            'source_opts': source_opts,
            'teams_by_id': teams_by_id,
        })

    return render_template('admin/bracket.html',
                           event=event,
                           phase_data=phase_data,
                           match_by_id=match_by_id,
                           teams_by_id=teams_by_id)


@admin_bp.route('/matches/<int:match_id>/bracket-link', methods=['POST'])
@require_admin
def bracket_link_save(match_id):
    match = Match.query.get_or_404(match_id)
    event_id = match.phase.event_id

    match.home_source_match_id = request.form.get('home_source_match_id', type=int) or None
    match.home_source_outcome  = request.form.get('home_source_outcome')  or 'winner'
    match.away_source_match_id = request.form.get('away_source_match_id', type=int) or None
    match.away_source_outcome  = request.form.get('away_source_outcome')  or 'winner'
    match.bracket_position     = request.form.get('bracket_position',     type=int) or None

    db.session.commit()
    label = match.match_label or f'Partido #{match.id}'
    flash(f'Conexiones de "{label}" actualizadas.', 'success')
    return redirect(url_for('admin.bracket', event_id=event_id))


# ── Template scoring ──────────────────────────────────────────────────────────

@admin_bp.route('/templates/<int:template_id>/scoring', methods=['POST'])
@require_admin
def template_scoring_update(template_id):
    template = EventTemplate.query.get_or_404(template_id)
    configs = TemplateScoringConfig.query.filter_by(template_id=template_id).all()
    for cfg in configs:
        cfg.points_value = request.form.get(f'points_{cfg.score_type}', type=int,
                                            default=cfg.points_value)
        cfg.is_active = bool(request.form.get(f'active_{cfg.score_type}'))
    db.session.commit()
    flash('Configuración de puntuación de la plantilla actualizada.', 'success')
    return redirect(url_for('admin.template_detail', template_id=template_id))
