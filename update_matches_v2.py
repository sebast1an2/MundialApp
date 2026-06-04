import os
from app import create_app, db
from app.models import Event, Phase, Group, Match, Team
from datetime import datetime

app = create_app()

matches_data = """
06/11/2026 15:00, México vs. Sudáfrica, Grupo A
06/11/2026 22:00, República de Corea vs. República Checa, Grupo A
06/12/2026 15:00, Canadá vs. Bosnia y Herzegovina, Grupo B
06/12/2026 21:00, Estados Unidos vs. Paraguay, Grupo D
06/13/2026 15:00, Catar vs. Suiza, Grupo B
06/13/2026 18:00, Brasil vs. Marruecos, Grupo C
06/13/2026 21:00, Haití vs. Escocia, Grupo C
06/13/2026 00:00*, Australia vs. Turquía, Grupo D
06/14/2026 13:00, Alemania vs. Curazao, Grupo E
06/14/2026 16:00, Países Bajos vs. Japón, Grupo F
06/14/2026 19:00, Costa de Marfil vs. Ecuador, Grupo E
06/14/2026 22:00, Suecia vs. Túnez, Grupo F
06/15/2026 12:00, España vs. Cabo Verde, Grupo H
06/15/2026 15:00, Bélgica vs. Egipto, Grupo G
06/15/2026 18:00, Arabia Saudí vs. Uruguay, Grupo H
06/15/2026 21:00, RI de Irán vs. Nueva Zelanda, Grupo G
06/16/2026 15:00, Francia vs. Senegal, Grupo I
06/16/2026 18:00, Irak vs. Noruega, Grupo I
06/16/2026 21:00, Argentina vs. Argelia, Grupo J
06/16/2026 00:00*, Austria vs. Jordania, Grupo J
06/17/2026 13:00, Portugal vs. RD Congo, Grupo K
06/17/2026 16:00, Inglaterra vs. Croacia, Grupo L
06/17/2026 19:00, Ghana vs. Panamá, Grupo L
06/17/2026 22:00, Uzbekistán vs. Colombia, Grupo K
06/18/2026 12:00, República Checa vs. Sudáfrica, Grupo A
06/18/2026 15:00, Suiza vs. Bosnia y Herzegovina, Grupo B
06/18/2026 18:00, Canadá vs. Catar, Grupo B
06/18/2026 21:00, México vs. República de Corea, Grupo A
06/19/2026 15:00, Estados Unidos vs. Australia, Grupo D
06/19/2026 18:00, Escocia vs. Marruecos, Grupo C
06/19/2026 21:00, Brasil vs. Haití, Grupo C
06/19/2026 00:00*, Turquía vs. Paraguay, Grupo D
06/20/2026 13:00, Países Bajos vs. Suecia, Grupo F
06/20/2026 16:00, Alemania vs. Costa de Marfil, Grupo E
06/20/2026 22:00, Ecuador vs. Curazao, Grupo E
06/20/2026 00:00*, Túnez vs. Japón, Grupo F
06/21/2026 12:00, España vs. Arabia Saudí, Grupo H
06/21/2026 15:00, Bélgica vs. Irán, Grupo G
06/21/2026 18:00, Uruguay vs. Cabo Verde, Grupo H
06/21/2026 21:00, Nueva Zelanda vs. Egipto, Grupo G
06/22/2026 13:00, Argentina vs. Austria, Grupo J
06/22/2026 17:00, Francia vs. Irak, Grupo I
06/22/2026 20:00, Noruega vs. Senegal, Grupo I
06/22/2026 23:00, Jordania vs. Argelia, Grupo J
06/23/2026 13:00, Portugal vs. Uzbekistán, Grupo K
06/23/2026 16:00, Inglaterra vs. Ghana, Grupo L
06/23/2026 19:00, Panamá vs. Croacia, Grupo L
06/23/2026 22:00, Colombia vs. RD Congo, Grupo K
06/24/2026 15:00, Suiza vs. Canadá, Grupo B
06/24/2026 15:00, Bosnia y Herzegovina vs. Catar, Grupo B
06/24/2026 18:00, Escocia vs. Brasil, Grupo C
06/24/2026 18:00, Marruecos vs. Haití, Grupo C
06/24/2026 21:00, República Checa vs. México, Grupo A
06/24/2026 21:00, Sudáfrica vs. República de Corea, Grupo A
06/25/2026 16:00, Curazao vs. Costa de Marfil, Grupo E
06/25/2026 16:00, Ecuador vs. Alemania, Grupo E
06/25/2026 19:00, Japón vs. Suecia, Grupo F
06/25/2026 19:00, Túnez vs. Países Bajos, Grupo F
06/25/2026 22:00, Turquía vs. Estados Unidos, Grupo D
06/25/2026 22:00, Paraguay vs. Australia, Grupo D
06/26/2026 15:00, Noruega vs. Francia, Grupo I
06/26/2026 15:00, Senegal vs. Irak, Grupo I
06/26/2026 20:00, Cabo Verde vs. Arabia Saudí, Grupo H
06/26/2026 20:00, Uruguay vs. España, Grupo H
06/26/2026 23:00, Egipto vs. Irán, Grupo G
06/26/2026 23:00, Nueva Zelanda vs. Bélgica, Grupo G
06/27/2026 17:00, Panamá vs. Inglaterra, Grupo L
06/27/2026 17:00, Croacia vs. Ghana, Grupo L
06/27/2026 19:30, Colombia vs. Portugal, Grupo K
06/27/2026 19:30, RD Congo vs. Uzbekistán, Grupo K
06/27/2026 22:00, Argelia vs. Austria, Grupo J
06/27/2026 22:00, Jordania vs. Argentina, Grupo J
"""

def normalize_name(name):
    name = name.strip()
    mapping = {
        "RD Congo": "R.D. Congo",
        "República Checa": "Rep. Checa",
        "República de Corea": "Corea del Sur",
        "Catar": "Qatar",
        "RI de Irán": "Irán",
        "Arabia Saudí": "Arabia Saudita"
    }
    return mapping.get(name, name)

with app.app_context():
    event = Event.query.first()
    if not event:
        print("No event found.")
        exit()
        
    phase = Phase.query.filter_by(event_id=event.id, phase_order=1).first()
    if not phase:
        print("No phase found.")
        exit()
        
    lines = matches_data.strip().split('\n')
    updated = 0
    not_found = 0
    
    for line in lines:
        if not line.strip(): continue
        parts = line.split(',')
        if len(parts) != 3: continue
        
        date_str = parts[0].strip().replace('*', '') # "06/11/2026 15:00"
        teams_str = parts[1].strip()
        
        # Split teams_str by " vs. "
        team_parts = teams_str.split(' vs. ')
        if len(team_parts) != 2:
            print(f"Error parsing teams: {teams_str}")
            continue
            
        home_name = normalize_name(team_parts[0])
        away_name = normalize_name(team_parts[1])
        
        try:
            match_date = datetime.strptime(date_str, '%m/%d/%Y %H:%M')
        except ValueError as e:
            print(f"Date error: {date_str}")
            continue
            
        home_team = Team.query.filter_by(name=home_name).first()
        away_team = Team.query.filter_by(name=away_name).first()
        
        if not home_team or not away_team:
            print(f"Team missing: '{home_name}' or '{away_name}'")
            continue
            
        # Look for the match between these two teams (in any order)
        match = Match.query.filter(
            Match.phase_id == phase.id,
            ((Match.home_team_id == home_team.id) & (Match.away_team_id == away_team.id)) |
            ((Match.home_team_id == away_team.id) & (Match.away_team_id == home_team.id))
        ).first()
        
        if match:
            match.match_date = match_date
            # Also update home/away if it changed
            if match.home_team_id != home_team.id:
                match.home_team_id = home_team.id
                match.away_team_id = away_team.id
            updated += 1
        else:
            print(f"Match not found: {home_name} vs {away_name}")
            not_found += 1

    db.session.commit()
    print(f"Updated {updated} matches.")
    if not_found > 0:
        print(f"Could not find {not_found} matches.")
