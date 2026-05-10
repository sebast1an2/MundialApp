import os
from app import create_app, db
from app.models import Phase, Score, Prediction, Match

app = create_app()

with app.app_context():
    # Pick the last phase to try deleting
    phase = Phase.query.order_by(Phase.id.desc()).first()
    if phase:
        print(f"Intentando borrar fase {phase.name} (ID: {phase.id})")
        try:
            match_ids = [m.id for m in phase.matches.all()]
            if match_ids:
                Score.query.filter(Score.match_id.in_(match_ids)).delete(synchronize_session=False)
                Prediction.query.filter(Prediction.match_id.in_(match_ids)).delete(synchronize_session=False)
                Match.query.filter(Match.id.in_(match_ids)).delete(synchronize_session=False)
            
            Prediction.query.filter_by(phase_id=phase.id).delete(synchronize_session=False)

            db.session.delete(phase)
            db.session.commit()
            print("Borrado exitoso.")
        except Exception as e:
            db.session.rollback()
            print(f"Error al borrar: {e}")
    else:
        print("No hay fases.")
