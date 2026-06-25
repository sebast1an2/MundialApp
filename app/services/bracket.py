"""
Bracket advancement engine.

Entry point: advance_bracket(finished_match)

Called automatically by the admin results route after a match result is saved.
Only operates on matches that have bracket source links configured
(home_source_match_id / away_source_match_id). Legacy events with no bracket
links are completely unaffected — the queries return empty lists and the
function returns early.

Invariants (never violated):
  - Never overwrites an occupied team slot (home_team_id / away_team_id not None).
  - Never modifies a destination match that has already started or finished.
  - Never modifies scoring, predictions, ranking, or public views.
  - A 'draw' result without a penalty_winner_id does not trigger advancement
    (admin must enter the penalty winner first).
"""

import logging
from app import db
from app.models import Match

log = logging.getLogger(__name__)


def _resolve_team(match: Match, outcome: str):
    """Return the team_id that advances based on the outcome string."""
    result = match.get_result()
    if result == 'home':
        winner_id = match.home_team_id
        loser_id  = match.away_team_id
    elif result == 'away':
        winner_id = match.away_team_id
        loser_id  = match.home_team_id
    else:
        # 'draw' without penalty resolution — indeterminate
        return None, result

    if outcome == 'winner':
        return winner_id, result
    if outcome == 'loser':
        return loser_id, result
    return None, result


def advance_bracket(finished_match: Match) -> dict:
    """
    Propagate the result of *finished_match* to any configured downstream
    bracket slots.

    Returns a stats dict:
      slots_filled      — slots successfully updated this call
      skipped_occupied  — slots skipped (already had a team)
      skipped_started   — slots skipped (destination match already underway)
      skipped_draw      — slots skipped (unresolved draw, no penalty winner)
    """
    stats = {
        'slots_filled':     0,
        'skipped_occupied': 0,
        'skipped_started':  0,
        'skipped_draw':     0,
    }

    # Guard 1: match must be finished with both teams present
    if not finished_match.is_finished:
        return stats
    if not finished_match.home_team_id or not finished_match.away_team_id:
        return stats

    # Find all destination matches that reference this match as a bracket source
    home_dests = Match.query.filter_by(
        home_source_match_id=finished_match.id
    ).all()
    away_dests = Match.query.filter_by(
        away_source_match_id=finished_match.id
    ).all()

    # Guard 2: no bracket links → legacy event, nothing to do
    if not home_dests and not away_dests:
        return stats

    # ── Process home-slot destinations ────────────────────────────────────────
    for dest in home_dests:
        outcome = dest.home_source_outcome or 'winner'
        team_id, result = _resolve_team(finished_match, outcome)

        if team_id is None:
            log.warning(
                "[bracket] Match %d → %d (home slot): result is '%s' with no "
                "penalty winner — enter penalty winner to advance bracket.",
                finished_match.id, dest.id, result,
            )
            stats['skipped_draw'] += 1
            continue

        if dest.home_team_id is not None:
            log.warning(
                "[bracket] Match %d → %d (home slot): already occupied by "
                "team %d — skipping.",
                finished_match.id, dest.id, dest.home_team_id,
            )
            stats['skipped_occupied'] += 1
            continue

        if dest.is_finished or dest.home_score is not None:
            log.warning(
                "[bracket] Match %d → %d (home slot): destination already "
                "started or finished — skipping.",
                finished_match.id, dest.id,
            )
            stats['skipped_started'] += 1
            continue

        dest.home_team_id = team_id
        stats['slots_filled'] += 1
        log.info(
            "[bracket] Match %d → %d home slot filled: team %d (outcome=%s).",
            finished_match.id, dest.id, team_id, outcome,
        )

    # ── Process away-slot destinations ────────────────────────────────────────
    for dest in away_dests:
        outcome = dest.away_source_outcome or 'winner'
        team_id, result = _resolve_team(finished_match, outcome)

        if team_id is None:
            log.warning(
                "[bracket] Match %d → %d (away slot): result is '%s' with no "
                "penalty winner — enter penalty winner to advance bracket.",
                finished_match.id, dest.id, result,
            )
            stats['skipped_draw'] += 1
            continue

        if dest.away_team_id is not None:
            log.warning(
                "[bracket] Match %d → %d (away slot): already occupied by "
                "team %d — skipping.",
                finished_match.id, dest.id, dest.away_team_id,
            )
            stats['skipped_occupied'] += 1
            continue

        if dest.is_finished or dest.home_score is not None:
            log.warning(
                "[bracket] Match %d → %d (away slot): destination already "
                "started or finished — skipping.",
                finished_match.id, dest.id,
            )
            stats['skipped_started'] += 1
            continue

        dest.away_team_id = team_id
        stats['slots_filled'] += 1
        log.info(
            "[bracket] Match %d → %d away slot filled: team %d (outcome=%s).",
            finished_match.id, dest.id, team_id, outcome,
        )

    # Persist only if something changed
    if stats['slots_filled'] > 0:
        db.session.commit()

    return stats
