USE tfg;

-- 1) Catálogo de experimentos
CREATE TABLE IF NOT EXISTS ml_experimento (
  id_experimento    TINYINT AUTO_INCREMENT PRIMARY KEY,
  codigo            VARCHAR(20)  NOT NULL,   -- 'E1', 'E2', 'L4_demo', etc
  descripcion       VARCHAR(255) NOT NULL,
  dataset_origen    VARCHAR(50)  NOT NULL,
  fecha_ejecucion   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2) Ampliar d_modelo para guardar algoritmo y params
ALTER TABLE d_modelo
  ADD COLUMN algoritmo      VARCHAR(30)  NULL,
  ADD COLUMN params_resumen VARCHAR(255) NULL;

-- 3) Resultados globales por experimento + modelo + dataset
CREATE TABLE IF NOT EXISTS ml_resultado_global (
  id_resultado     INT AUTO_INCREMENT PRIMARY KEY,
  id_experimento   TINYINT      NOT NULL,
  modelo_version   VARCHAR(30)  NOT NULL,
  dataset          VARCHAR(20)  NOT NULL,
  accuracy_pct     DECIMAL(5,2) NOT NULL,
  f1_macro_pct     DECIMAL(5,2) NULL,
  f1_weighted_pct  DECIMAL(5,2) NULL,
  precision_macro_pct DECIMAL(5,2) NULL,
  recall_macro_pct    DECIMAL(5,2) NULL,
  n_muestras       INT          NOT NULL,
  tiempo_seg       DECIMAL(8,2) NULL,
  CONSTRAINT fk_mrg_exp
    FOREIGN KEY (id_experimento) REFERENCES ml_experimento(id_experimento),
  CONSTRAINT fk_mrg_model
    FOREIGN KEY (modelo_version) REFERENCES d_modelo(modelo_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4) Resultados por clase
CREATE TABLE IF NOT EXISTS ml_resultado_por_clase (
  id_resultado_clase INT AUTO_INCREMENT PRIMARY KEY,
  id_experimento     TINYINT      NOT NULL,
  modelo_version     VARCHAR(30)  NOT NULL,
  dataset            VARCHAR(20)  NOT NULL,
  id_tipo_real       TINYINT      NOT NULL,   -- << aquí el cambio
  precision_pct      DECIMAL(5,2) NULL,
  recall_pct         DECIMAL(5,2) NULL,
  f1_pct             DECIMAL(5,2) NULL,
  soporte_n          INT          NOT NULL,
  CONSTRAINT fk_mrc_exp   FOREIGN KEY (id_experimento)
      REFERENCES ml_experimento(id_experimento),
  CONSTRAINT fk_mrc_model FOREIGN KEY (modelo_version)
      REFERENCES d_modelo(modelo_version),
  CONSTRAINT fk_mrc_tipo  FOREIGN KEY (id_tipo_real)
      REFERENCES d_tipo(id_tipo)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;

-- 5) Matrices de confusión por experimento/modelo/dataset
CREATE TABLE IF NOT EXISTS ml_confusion (
  id_confusion   INT AUTO_INCREMENT PRIMARY KEY,
  id_experimento TINYINT      NOT NULL,
  modelo_version VARCHAR(30)  NOT NULL,
  dataset        VARCHAR(20)  NOT NULL,
  id_real        TINYINT      NOT NULL,   -- cambio aquí
  id_pred        TINYINT      NOT NULL,   -- y aquí
  n              INT          NOT NULL,
  CONSTRAINT fk_mc_exp   FOREIGN KEY (id_experimento)
      REFERENCES ml_experimento(id_experimento),
  CONSTRAINT fk_mc_model FOREIGN KEY (modelo_version)
      REFERENCES d_modelo(modelo_version),
  CONSTRAINT fk_mc_real  FOREIGN KEY (id_real)
      REFERENCES d_tipo(id_tipo),
  CONSTRAINT fk_mc_pred  FOREIGN KEY (id_pred)
      REFERENCES d_tipo(id_tipo)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;


------------
-- VISTAS --
------------
-- Vista de resultados globales para BI
CREATE OR REPLACE VIEW vw_ml_resultado_global AS
SELECT
  e.codigo           AS experimento,
  e.descripcion      AS experimento_desc,
  rg.dataset,
  m.modelo_version,
  m.algoritmo,
  m.params_resumen,
  rg.n_muestras,
  rg.tiempo_seg,
  rg.accuracy_pct,
  rg.f1_macro_pct,
  rg.f1_weighted_pct,
  rg.precision_macro_pct,
  rg.recall_macro_pct
FROM ml_resultado_global rg
JOIN ml_experimento e ON e.id_experimento = rg.id_experimento
JOIN d_modelo      m ON m.modelo_version   = rg.modelo_version;

-- Vista de métricas por clase para BI
CREATE OR REPLACE VIEW vw_ml_resultado_por_clase AS
SELECT
  e.codigo        AS experimento,
  rg.dataset,
  m.modelo_version,
  m.algoritmo,
  t.codigo        AS real_cat,
  t.nombre        AS real_cat_nombre,
  rg.precision_pct,
  rg.recall_pct,
  rg.f1_pct,
  rg.soporte_n
FROM ml_resultado_por_clase rg
JOIN ml_experimento e ON e.id_experimento = rg.id_experimento
JOIN d_modelo      m ON m.modelo_version   = rg.modelo_version
JOIN d_tipo        t ON t.id_tipo          = rg.id_tipo_real;

---------------------------------
-- Reg. Experimentos / Modelos --
---------------------------------
INSERT INTO ml_experimento (codigo, descripcion, dataset_origen)
VALUES
  ('E1', 'Baselines solo texto (NB, RL, SVM) sobre VALID', 'VALID'),
  ('E2', 'Baselines texto + metadatos (NB, RL, SVM) sobre VALID', 'VALID'),
  ('L4', 'Evaluación manual 50 tickets etiquetados (SVM_v1.1)', 'L4_manual');

INSERT INTO d_modelo (modelo_version, descripcion, fecha_entrenamiento, algoritmo, params_resumen)
VALUES
  ('E1_NB',  'Naive Bayes Multinomial (E1, solo texto)', NOW(), 'MultinomialNB', 'TF-IDF texto; alpha=1.0'),
  ('E1_RL',  'Regresión Logística (E1, solo texto)', NOW(), 'LogisticRegression', 'TF-IDF texto; solver=lbfgs'),
  ('E1_SVM', 'SVM lineal (E1, solo texto)', NOW(), 'LinearSVC', 'TF-IDF texto; C=1.0'),
  ('E2_SVM', 'SVM lineal (E2, texto + canal/prioridad)', NOW(), 'LinearSVC', 'TF-IDF + metadatos'),
  ('SVM_v1.1', 'SVM lineal L4 - modelo referencia producción', NOW(), 'LinearSVC', 'TF-IDF texto; entrenado con TRAIN+VALID+L4');


----------------------------
-- Tablas Staging para ML --
----------------------------

CREATE TABLE IF NOT EXISTS stg_ml_resultado_global (
  experimento      VARCHAR(10),
  id_experimento   TINYINT,
  modelo_version   VARCHAR(30),
  dataset          VARCHAR(20),
  accuracy_pct     DECIMAL(5,2),
  f1_macro_pct     DECIMAL(5,2),
  f1_weighted_pct  DECIMAL(5,2),
  precision_macro_pct DECIMAL(5,2),
  recall_macro_pct    DECIMAL(5,2),
  n_muestras       INT
);

CREATE TABLE IF NOT EXISTS stg_ml_resultado_por_clase (
  experimento      VARCHAR(10),
  id_experimento   TINYINT,
  modelo_version   VARCHAR(30),
  dataset          VARCHAR(20),
  real_cat         VARCHAR(10),
  precision_pct    DECIMAL(5,2),
  recall_pct       DECIMAL(5,2),
  f1_pct           DECIMAL(5,2),
  soporte_n        INT
);

CREATE TABLE IF NOT EXISTS stg_ml_confusion (
  experimento      VARCHAR(10),
  id_experimento   TINYINT,
  modelo_version   VARCHAR(30),
  dataset          VARCHAR(20),
  real_cat         VARCHAR(10),
  pred_cat         VARCHAR(10),
  n                INT
);