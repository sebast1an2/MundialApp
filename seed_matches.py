import os
from app import create_app, db
from app.models import Event, Phase, Group, Match, Team, GroupTeam
from datetime import datetime

app = create_app()

matches_data = """
06/11/2026, México, Sudáfrica, Grupo A
06/11/2026, Corea del Sur, República Checa, Grupo A
06/18/2026, República Checa, Sudáfrica, Grupo A
06/18/2026, México, Corea del Sur, Grupo A
06/25/2026, Sudáfrica, Corea del Sur, Grupo A
06/25/2026, República Checa, México, Grupo A
06/12/2026, Canadá, Bosnia y Herzegovina, Grupo B
06/12/2026, Qatar, Suiza, Grupo B
06/19/2026, Suiza, Bosnia y Herzegovina, Grupo B
06/19/2026, Canadá, Qatar, Grupo B
06/26/2026, Bosnia y Herzegovina, Qatar, Grupo B
06/26/2026, Suiza, Canadá, Grupo B
06/13/2026, Brasil, Marruecos, Grupo C
06/13/2026, Haití, Escocia, Grupo C
06/20/2026, Escocia, Marruecos, Grupo C
06/20/2026, Brasil, Haití, Grupo C
06/27/2026, Marruecos, Haití, Grupo C
06/27/2026, Escocia, Brasil, Grupo C
06/13/2026, Estados Unidos, Paraguay, Grupo D
06/13/2026, Australia, Turquía, Grupo D
06/20/2026, Estados Unidos, Australia, Grupo D
06/20/2026, Turquía, Paraguay, Grupo D
06/27/2026, Paraguay, Australia, Grupo D
06/27/2026, Turquía, Estados Unidos, Grupo D
06/14/2026, Alemania, Curazao, Grupo E
06/14/2026, Costa de Marfil, Ecuador, Grupo E
06/21/2026, Alemania, Costa de Marfil, Grupo E
06/21/2026, Ecuador, Curazao, Grupo E
06/28/2026, Curazao, Costa de Marfil, Grupo E
06/28/2026, Ecuador, Alemania, Grupo E
06/14/2026, Países Bajos, Japón, Grupo F
06/14/2026, Suecia, Túnez, Grupo F
06/21/2026, Países Bajos, Suecia, Grupo F
06/21/2026, Túnez, Japón, Grupo F
06/28/2026, Japón, Suecia, Grupo F
06/28/2026, Túnez, Países Bajos, Grupo F
06/15/2026, Bélgica, Egipto, Grupo G
06/15/2026, Irán, Nueva Zelanda, Grupo G
06/22/2026, Bélgica, Irán, Grupo G
06/22/2026, Nueva Zelanda, Egipto, Grupo G
06/29/2026, Egipto, Irán, Grupo G
06/29/2026, Nueva Zelanda, Bélgica, Grupo G
06/15/2026, España, Cabo Verde, Grupo H
06/15/2026, Arabia Saudita, Uruguay, Grupo H
06/22/2026, España, Arabia Saudita, Grupo H
06/22/2026, Uruguay, Cabo Verde, Grupo H
06/29/2026, Cabo Verde, Arabia Saudita, Grupo H
06/29/2026, Uruguay, España, Grupo H
06/16/2026, Francia, Senegal, Grupo I
06/16/2026, Irak, Noruega, Grupo I
06/23/2026, Francia, Irak, Grupo I
06/23/2026, Noruega, Senegal, Grupo I
06/30/2026, Senegal, Irak, Grupo I
06/30/2026, Noruega, Francia, Grupo I
06/16/2026, Argentina, Argelia, Grupo J
06/16/2026, Austria, Jordania, Grupo J
06/23/2026, Argentina, Austria, Grupo J
06/23/2026, Jordania, Argelia, Grupo J
06/30/2026, Argelia, Austria, Grupo J
06/30/2026, Jordania, Argentina, Grupo J
06/17/2026, Portugal, RD Congo, Grupo K
06/17/2026, Uzbekistán, Colombia, Grupo K
06/24/2026, Portugal, Uzbekistán, Grupo K
06/24/2026, Colombia, RD Congo, Grupo K
07/01/2026, Colombia, Portugal, Grupo K
07/01/2026, RD Congo, Uzbekistán, Grupo K
06/17/2026, Inglaterra, Croacia, Grupo L
06/17/2026, Ghana, Panamá, Grupo L
06/24/2026, Inglaterra, Ghana, Grupo L
06/24/2026, Panamá, Croacia, Grupo L
07/01/2026, Panamá, Inglaterra, Grupo L
07/01/2026, Croacia, Ghana, Grupo L
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
    added = 0
    missing_teams = set()
    
    for line in lines:
        parts = line.split(',')
        if len(parts) != 4: continue
        
        date_str = parts[0].strip()
        home_name = normalize_name(parts[1])
        away_name = normalize_name(parts[2])
        group_name = parts[3].strip().replace('Grupo ', '')
        
        try:
            match_date = datetime.strptime(date_str, '%m/%d/%Y')
        except:
            match_date = None
            
        group = Group.query.filter_by(event_id=event.id, name=group_name).first()
        if not group:
            print(f"Group not found: {group_name}")
            continue
            
        home_team = Team.query.filter_by(name=home_name).first()
        away_team = Team.query.filter_by(name=away_name).first()
        
        if not home_team: missing_teams.add(home_name)
        if not away_team: missing_teams.add(away_name)
        
        if not home_team or not away_team:
            continue
            
        # Check duplicate
        exists = Match.query.filter_by(
            phase_id=phase.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id
        ).first()
        
        if not exists:
            m = Match(
                phase_id=phase.id,
                group_id=group.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                match_label=f"Grupo {group_name}",
                match_date=match_date
            )
            db.session.add(m)
            added += 1

    db.session.commit()
    print(f"Added {added} matches.")
    if missing_teams:
        print(f"Missing teams: {missing_teams}")
