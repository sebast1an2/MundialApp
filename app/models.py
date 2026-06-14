from datetime import datetime
from app import db


# ─────────────────────────────────────────────
# CATÁLOGO DE EQUIPOS (global, reutilizable)
# ─────────────────────────────────────────────
class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    short_name = db.Column(db.String(10))          # COL, ARG, RMA ...
    team_type = db.Column(db.String(20), nullable=False)  # 'national' | 'club'
    flag_emoji = db.Column(db.String(10), default='🏴')
    country_code = db.Column(db.String(3))          # ISO-3166 alpha-2
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    group_teams = db.relationship('GroupTeam', backref='team', lazy='dynamic')
    home_matches = db.relationship('Match', foreign_keys='Match.home_team_id',
                                   backref='home_team', lazy='dynamic')
    away_matches = db.relationship('Match', foreign_keys='Match.away_team_id',
                                   backref='away_team', lazy='dynamic')

    def __repr__(self):
        return f'<Team {self.name}>'


# ─────────────────────────────────────────────
# EVENTO DE TORNEO
# ─────────────────────────────────────────────
class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    tournament_type = db.Column(db.String(50), default='world_cup')  # world_cup | champions | custom
    description = db.Column(db.Text)
    logo_emoji = db.Column(db.String(10), default='🏆')
    status = db.Column(db.String(20), default='draft')   # draft | active | finished
    can_view_others_predictions = db.Column(db.Boolean, default=True)
    # Clasificación de mejores terceros lugares
    qualifies_third_place = db.Column(db.Boolean, default=False)   # ¿Clasifican terceros?
    third_place_slots     = db.Column(db.Integer, default=0)        # Cuántos terceros clasifican
    participation_fee = db.Column(db.Numeric(12, 2), nullable=True, default=0)  # valor de participación en moneda local
    # Prize configuration
    prize_first  = db.Column(db.Numeric(12, 2), nullable=True, default=0)   # Premio 1er lugar
    prize_second = db.Column(db.Numeric(12, 2), nullable=True, default=0)   # Premio 2do lugar
    prize_third  = db.Column(db.Numeric(12, 2), nullable=True, default=0)   # Premio 3er lugar
    nequi_number = db.Column(db.String(20), nullable=True, default='')      # Número Nequi para pagos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    groups = db.relationship('Group', backref='event', lazy='dynamic',
                              cascade='all, delete-orphan')
    phases = db.relationship('Phase', backref='event', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='Phase.phase_order')
    participants = db.relationship('Participant', backref='event', lazy='dynamic',
                                   cascade='all, delete-orphan')
    scoring_configs = db.relationship('ScoringConfig', backref='event', lazy='dynamic',
                                      cascade='all, delete-orphan')

    def get_active_phase(self):
        return Phase.query.filter_by(event_id=self.id, is_prediction_open=True)\
                          .order_by(Phase.phase_order).first()

    def __repr__(self):
        return f'<Event {self.name}>'


# ─────────────────────────────────────────────
# GRUPOS DENTRO DE UN EVENTO
# ─────────────────────────────────────────────
class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    name = db.Column(db.String(10), nullable=False)   # A, B, C ... L

    # Relations
    group_teams = db.relationship('GroupTeam', backref='group', lazy='dynamic',
                                  cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='group', lazy='dynamic')

    def __repr__(self):
        return f'<Group {self.name}>'


class GroupTeam(db.Model):
    __tablename__ = 'group_teams'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    seed_order = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('group_id', 'team_id'),)


# ─────────────────────────────────────────────
# FASES DEL TORNEO
# ─────────────────────────────────────────────
class Phase(db.Model):
    __tablename__ = 'phases'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)   # Fase de Grupos, Octavos...
    phase_order = db.Column(db.Integer, nullable=False, default=1)

    # Control MANUAL de apertura/cierre (independiente de fechas)
    is_prediction_open = db.Column(db.Boolean, default=False)
    is_results_active = db.Column(db.Boolean, default=False)

    # Fechas informativas (opcionales)
    prediction_open_at = db.Column(db.DateTime, nullable=True)
    prediction_close_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    matches = db.relationship('Match', backref='phase', lazy='dynamic',
                              cascade='all, delete-orphan')
    predictions = db.relationship('Prediction', backref='phase', lazy='dynamic')

    def __repr__(self):
        return f'<Phase {self.name}>'


# ─────────────────────────────────────────────
# PARTIDOS
# ─────────────────────────────────────────────
class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    match_date = db.Column(db.DateTime, nullable=True)
    match_label = db.Column(db.String(100))   # "Grupo A - J1" / "Semifinal 1"

    # Resultado real
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    penalty_winner_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    is_finished = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    predictions = db.relationship('Prediction', backref='match', lazy='dynamic',
                                  cascade='all, delete-orphan')
    scores = db.relationship('Score', backref='match', lazy='dynamic',
                             cascade='all, delete-orphan')

    def get_result(self):
        """Returns 'home', 'away', or 'draw' based on real scores and penalties."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return 'home'
        if self.away_score > self.home_score:
            return 'away'
        
        # Draw: check penalties
        if self.penalty_winner_id == self.home_team_id:
            return 'home'
        if self.penalty_winner_id == self.away_team_id:
            return 'away'
            
        return 'draw'

    def __repr__(self):
        return f'<Match {self.home_team_id} vs {self.away_team_id}>'


# ─────────────────────────────────────────────
# PARTICIPANTES
# ─────────────────────────────────────────────
class Participant(db.Model):
    __tablename__ = 'participants'

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    total_points = db.Column(db.Integer, default=0)
    payment_confirmed = db.Column(db.Boolean, default=False)  # pago de participación confirmado por admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('cedula', 'event_id',
                                          name='uq_cedula_event'),)

    # Relations
    predictions = db.relationship('Prediction', backref='participant', lazy='dynamic',
                                  cascade='all, delete-orphan')
    scores = db.relationship('Score', backref='participant', lazy='dynamic',
                             cascade='all, delete-orphan')

    def has_predicted_phase(self, phase_id):
        return Prediction.query.filter_by(
            participant_id=self.id, phase_id=phase_id
        ).count() > 0

    def __repr__(self):
        return f'<Participant {self.name} ({self.cedula})>'


# ─────────────────────────────────────────────
# PREDICCIONES
# ─────────────────────────────────────────────
class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    home_pred = db.Column(db.Integer, nullable=False)
    away_pred = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('participant_id', 'match_id',
                                          name='uq_participant_match'),)

    def get_pred_result(self):
        if self.home_pred > self.away_pred:
            return 'home'
        elif self.away_pred > self.home_pred:
            return 'away'
        return 'draw'

    def __repr__(self):
        return f'<Prediction {self.participant_id} match={self.match_id} {self.home_pred}-{self.away_pred}>'


# ─────────────────────────────────────────────
# PUNTOS POR PARTIDO
# ─────────────────────────────────────────────
class Score(db.Model):
    __tablename__ = 'scores'

    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    points_earned = db.Column(db.Integer, default=0)
    score_type = db.Column(db.String(30), default='none')
    # 'exact_score' | 'correct_winner' | 'none'
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('participant_id', 'match_id',
                                          name='uq_score_participant_match'),)


# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PUNTUACIÓN (por evento)
# ─────────────────────────────────────────────
class ScoringConfig(db.Model):
    __tablename__ = 'scoring_configs'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    score_type = db.Column(db.String(30), nullable=False)
    # 'exact_score' | 'correct_winner' | 'group_position'
    points_value = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(200))

    __table_args__ = (db.UniqueConstraint('event_id', 'score_type',
                                          name='uq_scoring_event_type'),)

    @staticmethod
    def create_defaults(event_id):
        """Create default scoring config for a new event."""
        defaults = [
            {
                'score_type': 'exact_score',
                'points_value': 3,
                'is_active': True,
                'description': 'Marcador exacto (ej: predijiste 2-1 y fue 2-1)',
            },
            {
                'score_type': 'correct_winner',
                'points_value': 1,
                'is_active': True,
                'description': 'Ganador/empate correcto pero marcador incorrecto',
            },
            {
                'score_type': 'group_position',
                'points_value': 2,
                'is_active': False,
                'description': 'Posición exacta del equipo en la tabla del grupo',
            },
        ]
        for d in defaults:
            sc = ScoringConfig(event_id=event_id, **d)
            db.session.add(sc)
        db.session.commit()
