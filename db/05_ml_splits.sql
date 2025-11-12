--==========================================================
-- 
-- 05_ml_splits.sql 
--==========================================================
USE tfg;

-- 1) Vista base para ML (por si cambia vw_ml_training en el futuro)
CREATE OR REPLACE VIEW vw_tickets_base AS
SELECT 
  f.id_ticket,
  CONCAT_WS(' ', NULLIF(f.asunto,''), NULLIF(f.descripcion,'')) AS texto,
  f.id_canal,
  f.id_prioridad,
  f.id_estado,
  f.sla_met,
  f.id_tipo_real   -- etiqueta "verdad terreno"
FROM f_tickets f;

-- 2) Split reproducible (80/20) usando CRC32 del id_ticket
CREATE OR REPLACE VIEW vw_ml_train_split AS
SELECT b.*
FROM vw_tickets_base b
WHERE
  b.texto IS NOT NULL
  AND LENGTH(TRIM(b.texto)) >= 5
  AND (CRC32(b.id_ticket) % 5) IN (1,2,3,4);   -- 80%

CREATE OR REPLACE VIEW vw_ml_valid_split AS
SELECT b.*
FROM vw_tickets_base b
WHERE
  b.texto IS NOT NULL
  AND LENGTH(TRIM(b.texto)) >= 5
  AND (CRC32(b.id_ticket) % 5) IN (0);         -- 20%

-- 3)
-- 3.1) Textos que puedan resultar problemáticos (vacíos/cortos)
CREATE OR REPLACE VIEW vw_ml_text_quality AS
SELECT 
  SUM(CASE WHEN b.texto IS NULL OR LENGTH(TRIM(b.texto)) < 5 THEN 1 ELSE 0 END) AS textos_invalidos,
  COUNT(*) AS total
FROM vw_tickets_base b;

-- 3.2) Distribución por clase en cada split
CREATE OR REPLACE VIEW vw_ml_dist_train AS
SELECT dt.codigo AS real_cat, COUNT(*) AS n
FROM vw_ml_train_split t
JOIN d_tipo dt ON dt.id_tipo = t.id_tipo_real
GROUP BY dt.codigo
ORDER BY n DESC;

CREATE OR REPLACE VIEW vw_ml_dist_valid AS
SELECT dt.codigo AS real_cat, COUNT(*) AS n
FROM vw_ml_valid_split v
JOIN d_tipo dt ON dt.id_tipo = v.id_tipo_real
GROUP BY dt.codigo
ORDER BY n DESC;

------------------
-- Verificaciones:
------------------
-- Tamaños (aprox. 80/20 del total "válido")
-- USE tfg;
-- SELECT (SELECT COUNT(*) FROM vw_ml_train_split) AS train_rows,
--        (SELECT COUNT(*) FROM vw_ml_valid_split) AS valid_rows;

-- Calidad de texto (idealmente textos_invalidos = 0)
-- USE tfg;
-- SELECT * FROM vw_ml_text_quality;

-- Distribución por clase
-- USE tfg;
-- SELECT * FROM vw_ml_dist_train;
-- SELECT * FROM vw_ml_dist_valid;
