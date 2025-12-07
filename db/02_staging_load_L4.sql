--==============================================================
-- 02_staging_load_L4.sql  (L4_manual_cat.csv -> staging -> f_tickets)
-- Limpieza staging, promoción idempotente, KPIs y linaje
--==============================================================

USE tfg;

-------------------------------------------------------
-- 1. Limpieza + normalización a stg (reejecutable)
-------------------------------------------------------
UPDATE stg_tickets
SET canal     = TRIM(canal),
    estado    = TRIM(estado),
    prioridad = TRIM(prioridad),
    categoria = TRIM(categoria),
    sla_met   = TRIM(sla_met);

-- Booleanos SLA a 0/1
UPDATE stg_tickets
SET sla_met = CASE LOWER(sla_met)
                WHEN 'true' THEN '1'
                WHEN 'false' THEN '0'
                WHEN 'verdadero' THEN '1'
                WHEN 'falso' THEN '0'
                ELSE NULL
              END;

-- Linaje en staging (por si hubiera llegado vacío) - L4_demo
UPDATE stg_tickets
SET origen='L4_demo', id_origen=id_ticket
WHERE (origen IS NULL OR origen='') OR (id_origen IS NULL OR id_origen='');

-- Unificación de canal a la dimensión
UPDATE stg_tickets
SET canal = CASE
  WHEN UPPER(canal) = 'PORTAL_SOPORTE'    THEN 'Portal Soporte General'
  WHEN UPPER(canal) = 'PORTAL_INTERNO'    THEN 'Portal Interno'
  WHEN UPPER(canal) = 'PORTAL_DOCUMENTAL' THEN 'Portal Documental'
  WHEN UPPER(canal) = 'EMAIL'             THEN 'Email'
  ELSE canal
END;

-- Unificación de prioridad: todo a Baja/Media/Alta/Urgente
UPDATE stg_tickets
SET prioridad='Urgente'
WHERE LOWER(prioridad) IN ('crítica','critica','p1','critical');

-- Unificación de estado: 'ABIERTO' - 'Pendiente'
UPDATE stg_tickets
SET estado='Pendiente'
WHERE UPPER(estado)='ABIERTO';

-- Verificaciones:
-- SELECT s.canal, COUNT(*) FROM stg_tickets s LEFT JOIN d_canal d ON d.canal=s.canal WHERE d.id_canal IS NULL GROUP BY s.canal;
-- SELECT s.prioridad, COUNT(*) FROM stg_tickets s LEFT JOIN d_prioridad d ON d.prioridad=s.prioridad WHERE d.id_prioridad IS NULL GROUP BY s.prioridad;
-- SELECT s.estado, COUNT(*) FROM stg_tickets s LEFT JOIN d_estado d ON d.estado=s.estado WHERE d.id_estado IS NULL GROUP BY s.estado;

-----------------------------------------
-- 2. Promoción a capa GOLD (idempotente)
-----------------------------------------
START TRANSACTION;

-- 2.1. Borrar linaje de este conjunto (evita FK 1451)
DELETE FROM map_id_origen
WHERE id_ticket IN (
  SELECT f.id_ticket
  FROM f_tickets f
  WHERE f.ticket_code IN (SELECT id_ticket FROM stg_tickets)
);

-- 2.2. Borrar hechos previos del mismo conjunto (por si acaso, idempotencia)
DELETE FROM f_tickets
WHERE ticket_code IN (SELECT id_ticket FROM stg_tickets);

-- 2.3. Insert con normalización de fechas por patrones (evita 1411)
INSERT INTO f_tickets (
  ticket_code, id_canal, id_prioridad, id_estado, id_tipo_real,
  asunto, descripcion, fecha_creacion, fecha_resolucion,
  first_response_time_min, time_to_resolution_min, sla_met
)
SELECT
  s.id_ticket,
  dc.id_canal, dp.id_prioridad, de.id_estado, dt.id_tipo,
  s.resumen, s.descripcion,
  s.fc, s.fz,
  CASE WHEN s.fc IS NULL OR s.fr IS NULL THEN NULL ELSE TIMESTAMPDIFF(MINUTE, s.fc, s.fr) END,
  CASE WHEN s.fc IS NULL OR s.fz IS NULL THEN NULL ELSE TIMESTAMPDIFF(MINUTE, s.fc, s.fz) END,
  CAST(NULLIF(s.sla_met,'') AS UNSIGNED)
FROM (
  SELECT
    st.*,

    -- fecha_creacion -> fc
    CASE
      WHEN NULLIF(TRIM(st.fecha_creacion),'') IS NULL THEN NULL
      WHEN st.fecha_creacion REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
        THEN STR_TO_DATE(
               REPLACE(SUBSTRING_INDEX(SUBSTRING_INDEX(st.fecha_creacion,'Z',1),'.',1),'T',' '),
               CASE
                 WHEN st.fecha_creacion REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%Y-%m-%d %H:%i:%s'
                 WHEN st.fecha_creacion REGEXP ' [0-9]{2}:[0-9]{2}$'  THEN '%Y-%m-%d %H:%i'
                 ELSE '%Y-%m-%d'
               END
             )
      WHEN st.fecha_creacion REGEXP '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}'
        THEN STR_TO_DATE(
               st.fecha_creacion,
               CASE
                 WHEN st.fecha_creacion REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i:%s'
                 WHEN st.fecha_creacion REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i'
                 ELSE '%e/%c/%Y'
               END
             )
      WHEN st.fecha_creacion REGEXP '^[0-9]{1,2}-[0-9]{1,2}-[0-9]{4}'
        THEN STR_TO_DATE(
               st.fecha_creacion,
               CASE
                 WHEN st.fecha_creacion REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i:%s'
                 WHEN st.fecha_creacion REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i'
                 ELSE '%e-%c-%Y'
               END
             )
      ELSE NULL
    END AS fc,

    -- first_reply_at -> fr
    CASE
      WHEN NULLIF(TRIM(st.first_reply_at),'') IS NULL THEN NULL
      WHEN st.first_reply_at REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
        THEN STR_TO_DATE(
               REPLACE(SUBSTRING_INDEX(SUBSTRING_INDEX(st.first_reply_at,'Z',1),'.',1),'T',' '),
               CASE
                 WHEN st.first_reply_at REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%Y-%m-%d %H:%i:%s'
                 WHEN st.first_reply_at REGEXP ' [0-9]{2}:[0-9]{2}$'  THEN '%Y-%m-%d %H:%i'
                 ELSE '%Y-%m-%d'
               END
             )
      WHEN st.first_reply_at REGEXP '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}'
        THEN STR_TO_DATE(
               st.first_reply_at,
               CASE
                 WHEN st.first_reply_at REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i:%s'
                 WHEN st.first_reply_at REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i'
                 ELSE '%e/%c/%Y'
               END
             )
      WHEN st.first_reply_at REGEXP '^[0-9]{1,2}-[0-9]{1,2}-[0-9]{4}'
        THEN STR_TO_DATE(
               st.first_reply_at,
               CASE
                 WHEN st.first_reply_at REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i:%s'
                 WHEN st.first_reply_at REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i'
                 ELSE '%e-%c-%Y'
               END
             )
      ELSE NULL
    END AS fr,

    -- fecha_cierre -> fz
    CASE
      WHEN NULLIF(TRIM(st.fecha_cierre),'') IS NULL THEN NULL
      WHEN st.fecha_cierre REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
        THEN STR_TO_DATE(
               REPLACE(SUBSTRING_INDEX(SUBSTRING_INDEX(st.fecha_cierre,'Z',1),'.',1),'T',' '),
               CASE
                 WHEN st.fecha_cierre REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%Y-%m-%d %H:%i:%s'
                 WHEN st.fecha_cierre REGEXP ' [0-9]{2}:[0-9]{2}$'  THEN '%Y-%m-%d %H:%i'
                 ELSE '%Y-%m-%d'
               END
             )
      WHEN st.fecha_cierre REGEXP '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}'
        THEN STR_TO_DATE(
               st.fecha_cierre,
               CASE
                 WHEN st.fecha_cierre REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i:%s'
                 WHEN st.fecha_cierre REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e/%c/%Y %H:%i'
                 ELSE '%e/%c/%Y'
               END
             )
      WHEN st.fecha_cierre REGEXP '^[0-9]{1,2}-[0-9]{1,2}-[0-9]{4}'
        THEN STR_TO_DATE(
               st.fecha_cierre,
               CASE
                 WHEN st.fecha_cierre REGEXP ':[0-9]{2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i:%s'
                 WHEN st.fecha_cierre REGEXP ' [0-9]{1,2}:[0-9]{2}$' THEN '%e-%c-%Y %H:%i'
                 ELSE '%e-%c-%Y'
               END
             )
      ELSE NULL
    END AS fz
  FROM stg_tickets st
) AS s
JOIN d_canal     dc ON dc.canal     = s.canal
JOIN d_prioridad dp ON dp.prioridad = s.prioridad
JOIN d_estado    de ON de.estado    = s.estado
LEFT JOIN d_tipo dt ON dt.codigo    = s.categoria
WHERE s.fc IS NOT NULL;

-- 2.4. Linaje (evita duplicados si se reejecuta) - L4_demo
INSERT IGNORE INTO map_id_origen (id_ticket, origen, id_origen)
SELECT f.id_ticket, 'L4', st.id_ticket
FROM stg_tickets st
JOIN f_tickets   f ON f.ticket_code = st.id_ticket;

COMMIT;

---------------------
-- 3. Verificaciones
---------------------
-- SELECT COUNT(*) AS stg  FROM stg_tickets;
-- SELECT COUNT(*) AS fact FROM f_tickets WHERE ticket_code IN (SELECT id_ticket FROM stg_tickets);
-- SELECT COUNT(*) AS lin  FROM map_id_origen WHERE origen='manual' AND id_origen IN (SELECT id_ticket FROM stg_tickets);
-- 
-- Esto debería devolver 0 filas:
-- SELECT * FROM f_tickets
-- WHERE ticket_code IN (SELECT id_ticket FROM stg_tickets) AND fecha_resolucion IS NOT NULL AND fecha_resolucion < fecha_creacion;