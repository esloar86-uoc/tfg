--==================================================================================
-- 03_ml_schema.sql
-- Esquema de soporte para ML: versionado de modelos, almacenamiento de predicciones
-- y vistas de trabajo (entrenamiento, pendientes e informes de evaluación).
--==================================================================================

USE tfg;

-- 1) Catálogo de modelos (versionado)
CREATE TABLE IF NOT EXISTS d_modelo (
  modelo_version        VARCHAR(30) NOT NULL,
  descripcion           VARCHAR(255) NULL,
  fecha_entrenamiento   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (modelo_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2) Predicciones por ticket (separadas del hecho para evitar contaminación)
CREATE TABLE IF NOT EXISTS tickets_clasificados (
  id_clasificacion   INT NOT NULL AUTO_INCREMENT,
  id_ticket          INT NOT NULL,
  id_tipo_predicho   INT NOT NULL,
  score_predicho     DECIMAL(5,4) NULL,
  modelo_version     VARCHAR(30) NOT NULL,
  fecha_inferencia   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_clasificacion),
  CONSTRAINT fk_tc_ticket  FOREIGN KEY (id_ticket)        REFERENCES f_tickets(id_ticket) ON DELETE CASCADE,
  CONSTRAINT fk_tc_tipo    FOREIGN KEY (id_tipo_predicho) REFERENCES d_tipo(id_tipo),
  CONSTRAINT fk_tc_modelo  FOREIGN KEY (modelo_version)   REFERENCES d_modelo(modelo_version),
  CONSTRAINT chk_tc_score  CHECK (score_predicho IS NULL OR (score_predicho >= 0 AND score_predicho <= 1)),
  UNIQUE KEY uk_ticket_modelo (id_ticket, modelo_version),
  KEY idx_tc_ticket  (id_ticket),
  KEY idx_tc_modelo  (modelo_version),
  KEY idx_tc_tipo    (id_tipo_predicho)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3) Vista de entrenamiento (gold etiquetado manual)
CREATE OR REPLACE VIEW vw_ml_training AS
SELECT
  f.id_ticket,
  CONCAT_WS(' ', NULLIF(f.asunto,''), NULLIF(f.descripcion,'')) AS texto,
  f.id_canal, f.id_prioridad, f.id_estado, f.sla_met,
  f.id_tipo_real AS etiqueta
FROM f_tickets f
WHERE f.id_tipo_real IS NOT NULL;

-- 4) Vista de pendientes de clasificar (sin predicción para la versión actual)
--  (se dejan todas las versiones por simplicidad, operativa filtra modelo al insertar).
CREATE OR REPLACE VIEW vw_pendientes_clasificar AS
SELECT
  f.id_ticket,
  CONCAT_WS(' ', NULLIF(f.asunto,''), NULLIF(f.descripcion,'')) AS texto,
  f.id_canal, f.id_prioridad, f.id_estado, f.sla_met
FROM f_tickets f
LEFT JOIN tickets_clasificados tc
  ON tc.id_ticket = f.id_ticket
WHERE tc.id_ticket IS NULL;

-- 5) Vista de evaluación (real vs. predicho)
CREATE OR REPLACE VIEW vw_eval_confusion AS
SELECT
  dr.codigo AS real_cat,
  dp.codigo AS pred_cat,
  COUNT(*)  AS n
FROM f_tickets f
JOIN tickets_clasificados tc ON tc.id_ticket = f.id_ticket
JOIN d_tipo dr ON dr.id_tipo = f.id_tipo_real
JOIN d_tipo dp ON dp.id_tipo = tc.id_tipo_predicho
GROUP BY dr.codigo, dp.codigo;

-- 6) Tickets con texto + METADATOS + etiqueta real (para entrenar/validar)
CREATE OR REPLACE VIEW vw_tickets_para_modelo AS
SELECT
  f.id_ticket,
  CONCAT_WS(' ', NULLIF(f.asunto,''), NULLIF(f.descripcion,'')) AS texto,
  f.id_canal,
  f.id_prioridad,
  f.id_estado,
  f.sla_met,
  f.id_tipo_real
FROM f_tickets f
WHERE f.id_tipo_real IS NOT NULL;