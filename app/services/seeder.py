from app import db
from app.models import Team


NATIONAL_TEAMS = [
    # CONCACAF
    ("Estados Unidos", "USA", "national", "🇺🇸", "US"),
    ("México", "MEX", "national", "🇲🇽", "MX"),
    ("Canadá", "CAN", "national", "🇨🇦", "CA"),
    ("Panamá", "PAN", "national", "🇵🇦", "PA"),
    ("Honduras", "HON", "national", "🇭🇳", "HN"),
    ("Costa Rica", "CRC", "national", "🇨🇷", "CR"),
    ("Jamaica", "JAM", "national", "🇯🇲", "JM"),
    ("El Salvador", "SLV", "national", "🇸🇻", "SV"),
    # CONMEBOL
    ("Argentina", "ARG", "national", "🇦🇷", "AR"),
    ("Brasil", "BRA", "national", "🇧🇷", "BR"),
    ("Colombia", "COL", "national", "🇨🇴", "CO"),
    ("Uruguay", "URU", "national", "🇺🇾", "UY"),
    ("Ecuador", "ECU", "national", "🇪🇨", "EC"),
    ("Venezuela", "VEN", "national", "🇻🇪", "VE"),
    ("Chile", "CHI", "national", "🇨🇱", "CL"),
    ("Paraguay", "PAR", "national", "🇵🇾", "PY"),
    ("Bolivia", "BOL", "national", "🇧🇴", "BO"),
    ("Perú", "PER", "national", "🇵🇪", "PE"),
    # UEFA
    ("Alemania", "GER", "national", "🇩🇪", "DE"),
    ("España", "ESP", "national", "🇪🇸", "ES"),
    ("Francia", "FRA", "national", "🇫🇷", "FR"),
    ("Inglaterra", "ENG", "national", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "GB"),
    ("Portugal", "POR", "national", "🇵🇹", "PT"),
    ("Países Bajos", "NED", "national", "🇳🇱", "NL"),
    ("Bélgica", "BEL", "national", "🇧🇪", "BE"),
    ("Croacia", "CRO", "national", "🇭🇷", "HR"),
    ("Italia", "ITA", "national", "🇮🇹", "IT"),
    ("Suiza", "SUI", "national", "🇨🇭", "CH"),
    ("Austria", "AUT", "national", "🇦🇹", "AT"),
    ("Dinamarca", "DEN", "national", "🇩🇰", "DK"),
    ("Serbia", "SRB", "national", "🇷🇸", "RS"),
    ("Polonia", "POL", "national", "🇵🇱", "PL"),
    ("Turquía", "TUR", "national", "🇹🇷", "TR"),
    ("Eslovaquia", "SVK", "national", "🇸🇰", "SK"),
    ("Escocia", "SCO", "national", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "GB"),
    ("Georgia", "GEO", "national", "🇬🇪", "GE"),
    ("Rumanía", "ROU", "national", "🇷🇴", "RO"),
    ("Rep. Checa", "CZE", "national", "🇨🇿", "CZ"),
    ("Ucrania", "UKR", "national", "🇺🇦", "UA"),
    ("Hungría", "HUN", "national", "🇭🇺", "HU"),
    ("Albania", "ALB", "national", "🇦🇱", "AL"),
    ("Eslovenia", "SVN", "national", "🇸🇮", "SI"),
    # CAF
    ("Marruecos", "MAR", "national", "🇲🇦", "MA"),
    ("Senegal", "SEN", "national", "🇸🇳", "SN"),
    ("Nigeria", "NGA", "national", "🇳🇬", "NG"),
    ("Egipto", "EGY", "national", "🇪🇬", "EG"),
    ("Camerún", "CMR", "national", "🇨🇲", "CM"),
    ("Ghana", "GHA", "national", "🇬🇭", "GH"),
    ("Costa de Marfil", "CIV", "national", "🇨🇮", "CI"),
    ("Argelia", "ALG", "national", "🇩🇿", "DZ"),
    ("Túnez", "TUN", "national", "🇹🇳", "TN"),
    ("Sudáfrica", "RSA", "national", "🇿🇦", "ZA"),
    ("Mali", "MLI", "national", "🇲🇱", "ML"),
    ("R.D. Congo", "COD", "national", "🇨🇩", "CD"),
    ("Gabón", "GAB", "national", "🇬🇦", "GA"),
    ("Mozambique", "MOZ", "national", "🇲🇿", "MZ"),
    ("Tanzania", "TAN", "national", "🇹🇿", "TZ"),
    # AFC (Expanded)
    ("Japón", "JPN", "national", "🇯🇵", "JP"),
    ("Corea del Sur", "KOR", "national", "🇰🇷", "KR"),
    ("Australia", "AUS", "national", "🇦🇺", "AU"),
    ("Irán", "IRN", "national", "🇮🇷", "IR"),
    ("Arabia Saudita", "KSA", "national", "🇸🇦", "SA"),
    ("Qatar", "QAT", "national", "🇶🇦", "QA"),
    ("Uzbekistán", "UZB", "national", "🇺🇿", "UZ"),
    ("Jordania", "JOR", "national", "🇯🇴", "JO"),
    ("Irak", "IRQ", "national", "🇮🇶", "IQ"),
    ("Omán", "OMA", "national", "🇴🇲", "OM"),
    ("China", "CHN", "national", "🇨🇳", "CN"),
    ("Siria", "SYR", "national", "🇸🇾", "SY"),
    ("Bahréin", "BHR", "national", "🇧🇭", "BH"),
    # OFC
    ("Nueva Zelanda", "NZL", "national", "🇳🇿", "NZ"),
    ("Islas Salomón", "SOL", "national", "🇸🇧", "SB"),
    # Missing UEFA
    ("Gales", "WAL", "national", "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "GB"),
    ("Grecia", "GRE", "national", "🇬🇷", "GR"),
    ("Islandia", "ISL", "national", "🇮🇸", "IS"),
    ("Suecia", "SWE", "national", "🇸🇪", "SE"),
    ("Noruega", "NOR", "national", "🇳🇴", "NO"),
    ("Finlandia", "FIN", "national", "🇫🇮", "FI"),
    # Missing CONMEBOL
    # None (all 10 are there)
]

CLUB_TEAMS = [
    # España
    ("Real Madrid", "RMA", "club", "⚪", "ES"),
    ("FC Barcelona", "FCB", "club", "🔵🔴", "ES"),
    ("Atlético de Madrid", "ATM", "club", "🔴⚪", "ES"),
    ("Sevilla FC", "SEV", "club", "⚪", "ES"),
    # Inglaterra
    ("Manchester City", "MCI", "club", "🔵", "GB"),
    ("Liverpool", "LIV", "club", "🔴", "GB"),
    ("Chelsea", "CHE", "club", "🔵", "GB"),
    ("Arsenal", "ARS", "club", "🔴", "GB"),
    ("Manchester United", "MNU", "club", "🔴", "GB"),
    ("Tottenham", "TOT", "club", "⚪", "GB"),
    # Alemania
    ("Bayern München", "BAY", "club", "🔴", "DE"),
    ("Borussia Dortmund", "BVB", "club", "🟡", "DE"),
    # Italia
    ("Juventus", "JUV", "club", "⚫⚪", "IT"),
    ("Inter de Milán", "INT", "club", "⚫🔵", "IT"),
    ("AC Milan", "MIL", "club", "🔴⚫", "IT"),
    ("Nápoles", "NAP", "club", "🔵", "IT"),
    # Francia
    ("Paris Saint-Germain", "PSG", "club", "🔵🔴", "FR"),
    # Portugal
    ("Benfica", "SLB", "club", "🔴", "PT"),
    ("Porto", "POR", "club", "🔵", "PT"),
    ("Sporting CP", "SCP", "club", "🟢", "PT"),
    # Colombia
    ("Atlético Nacional", "NAL", "club", "🟢", "CO"),
    ("Millonarios FC", "MIL", "club", "🔵", "CO"),
    ("América de Cali", "AME", "club", "🔴", "CO"),
    ("Junior FC", "JUN", "club", "🔴🟡", "CO"),
    # Argentina
    ("Boca Juniors", "BOC", "club", "🔵🟡", "AR"),
    ("River Plate", "RIV", "club", "⚪🔴", "AR"),
    # Brasil
    ("Flamengo", "FLA", "club", "🔴⚫", "BR"),
    ("Palmeiras", "PAL", "club", "🟢", "BR"),
    ("Santos", "SAN", "club", "⚪", "BR"),
    # México
    ("Club América", "AME", "club", "🟡🔵", "MX"),
    ("Chivas Guadalajara", "GDL", "club", "🔴⚪", "MX"),
]


def seed_teams():
    """Load initial team catalog. Skips existing teams by name."""
    added = 0

    for name, short, ttype, emoji, code in NATIONAL_TEAMS:
        if not Team.query.filter_by(name=name).first():
            db.session.add(Team(
                name=name, short_name=short, team_type=ttype,
                flag_emoji=emoji, country_code=code
            ))
            added += 1

    for name, short, ttype, emoji, code in CLUB_TEAMS:
        if not Team.query.filter_by(name=name).first():
            db.session.add(Team(
                name=name, short_name=short, team_type=ttype,
                flag_emoji=emoji, country_code=code
            ))
            added += 1

    db.session.commit()
    return added
