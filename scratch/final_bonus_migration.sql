-- =============================================================================
-- Migración Segura: Agregar regla 'final_winner_bonus'
-- =============================================================================
-- Este script inserta la nueva configuración de bonus en las tablas correspondientes
-- sin afectar la estructura ni los datos actuales de los eventos.

-- 1. Insertar en template_scoring_configs para todas las plantillas existentes
-- Valor por defecto en plantillas: 3 puntos, activo (is_active = TRUE)
INSERT INTO template_scoring_configs (template_id, score_type, points_value, is_active, description)
SELECT id, 'final_winner_bonus', 3, TRUE, 'Bonus: Acertar el ganador del partido de la Final'
FROM event_templates
WHERE id NOT IN (
    SELECT template_id 
    FROM template_scoring_configs 
    WHERE score_type = 'final_winner_bonus'
);

-- 2. Insertar en scoring_configs para todos los eventos existentes
-- IMPORTANTE: Para cumplir la retrocompatibilidad estricta, los eventos que ya 
-- estaban creados reciben esta configuración inactiva (is_active = FALSE).
INSERT INTO scoring_configs (event_id, score_type, points_value, is_active, description)
SELECT id, 'final_winner_bonus', 3, FALSE, 'Bonus: Acertar el ganador del partido de la Final'
FROM events
WHERE id NOT IN (
    SELECT event_id 
    FROM scoring_configs 
    WHERE score_type = 'final_winner_bonus'
);
