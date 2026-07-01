-- =============================================================================
-- MundialApp — Migración acumulada para Supabase
-- Generado: 2026-06-25
-- Seguro de ejecutar múltiples veces (IF NOT EXISTS / DO $$ … $$)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. NUEVAS TABLAS
--    Crear antes de añadir FKs a columnas que las referencian.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS event_templates (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    logo_emoji  VARCHAR(10)  DEFAULT '📋',
    is_active   BOOLEAN      DEFAULT TRUE,
    uses_bracket        BOOLEAN DEFAULT FALSE,
    allows_group_stage  BOOLEAN DEFAULT TRUE,
    allows_knockout     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS template_phases (
    id           SERIAL PRIMARY KEY,
    template_id  INTEGER NOT NULL REFERENCES event_templates(id) ON DELETE CASCADE,
    name         VARCHAR(100) NOT NULL,
    phase_order  INTEGER NOT NULL DEFAULT 1,
    phase_type   VARCHAR(20)  DEFAULT 'group',
    teams_qualify    INTEGER,
    is_bracket_round BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS template_scoring_configs (
    id           SERIAL PRIMARY KEY,
    template_id  INTEGER NOT NULL REFERENCES event_templates(id) ON DELETE CASCADE,
    score_type   VARCHAR(30) NOT NULL,
    points_value INTEGER     DEFAULT 0,
    is_active    BOOLEAN     DEFAULT TRUE,
    description  VARCHAR(200),
    CONSTRAINT uq_template_scoring_type UNIQUE (template_id, score_type)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. TABLA events — columnas nuevas
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS can_view_others_predictions BOOLEAN     DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS qualifies_third_place       BOOLEAN     DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS third_place_slots           INTEGER     DEFAULT 0,
    ADD COLUMN IF NOT EXISTS participation_fee           NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS prize_first                 NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS prize_second                NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS prize_third                 NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS nequi_number                VARCHAR(20) DEFAULT '',
    ADD COLUMN IF NOT EXISTS template_id                 INTEGER     REFERENCES event_templates(id) ON DELETE SET NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. TABLA matches — columnas nuevas
-- ─────────────────────────────────────────────────────────────────────────────

-- Columnas básicas que pueden faltar
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS match_label       VARCHAR(100),
    ADD COLUMN IF NOT EXISTS is_locked         BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS penalty_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL;

-- Infraestructura del Fixture (avance automático entre fases eliminatorias)
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS home_source_match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS away_source_match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS home_source_outcome  VARCHAR(10) DEFAULT 'winner',
    ADD COLUMN IF NOT EXISTS away_source_outcome  VARCHAR(10) DEFAULT 'winner',
    ADD COLUMN IF NOT EXISTS bracket_position     INTEGER;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. TABLA predictions — columnas nuevas
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS predicted_penalty_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. TABLA participants — columnas nuevas
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE participants
    ADD COLUMN IF NOT EXISTS payment_confirmed BOOLEAN DEFAULT FALSE;


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. DATOS — scoring_configs: insertar correct_penalty_winner para eventos
--    que fueron creados antes de que existiera esta configuración.
--    Se inserta solo donde no exista; no toca eventos que ya lo tengan.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO scoring_configs (event_id, score_type, points_value, is_active, description)
SELECT
    e.id,
    'correct_penalty_winner',
    1,
    TRUE,
    'Bonus: adivinaste qué equipo clasifica en penales (solo empates de eliminatoria)'
FROM events e
WHERE NOT EXISTS (
    SELECT 1
    FROM scoring_configs sc
    WHERE sc.event_id = e.id
      AND sc.score_type = 'correct_penalty_winner'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. ÍNDICES recomendados (mejoran el rendimiento del Fixture y rankings)
--    CONCURRENTLY no bloquea la tabla; seguro en producción.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_matches_home_source ON matches(home_source_match_id)
    WHERE home_source_match_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_matches_away_source ON matches(away_source_match_id)
    WHERE away_source_match_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_penalty_winner ON predictions(predicted_penalty_winner_id)
    WHERE predicted_penalty_winner_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_matches_phase_bracket ON matches(phase_id, bracket_position);


-- ─────────────────────────────────────────────────────────────────────────────
-- FIN — Verificación rápida
-- ─────────────────────────────────────────────────────────────────────────────

-- Ejecuta este SELECT para confirmar que las columnas existen:
SELECT
    table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      (table_name = 'matches'      AND column_name IN ('match_label','is_locked','penalty_winner_id',
                                                        'home_source_match_id','away_source_match_id',
                                                        'home_source_outcome','away_source_outcome',
                                                        'bracket_position'))
   OR (table_name = 'predictions'  AND column_name = 'predicted_penalty_winner_id')
   OR (table_name = 'events'       AND column_name IN ('can_view_others_predictions','qualifies_third_place',
                                                        'third_place_slots','participation_fee',
                                                        'prize_first','prize_second','prize_third',
                                                        'prize_type',
                                                        'nequi_number','template_id'))
   OR (table_name = 'participants' AND column_name = 'payment_confirmed')
   OR  table_name IN ('event_templates','template_phases','template_scoring_configs')
  )
ORDER BY table_name, column_name;


-- =============================================================================
-- SECCIÓN 8 — Tipo de premios flexible (Dinero / Porcentaje)
-- Generado: 2026-07-01
-- Seguro de ejecutar múltiples veces (ADD COLUMN IF NOT EXISTS)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 8.1  Nueva columna prize_type en events
--      DEFAULT 'money' garantiza que todos los eventos existentes continúen
--      funcionando exactamente igual (sin intervención adicional).
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS prize_type VARCHAR(10) DEFAULT 'money';

-- ─────────────────────────────────────────────────────────────────────────────
-- 8.2  Verificación — confirma que la columna existe y tiene el default correcto
-- ─────────────────────────────────────────────────────────────────────────────

SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name   = 'events'
  AND column_name  = 'prize_type';

-- Resultado esperado:
--   column_name | data_type         | column_default | is_nullable
--   prize_type  | character varying | 'money'::...   | YES
