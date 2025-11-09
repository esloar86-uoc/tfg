# Runbook - TFG esloar86 - **Reproducibilidad de PEC2/PEC3**
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#2-entorno-python)
[![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white)](#3-base-de-datos-mysql-local)
[![Power BI](https://img.shields.io/badge/Power%20BI-Desktop-F2C811?logo=powerbi&logoColor=black)](#8-power-bi-pec3)
[![License](https://img.shields.io/badge/License-CC0%20%7C%20CC%20BY--4.0-lightgrey)](#creditos-y-licencias)

> [!IMPORTANT]
> Este runbook **no incluye credenciales reales** por seguridad.
> Ejecuta los comandos en la **Terminal de VS Code** (PowerShell) dentro de la carpeta del repo.

---

## Índice
- [Visión general](#-visión-general)
- [0) Estructura del proyecto](#0-estructura-del-proyecto)
- [1) Clonar e inicializar](#1-clonar-e-inicializar)
- [2) Entorno Python](#2-entorno-python)
- [3) Base de datos MySQL (local)](#3-base-de-datos-mysql-local)
- [4) Datos (sintéticos / PEC2)](#4-datos-sintéticos--pec2)
- [5) ETL-A (ingesta → limpieza → carga)](#5-etl-a-ingesta--limpieza--carga)
- [6) ML (entrenar · evaluar · predecir)](#6-ml-entrenar--evaluar--predecir)
- [7) ETL-B (cargar predicciones al DWH)](#7-etl-b-cargar-predicciones-al-dwh)
- [8) Power BI (PEC3)](#8-power-bi-pec3)
- [9) Versionado (ramas y tags)](#9-versionado-ramas-y-tags)
- [Apéndice: Git útil](#apéndice-git-útil)
- [Créditos y licencias](#creditos-y-licencias)

---

## Visión general
Repo: **https://github.com/esloar86-uoc/tfg**  
SO: **Windows 10/11** · DB: **MySQL 8.x** · Python: **3.10+** · BI: **Power BI Desktop**

> [!NOTE]
> Los pasos marcados como **PEC2** se completan en esta entrega. **PEC3** se cubrirá cuando toque.

---

## 0) Estructura del proyecto
```text
.
├─ bi/                  # PBIX y exports (PEC3)
├─ db/                  # DDL, vistas KPI y scripts SQL
├─ data/
│  ├─ raw/              # Datos brutos (Kaggle + sintéticos)
│  └─ processed/        # Datos limpios/particionados (ETL-A)
├─ docs/                # Memoria y anexos
├─ etl/                 # Scripts ETL-A / ETL-B / utilidades
├─ ml/                  # Entrenamiento, evaluación, predicción
├─ logs/                # Logs de ETL y ML
├─ requirements.txt
├─ runbook.md           # Este documento
└─ README.md
```

---

## 1) Clonar e inicializar
```bash
# Clonar (HTTPS)
git clone https://github.com/esloar86-uoc/tfg.git
cd tfg

# Recomendado: Git LFS para binarios (docx/png/pbix)
git lfs install
```

---

## 2) Entorno Python
```powershell
# Crear venv y activarlo (Windows + PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Smoke test
python -c "import pandas, sklearn, sqlalchemy, pymysql; print('OK')"
```

---

## 3) Base de datos MySQL (local)
Asegúrate de que el servicio **MySQL80** está arrancado.

```bash
# Crear BD y objetos (DDL + vistas KPI)
mysql -u <user> -p < db/01_schema_ddl.sql
mysql -u <user> -p < db/02_views_kpi.sql
```

**Comprobaciones rápidas (cliente mysql o Workbench):**
```sql
SHOW DATABASES LIKE 'tfg';
USE tfg;
SHOW TABLES;
SHOW FULL TABLES;
```

> [!IMPORTANTE]
> La collation del esquema es **utf8mb4_0900_ai_ci** para admitir acentos y ordenación moderna en MySQL 8.

---

## 4) Datos (sintéticos / PEC2)
Coloca los CSV de entrada en `data/raw/`.  
Ejemplos: `email.csv`, `portal_documental.csv`, `portal_interno.csv`, `portal_soporte.csv`, etc.

---

## 5) ETL-A (ingesta - limpieza - carga)
**Objetivo:** cargar los tickets a **staging** (`stg_tickets`), normalizar y poblar la **gold** (`f_tickets` + dimensiones).

### 5.1 Ejecutar el ETL-A
```powershell
# (Ejemplo) — ajusta rutas si cambian
python etl/etl_a.py ^
  --input data/raw ^
  --out data/processed ^
  --mysql-url "mysql+pymysql://<user>:<pass>@localhost:3306/tfg" ^
  --log logs/etl_a_%DATE%.log
```

### 5.2 Verificaciones mínimas (SQL)
```sql
USE tfg;

-- Conteos esperados
SELECT COUNT(*) AS stg  FROM stg_tickets;
SELECT COUNT(*) AS fact FROM f_tickets;
SELECT COUNT(*) AS lin  FROM map_id_origen WHERE origen='manual';

-- Calidad temporal (debe devolver 0 filas)
SELECT * FROM f_tickets
WHERE fecha_resolucion IS NOT NULL
  AND fecha_resolucion < fecha_creacion;

-- Canales válidos en staging
SELECT s.canal, COUNT(*) n
FROM stg_tickets s
LEFT JOIN d_canal d ON d.canal = s.canal
WHERE d.id_canal IS NULL
GROUP BY s.canal;
```

> [!TIP]
> Si aparecen valores como `PORTAL_SOPORTE`, normaliza en staging:
> ```sql
> UPDATE stg_tickets
> SET canal = CASE
>   WHEN UPPER(canal)='PORTAL_SOPORTE'    THEN 'Portal Soporte General'
>   WHEN UPPER(canal)='PORTAL_INTERNO'    THEN 'Portal Interno'
>   WHEN UPPER(canal)='PORTAL_DOCUMENTAL' THEN 'Portal Documental'
>   WHEN UPPER(canal)='EMAIL'             THEN 'Email'
>   ELSE canal
> END;
> ```

---

## 6) ML (entrenar - evaluar - predecir) [EN PROCESO]
**Fuente de entrenamiento:** vista `vw_ml_training` (gold etiquetada manualmente).  
**Etiquetas:** `id_tipo_real` (FK a `d_tipo`).  
**Texto:** `asunto` + `descripcion` + metadatos (`canal`, `prioridad`, `estado`, `sla_met`).

```powershell
# Entrenar [EN PROCESO]
python ml/train.py ^
  --train data/processed/train.csv ^
  --text-cols asunto descripcion ^
  --cat-cols canal prioridad estado sla_met ^
  --label-col id_tipo_real ^
  --model-out artifacts/model_best.pkl ^
  --cv 5

# Evaluar [EN PROCESO]
python ml/evaluate.py ^
  --model artifacts/model_best.pkl ^
  --test data/processed/test.csv ^
  --report-out logs/ml_report.json ^
  --confusion-out logs/confusion_matrix.png

# Predecir sobre nuevas muestras (gold sin etiqueta) [EN PROCESO]
python ml/predict.py ^
  --model artifacts/model_best.pkl ^
  --input data/processed/nuevas_muestras.csv ^
  --out data/processed/predicciones.csv
```

---

## 7) ETL-B (cargar predicciones al DWH) [EN PROCESO]
Inserta las predicciones en `tickets_clasificados` (no se contaminan los **hechos**):
```powershell
python etl/load_predictions.py ^
  --pred data/processed/predicciones.csv ^
  --mysql-url "mysql+pymysql://<user>:<pass>@localhost:3306/tfg"
```

Consultas de apoyo:
```sql
-- Vista de evaluación (real vs predicho)
SELECT * FROM vw_eval_confusion;

-- Métricas por canal/periodo
SELECT * FROM vw_kpi_accuracy_by_channel;
```

---

## 8) Power BI (PEC3) [EN PROCESO]
- Conecta a **MySQL → BD `tfg`**.
- Tablas/vistas: `f_tickets`, `d_*`, `vw_ml_training`, `vw_eval_confusion`, `vw_kpi_*`.
- Publica el `.pbix` en `bi/` o añade capturas a `docs/`.

---

## 9) Versionado (ramas y tags) [EN PROCESO]
```bash
# Trabajo por entregas
git switch -c feature/pec2-etl-mysql   # crear y cambiar a rama
# ... commits ...
git push -u origin feature/pec2-etl-mysql

# Tag para congelar la entrega
git tag -a v-pec2 -m "Entrega PEC2"
git push origin v-pec2
```

---

## Apéndice: Git útil
```bash
# Estado y ramas
git status
git branch -vv
git remote -v

# Subir cambios
git add -A
git commit -m "feat: ETL-A y documentación"
git push

# Actualizar desde remoto sin mezclar historiales locales
git fetch origin
git reset --hard origin/main
```

---

## Créditos y licencias [EN PROCESO]
Licencias del proyecto: **CC0** y **CC BY 4.0** (según fichero).  
© esloar86 — UOC 2025.
