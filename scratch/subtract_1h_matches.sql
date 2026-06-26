-- ============================================================
-- Restar 1 hora a todos los partidos programados
-- Solo afecta la hora — días, meses y años no cambian
-- Ejecutar en Supabase > SQL Editor
-- ============================================================

-- Vista previa (opcional): ver antes y después sin ejecutar
-- SELECT id, match_date, match_date - INTERVAL '1 hour' AS match_date_nueva
-- FROM matches
-- WHERE match_date IS NOT NULL
-- ORDER BY match_date;

-- Actualización real:
UPDATE matches
SET match_date = match_date - INTERVAL '1 hour'
WHERE match_date IS NOT NULL;

-- Verificación post-ejecución:
SELECT COUNT(*) AS partidos_actualizados
FROM matches
WHERE match_date IS NOT NULL;
