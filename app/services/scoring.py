from datetime import datetime
from app import db
from app.models import Match, Prediction, Score, ScoringConfig, Participant


def _get_result(home, away):
    if home > away:
        return 'home'
    elif away > home:
        return 'away'
    return 'draw'


def calculate_match_scores(match_id):
    """
    Calculate and upsert scores for all predictions of a finished match.
    Recalculates total_points for all affected participants.
    """
    match = Match.query.get(match_id)
    if not match or not match.is_finished:
        return 0

    event = match.phase.event
    configs = {
        c.score_type: c
        for c in ScoringConfig.query.filter_by(event_id=event.id, is_active=True).all()
    }

    # Auto-seed correct_penalty_winner for events created before this feature.
    # Only seeds if the row doesn't exist at all (respects admin disabling it).
    if 'correct_penalty_winner' not in configs:
        existing = ScoringConfig.query.filter_by(
            event_id=event.id, score_type='correct_penalty_winner'
        ).first()
        if not existing:
            new_cfg = ScoringConfig(
                event_id=event.id,
                score_type='correct_penalty_winner',
                points_value=1,
                is_active=True,
                description='Bonus: adivinaste qué equipo clasifica en penales (solo empates de eliminatoria)',
            )
            db.session.add(new_cfg)
            db.session.flush()
            configs['correct_penalty_winner'] = new_cfg

    real_result = _get_result(match.home_score, match.away_score)
    predictions = Prediction.query.filter_by(match_id=match_id).all()
    updated = 0

    for pred in predictions:
        points = 0
        score_type = 'none'

        pred_home = pred.home_pred
        pred_away = pred.away_pred
        pred_result = _get_result(pred_home, pred_away)

        # Check exact score first (higher priority)
        if (pred_home == match.home_score and pred_away == match.away_score):
            cfg = configs.get('exact_score')
            if cfg:
                points = cfg.points_value
                score_type = 'exact_score'
        # Check correct winner/draw
        elif pred_result == real_result:
            cfg = configs.get('correct_winner')
            if cfg:
                points = cfg.points_value
                score_type = 'correct_winner'

        # Bonus: correct penalty winner.
        # Conditions: base result correct + match had penalties + participant predicted one.
        if (score_type != 'none'
                and match.penalty_winner_id
                and pred.predicted_penalty_winner_id
                and pred.predicted_penalty_winner_id == match.penalty_winner_id):
            pen_cfg = configs.get('correct_penalty_winner')
            if pen_cfg:
                points += pen_cfg.points_value
                score_type = score_type + '+pen'

        # Upsert score record
        score = Score.query.filter_by(
            participant_id=pred.participant_id,
            match_id=match_id
        ).first()

        if score:
            score.points_earned = points
            score.score_type = score_type
            score.calculated_at = datetime.utcnow()
        else:
            score = Score(
                participant_id=pred.participant_id,
                match_id=match_id,
                points_earned=points,
                score_type=score_type,
            )
            db.session.add(score)

        updated += 1

    db.session.commit()

    # Recalculate totals for participants of this event
    recalculate_participant_totals(event.id)

    return updated


def recalculate_participant_totals(event_id):
    """Recompute total_points for all participants of an event from Score table."""
    participants = Participant.query.filter_by(event_id=event_id).all()
    for p in participants:
        total = db.session.query(db.func.sum(Score.points_earned))\
                          .filter(Score.participant_id == p.id)\
                          .scalar() or 0
        p.total_points = int(total)
    db.session.commit()


def recalculate_all_event_scores(event_id):
    """Full recalculation: useful when scoring config changes."""
    from app.models import Phase
    phases = Phase.query.filter_by(event_id=event_id).all()
    total = 0
    for phase in phases:
        for match in phase.matches.filter_by(is_finished=True).all():
            total += calculate_match_scores(match.id)
    return total
