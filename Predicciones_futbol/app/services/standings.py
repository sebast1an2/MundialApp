from app import db
from app.models import Group, GroupTeam, Match, Team


def calculate_group_standings(group_id):
    """
    Dynamically compute standings for a group from finished match results.
    Returns a list of dicts sorted by PTS, DIF, GF.
    """
    group_teams = GroupTeam.query.filter_by(group_id=group_id).all()
    standings = []

    for gt in group_teams:
        team = gt.team
        stats = {
            'team': team,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0,
            'gf': 0, 'gc': 0, 'dif': 0, 'pts': 0,
        }

        # Fetch finished matches involving this team in this group
        matches = Match.query.filter(
            Match.group_id == group_id,
            Match.is_finished == True,
            db.or_(
                Match.home_team_id == team.id,
                Match.away_team_id == team.id,
            )
        ).all()

        for match in matches:
            stats['pj'] += 1
            if match.home_team_id == team.id:
                gf, gc = match.home_score, match.away_score
            else:
                gf, gc = match.away_score, match.home_score

            stats['gf'] += gf
            stats['gc'] += gc
            stats['dif'] += (gf - gc)

            if gf > gc:
                stats['pg'] += 1
                stats['pts'] += 3
            elif gf == gc:
                stats['pe'] += 1
                stats['pts'] += 1
            else:
                stats['pp'] += 1

        standings.append(stats)

    # Sort: PTS desc, DIF desc, GF desc
    standings.sort(key=lambda x: (-x['pts'], -x['dif'], -x['gf']))
    return standings


def calculate_event_group_standings(event_id):
    """Return standings for all groups of an event as a dict {group: [standings]}."""
    groups = Group.query.filter_by(event_id=event_id).order_by(Group.name).all()
    result = {}
    for group in groups:
        result[group] = calculate_group_standings(group.id)
    return result


def calculate_top_scoring_teams(event_id, limit=5):
    """Returns a list of teams with most goals in the event across all phases."""
    from app.models import Phase, Match
    phase_ids = [p.id for p in Phase.query.filter_by(event_id=event_id).all()]
    if not phase_ids:
        return []

    # Get all finished matches in these phases
    matches = Match.query.filter(Match.phase_id.in_(phase_ids), Match.is_finished == True).all()
    
    stats = {} # team_id -> {'team': Team, 'goals': 0}
    
    for m in matches:
        # Home team
        if m.home_team_id not in stats:
            stats[m.home_team_id] = {'team': m.home_team, 'goals': 0}
        stats[m.home_team_id]['goals'] += (m.home_score or 0)
        
        # Away team
        if m.away_team_id not in stats:
            stats[m.away_team_id] = {'team': m.away_team, 'goals': 0}
        stats[m.away_team_id]['goals'] += (m.away_score or 0)
        
    # Convert to list and sort
    top_teams = list(stats.values())
    top_teams.sort(key=lambda x: (-x['goals'], x['team'].name))
    
    return top_teams[:limit]
