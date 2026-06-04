import os
from app import create_app, db
from app.models import Event, Phase, Group, Match, Team
from datetime import datetime

app = create_app()

matches_data = """
06/11/2026 13:00, México, Sudáfrica, Grupo A
06/11/2026 16:00, Corea del Sur, República Checa, Grupo A
06/18/2026 13:00, México, Corea del Sur, Grupo A
06/18/2026 16:00, Sudáfrica, República Checa, Grupo A
06/25/2026 19:00, México, República Checa, Grupo A
06/25/2026 22:00, Sudáfrica, Corea del Sur, Grupo A

06/12/2026 13:00, Canadá, Bosnia y Herzegovina, Grupo B
06/12/2026 16:00, Qatar, Suiza, Grupo B
06/19/2026 13:00, Canadá, Qatar, Grupo B
06/19/2026 16:00, Bosnia y Herzegovina, Suiza, Grupo B
06/26/2026 19:00, Canadá, Suiza, Grupo B
06/26/2026 22:00, Bosnia y Herzegovina, Qatar, Grupo B

06/13/2026 13:00, Brasil, Marruecos, Grupo C
06/13/2026 16:00, Haití, Escocia, Grupo C
06/20/2026 13:00, Brasil, Haití, Grupo C
06/20/2026 16:00, Marruecos, Escocia, Grupo C
06/27/2026 19:00, Brasil, Escocia, Grupo C
06/27/2026 22:00, Marruecos, Haití, Grupo C

06/13/2026 13:00, Estados Unidos, Paraguay, Grupo D
06/13/2026 16:00, Australia, Turquía, Grupo D
06/20/2026 13:00, Estados Unidos, Australia, Grupo D
06/20/2026 16:00, Paraguay, Turquía, Grupo D
06/27/2026 19:00, Estados Unidos, Turquía, Grupo D
06/27/2026 22:00, Paraguay, Australia, Grupo D

06/14/2026 13:00, Alemania, Curazao, Grupo E
06/14/2026 16:00, Costa de Marfil, Ecuador, Grupo E
06/21/2026 13:00, Alemania, Costa de Marfil, Grupo E
06/21/2026 16:00, Curazao, Ecuador, Grupo E
06/28/2026 19:00, Alemania, Ecuador, Grupo E
06/28/2026 22:00, Curazao, Costa de Marfil, Grupo E

06/14/2026 13:00, Países Bajos, Japón, Grupo F
06/14/2026 16:00, Suecia, Túnez, Grupo F
06/21/2026 13:00, Países Bajos, Suecia, Grupo F
06/21/2026 16:00, Japón, Túnez, Grupo F
06/28/2026 19:00, Países Bajos, Túnez, Grupo F
06/28/2026 22:00, Japón, Suecia, Grupo F

06/15/2026 13:00, Bélgica, Egipto, Grupo G
06/15/2026 16:00, Irán, Nueva Zelanda, Grupo G
06/22/2026 13:00, Bélgica, Irán, Grupo G
06/22/2026 16:00, Egipto, Nueva Zelanda, Grupo G
06/29/2026 19:00, Bélgica, Nueva Zelanda, Grupo G
06/29/2026 22:00, Egipto, Irán, Grupo G

06/15/2026 13:00, España, Cabo Verde, Grupo H
06/15/2026 16:00, Arabia Saudita, Uruguay, Grupo H
06/22/2026 13:00, España, Arabia Saudita, Grupo H
06/22/2026 16:00, Cabo Verde, Uruguay, Grupo H
06/29/2026 19:00, España, Uruguay, Grupo H
06/29/2026 22:00, Cabo Verde, Arabia Saudita, Grupo H

06/16/2026 13:00, Francia, Senegal, Grupo I
06/16/2026 16:00, Irak, Noruega, Grupo I
06/23/2026 13:00, Francia, Irak, Grupo I
06/23/2026 16:00, Senegal, Noruega, Grupo I
06/30/2026 19:00, Francia, Noruega, Grupo I
06/30/2026 22:00, Senegal, Irak, Grupo I

06/16/2026 13:00, Argentina, Argelia, Grupo J
06/16/2026 16:00, Austria, Jordania, Grupo J
06/23/2026 13:00, Argentina, Austria, Grupo J
06/23/2026 16:00, Argelia, Jordania, Grupo J
06/30/2026 19:00, Argentina, Jordania, Grupo J
06/30/2026 22:00, Argelia, Austria, Grupo J

06/17/2026 13:00, Portugal, RD Congo, Grupo K
06/17/2026 16:00, Uzbekistán, Colombia, Grupo K
06/24/2026 13:00, Portugal, Uzbekistán, Grupo K
06/24/2026 16:00, Colombia, RD Congo, Grupo K
07/01/2026 19:00, Portugal, Colombia, Grupo K
07/01/2026 22:00, RD Congo, Uzbekistán, Grupo K

06/17/2026 13:00, Inglaterra, Croacia, Grupo L
06/17/2026 16:00, Ghana, Panamá, Grupo L
06/24/2026 13:00, Inglaterra, Ghana, Grupo L
06/24/2026 16:00, Croacia, Panamá, Grupo L
07/01/2026 19:00, Inglaterra, Panamá, Grupo L
07/01/2026 22:00, Croacia, Ghana, Grupo L
"""

def normalize_name(name):
    name = name.strip()
    if name == "RD Congo": return "R.D. Congo"
    if name == "República Checa": return "Rep. Checa"
    return name

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
        if len(parts) != 4: continue
        
        date_str = parts[0].strip() # "06/11/2026 13:00"
        home_name = normalize_name(parts[1])
        away_name = normalize_name(parts[2])
        
        try:
            match_date = datetime.strptime(date_str, '%m/%d/%Y %H:%M')
        except ValueError as e:
            print(f"Date error: {date_str}")
            continue
            
        home_team = Team.query.filter_by(name=home_name).first()
        away_team = Team.query.filter_by(name=away_name).first()
        
        if not home_team or not away_team:
            print(f"Team missing: {home_name} or {away_name}")
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
