--==========================================================
-- 01_schema_ddl.sql 
-- Esquema de almacén para el TFG
--==========================================================

CREATE DATABASE IF NOT EXISTS tfg
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE tfg;

-- Modo estricto, permitiendo insert select tolerantes en staging
SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION';

--- STAGING (reejecutable) ---
CREATE TABLE IF NOT EXISTS stg_tickets (
  id_ticket         VARCHAR(64)  NULL,
  canal             VARCHAR(30)  NULL,
  fecha_creacion    VARCHAR(40)  NULL,
  first_reply_at    VARCHAR(40)  NULL,
  fecha_cierre      VARCHAR(40)  NULL,
  estado            VARCHAR(30)  NULL,
  prioridad         VARCHAR(20)  NULL,
  predicted         VARCHAR(10)  NULL,
  categoria         VARCHAR(10)  NULL,
  agente_id         VARCHAR(100) NULL,
  sla_target_horas  VARCHAR(10)  NULL,
  sla_met           VARCHAR(10)  NULL,
  resumen           VARCHAR(255) NULL,
  descripcion       TEXT         NULL,
  origen            VARCHAR(20)  NULL,
  id_origen         VARCHAR(64)  NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--- Dimensiones ---
CREATE TABLE IF NOT EXISTS d_canal (
  id_canal      TINYINT      NOT NULL,
  canal         VARCHAR(30)  NOT NULL,
  PRIMARY KEY (id_canal),
  UNIQUE KEY uk_canal (canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS d_prioridad (
  id_prioridad  TINYINT      NOT NULL,
  prioridad     VARCHAR(20)  NOT NULL,
  PRIMARY KEY (id_prioridad),
  UNIQUE KEY uk_prioridad (prioridad)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS d_estado (
  id_estado     TINYINT      NOT NULL,
  estado        VARCHAR(30)  NOT NULL,
  PRIMARY KEY (id_estado),
  UNIQUE KEY uk_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS d_tipo (
  id_tipo  TINYINT      NOT NULL,
  codigo   VARCHAR(10)  NOT NULL,
  nombre   VARCHAR(60)  NOT NULL,
  PRIMARY KEY (id_tipo),
  UNIQUE KEY uk_tipo_codigo (codigo),
  UNIQUE KEY uk_tipo_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--- Hechos (facts) ---
CREATE TABLE IF NOT EXISTS f_tickets (
  id_ticket                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ticket_code                VARCHAR(64) UNIQUE,
  id_canal                   TINYINT NOT NULL,
  id_prioridad               TINYINT NOT NULL,
  id_estado                  TINYINT NOT NULL,
  id_tipo_real               TINYINT NULL,
  asunto                     VARCHAR(255) NOT NULL,
  descripcion                TEXT,
  fecha_creacion             DATETIME NOT NULL,
  fecha_resolucion           DATETIME NULL,
  first_response_time_min    INT NULL,
  time_to_resolution_min     INT NULL,
  sla_met                    TINYINT NULL,
  PRIMARY KEY (id_ticket),
  CONSTRAINT fk_ft_canal     FOREIGN KEY (id_canal)     REFERENCES d_canal(id_canal),
  CONSTRAINT fk_ft_prioridad FOREIGN KEY (id_prioridad) REFERENCES d_prioridad(id_prioridad),
  CONSTRAINT fk_ft_estado    FOREIGN KEY (id_estado)    REFERENCES d_estado(id_estado),
  CONSTRAINT fk_ft_tipo_real FOREIGN KEY (id_tipo_real) REFERENCES d_tipo(id_tipo),
  INDEX ix_fc (fecha_creacion),
  INDEX ix_canal (id_canal),
  INDEX ix_tipo (id_tipo_real),
  FULLTEXT KEY ft_texto (asunto, descripcion),
  CONSTRAINT ck_resolucion_fecha CHECK (fecha_resolucion IS NULL OR fecha_resolucion >= fecha_creacion),
  CONSTRAINT ck_ttr_nonneg       CHECK (time_to_resolution_min  IS NULL OR time_to_resolution_min  >= 0),
  CONSTRAINT ck_frt_nonneg       CHECK (first_response_time_min IS NULL OR first_response_time_min >= 0),
  CONSTRAINT ck_sla_met_bool     CHECK (sla_met IN (0,1) OR sla_met IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--- Linajes / inferencias ---
CREATE TABLE IF NOT EXISTS map_id_origen (
  id_ticket  INT UNSIGNED NOT NULL,
  origen     ENUM('kaggle1','kaggle2','synt','manual') NOT NULL,
  id_origen  VARCHAR(64) NOT NULL,
  PRIMARY KEY (id_ticket, origen, id_origen),
  CONSTRAINT fk_map_ticket FOREIGN KEY (id_ticket) REFERENCES f_tickets(id_ticket)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS tickets_clasificados (
  id_ticket         INT UNSIGNED NOT NULL,
  id_tipo_predicho  TINYINT NULL,
  score_predicho    DECIMAL(5,4) NULL,
  modelo_version    VARCHAR(50) NULL,
  fecha_inferencia  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_ticket),
  CONSTRAINT fk_tc_ticket FOREIGN KEY (id_ticket)        REFERENCES f_tickets(id_ticket),
  CONSTRAINT fk_tc_tipo   FOREIGN KEY (id_tipo_predicho) REFERENCES d_tipo(id_tipo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--- Semillas ---
INSERT IGNORE INTO d_canal (id_canal, canal) VALUES
  (1,'Email'),(2,'Portal Soporte General'),(3,'Portal Documental'),(4,'Portal Interno');

--- Unificar la taxonomía a 'Urgente' (no 'Crítica') ---
INSERT IGNORE INTO d_prioridad (id_prioridad, prioridad) VALUES
  (1,'Baja'),(2,'Media'),(3,'Alta'),(4,'Urgente');

INSERT IGNORE INTO d_estado (id_estado, estado) VALUES
  (1,'Pendiente'),(2,'En curso'),(3,'Resuelto'),(4,'Cerrado'),(5,'Reabierto');

INSERT IGNORE INTO d_tipo (id_tipo, codigo, nombre) VALUES
  (1,'ACC','Acceso y credenciales'),
  (2,'SW','Software'),
  (3,'HW','Hardware'),
  (4,'NET','Red y conectividad'),
  (5,'MAIL','Correo electrónico'),
  (6,'APP','Aplicaciones internas'),
  (7,'SRV','Servidores/infraestructura'),
  (8,'POL','Políticas y procedimientos');

ALTER TABLE f_tickets AUTO_INCREMENT = 401;

--- Vistas ---
CREATE OR REPLACE VIEW vw_tickets_base AS
SELECT 
  f.id_ticket, f.ticket_code,
  c.canal, p.prioridad, e.estado,
  t.nombre AS tipo_real,
  f.asunto, f.descripcion,
  f.fecha_creacion, f.fecha_resolucion,
  f.first_response_time_min, f.time_to_resolution_min,
  f.sla_met
FROM f_tickets f
JOIN d_canal c      ON c.id_canal = f.id_canal
JOIN d_prioridad p  ON p.id_prioridad = f.id_prioridad
JOIN d_estado e     ON e.id_estado = f.id_estado
LEFT JOIN d_tipo t  ON t.id_tipo   = f.id_tipo_real;

CREATE OR REPLACE VIEW vw_tickets_para_modelo AS
SELECT 
  f.id_ticket,
  COALESCE(f.ticket_code, CONCAT('SOPORTE-', LPAD(f.id_ticket, 4, '0'))) AS ticket_code,
  f.asunto, f.descripcion,
  c.canal, p.prioridad, e.estado,
  f.sla_met
FROM f_tickets f
JOIN d_canal c      ON c.id_canal = f.id_canal
JOIN d_prioridad p  ON p.id_prioridad = f.id_prioridad
JOIN d_estado e     ON e.id_estado = f.id_estado;