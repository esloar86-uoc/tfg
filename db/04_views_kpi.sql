--==========================================================
-- 04_views_kpi.sql
-- Vistas KPI para analítica/BI sobre el modelo gold (f_tickets + dimensiones)
-- Requisitos: 01_schema_ddl.sql y 02_staging_load.sql aplicados.
--==========================================================

USE tfg;

-- 1) Overview global
CREATE OR REPLACE VIEW vw_kpi_overview AS
SELECT
  COUNT(*)                                                        AS total_tickets,
  SUM(CASE WHEN fecha_resolucion IS NOT NULL THEN 1 ELSE 0 END)  AS cerrados,
  SUM(CASE WHEN fecha_resolucion IS NULL  THEN 1 ELSE 0 END)      AS abiertos,
  ROUND(
    100 * SUM(CASE WHEN sla_met = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN sla_met IN (0,1) THEN 1 ELSE 0 END),0)
  ,1)                                                             AS sla_ok_pct,
  AVG(first_response_time_min)                                    AS avg_frt_min,
  AVG(time_to_resolution_min)                                     AS avg_ttr_min
FROM f_tickets;

-- 2) Métricas por canal
CREATE OR REPLACE VIEW vw_kpi_by_channel AS
SELECT
  c.canal,
  COUNT(*)                                                        AS n,
  SUM(CASE WHEN f.fecha_resolucion IS NULL THEN 1 ELSE 0 END)     AS abiertos,
  ROUND(
    100 * SUM(CASE WHEN f.sla_met = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN f.sla_met IN (0,1) THEN 1 ELSE 0 END),0)
  ,1)                                                             AS sla_ok_pct,
  AVG(f.first_response_time_min)                                  AS avg_frt_min,
  AVG(f.time_to_resolution_min)                                   AS avg_ttr_min
FROM f_tickets f
JOIN d_canal c ON c.id_canal = f.id_canal
GROUP BY c.canal;

-- 3) Métricas por prioridad
CREATE OR REPLACE VIEW vw_kpi_by_priority AS
SELECT
  p.prioridad,
  COUNT(*) AS n,
  SUM(f.fecha_resolucion IS NULL) AS abiertos,
  ROUND(100 * AVG(CASE WHEN f.sla_met IS NULL THEN NULL ELSE f.sla_met END), 2) AS sla_ok_pct,
  ROUND(AVG(f.first_response_time_min), 1) AS avg_frt_min,
  ROUND(AVG(f.time_to_resolution_min), 1)  AS avg_ttr_min
FROM f_tickets f
JOIN d_prioridad p ON p.id_prioridad = f.id_prioridad
GROUP BY p.prioridad
ORDER BY n DESC;

-- 4) Flujo diario (entradas/salidas)
CREATE OR REPLACE VIEW vw_kpi_daily_flow AS
SELECT
  d.fecha,
  SUM(d.inflow)  AS tickets_creados,
  SUM(d.outflow) AS tickets_cerrados
FROM (
  SELECT DATE(fecha_creacion) AS fecha, COUNT(*) AS inflow, 0 AS outflow
  FROM f_tickets
  GROUP BY DATE(fecha_creacion)
  UNION ALL
  SELECT DATE(fecha_resolucion) AS fecha, 0 AS inflow, COUNT(*) AS outflow
  FROM f_tickets
  WHERE fecha_resolucion IS NOT NULL
  GROUP BY DATE(fecha_resolucion)
) d
GROUP BY d.fecha
ORDER BY d.fecha;

-- 5) Backlog actual (cantidad y antigüedad media en horas)
CREATE OR REPLACE VIEW vw_kpi_current_backlog AS
SELECT
  COUNT(*) AS backlog_abierto,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, fecha_creacion, NOW())), 1) AS edad_media_horas
FROM f_tickets
WHERE fecha_resolucion IS NULL;

-- 6) Cierre mensual (throughput) y tiempos medios
CREATE OR REPLACE VIEW vw_kpi_monthly AS
SELECT
  DATE_FORMAT(fecha_creacion, '%Y-%m') AS ym,
  COUNT(*)                              AS creados,
  ROUND(AVG(first_response_time_min),1) AS avg_frt_min,
  ROUND(AVG(time_to_resolution_min),1)  AS avg_ttr_min
FROM f_tickets
GROUP BY DATE_FORMAT(fecha_creacion, '%Y-%m')
ORDER BY ym;

-- 7) Distribución por tipo real
CREATE OR REPLACE VIEW vw_kpi_by_type AS
SELECT
  t.codigo AS tipo,
  COUNT(*) AS n,
  ROUND(100 * COUNT(*) / (SELECT COUNT(*) FROM f_tickets), 2) AS pct
FROM f_tickets f
LEFT JOIN d_tipo t ON t.id_tipo = f.id_tipo_real
GROUP BY t.codigo
ORDER BY n DESC;

-- 8) Calidad: incoherencias temporales (debería dar 0 filas)
CREATE OR REPLACE VIEW vw_kpi_quality_incoherences AS
SELECT *
FROM f_tickets
WHERE fecha_resolucion IS NOT NULL
  AND fecha_resolucion < fecha_creacion;

-- 9) Accuracy por canal (requiere 03_ml_schema.sql con tickets_clasificados)
CREATE OR REPLACE VIEW vw_kpi_accuracy_by_channel AS
SELECT
  c.canal,
  ROUND(100 * AVG(CASE WHEN f.id_tipo_real IS NULL THEN NULL
                       WHEN tc.id_tipo_predicho = f.id_tipo_real THEN 1 ELSE 0 END), 2) AS accuracy_pct,
  COUNT(*) AS n_eval
FROM tickets_clasificados tc
JOIN f_tickets f ON f.id_ticket = tc.id_ticket
JOIN d_canal c   ON c.id_canal  = f.id_canal
GROUP BY c.canal
ORDER BY n_eval DESC;
