Runbook — Reproducibilidad TFG esloar86
=================================================

Repo: https://github.com/esloar86-uoc/tfg
SO: Windows 10/11  |  DB: MySQL 8.x  |  Python: 3.10+  |  BI: Power BI Desktop

IMPORTANTE
----------
- Este runbook no incluye credenciales reales por seguridad. Se incluirán más adelante si es requerido por el consultor del TFG.
- Ejecuta los comandos en la Terminal de VS Code (PowerShell) dentro de la carpeta del repo.
- Los pasos marcados como (PEC2) o (PEC3) se completarán cuando se completen esas entregas.

0) Estructura del proyecto (provisional, se irá actualizando si cambia)
---------------------------------------
.
├─ bi/                  # Power BI (.pbix) y exports
├─ db/                  # DDL y vistas (SQL)
├─ data/
│  ├─ raw/              # Datos brutos (sintéticos)
│  └─ processed/        # Datos procesados/particionados
├─ docs/                # Memoria y anexos
├─ etl/                 # Scripts ETL
├─ ml/                  # Entrenamiento/evaluación
├─ gantt/               # Diagramas de planificación (.gan/.png)
├─ logs/                # Logs ETL/ML
├─ requirements.txt
├─ runbook.md           # 
└─ README.md

1) Clonar e inicializar
-----------------------
# Clonar (HTTPS)
git clone https://github.com/esloar86-uoc/tfg.git
cd tfg

# Git LFS para binarios (docx, png, pbix)
git lfs install

2) Entorno Python
-----------------
# Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Comprobación rápida
python -c "import pandas, sklearn, sqlalchemy, pymysql; print('OK')"

3) Base de datos MySQL (local)
------------------------------
# Asegúrate de que el servicio MySQL80 está arrancado.

# Crear base de datos y esquema.
mysql -u <user> -p < db\01_schema_ddl.sql
mysql -u <user> -p < db\02_views_kpi.sql

# Comprobaciones básicas (desde cliente mysql)
SHOW DATABASES LIKE 'tfg';
USE tfg;
SHOW TABLES;

4) Datos (sintéticos / PEC2)
----------------------------
# Coloca los CSV de entrada en: data\raw\

5) ETL (ingesta → limpieza → carga en MySQL) — PEC2
---------------------------------------------------
# Activar entorno
.venv\Scripts\activate

# Ejecutar ETL (ejemplo)
python etl\etl.py ^
  --input data\raw ^
  --out data\processed ^
  --mysql-url "mysql+pymysql://<user>:<pass>@localhost:3306/tfg" ^
  --log logs\etl_%DATE%.log

# Resultado esperado
# - CSV limpios en data\processed (train/test si procede)
# - Tablas pobladas en MySQL (f_tickets, d_*).

6) ML (entrenar, evaluar, predecir) — PEC2
------------------------------------------
# Entrenamiento (usa un YAML de config si existe; si no, parámetros CLI)
python ml\train.py ^
  --train data\processed\train.csv ^
  --text-col descripcion ^
  --label-col categoria_real ^
  --model-out artifacts\model_best.pkl ^
  --cv-folds 5

# Evaluación hold-out
python ml\evaluate.py ^
  --model artifacts\model_best.pkl ^
  --test data\processed\test.csv ^
  --report-out logs\ml_report.json ^
  --confusion-out logs\confusion_matrix.png

# Predicción sobre muestras nuevas
python ml\predict.py ^
  --model artifacts\model_best.pkl ^
  --input data\processed\nuevas_muestras.csv ^
  --out data\processed\predicciones.csv

7) Integración ML - DWH (PEC3)
-------------------------------
# Cargar predicciones (tipo_predicho, score_predicho) a MySQL
# PSe puede incluir un script de inserción "en bulk":
python etl\load_predictions.py ^
  --pred data\processed\predicciones.csv ^
  --mysql-url "mysql+pymysql://<user>:<pass>@localhost:3306/tfg"

# Verificar vistas KPI que usen el campo predicho
mysql -u <user> -p -e "USE tfg; SHOW FULL TABLES;"

8) Power BI (PEC3)
------------------
# Conectar a MySQL:
#  - Servidor: localhost
#  - Base de datos: tfg
#  - Tablas: f_tickets, d_*, v_kpi_*
# Crear medidas DAX y paneles (SLA, backlog, T.M.R., acierto por canal/periodo).
# Publica exports en /bi o captura en /docs si procede.

9) Versionado (ramas + tags)
----------------------------
# Flujo por entregas
#  - Trabaja en rama por PEC (pec2/…, pec3/…).
#  - Pull Request → main.
#  - Tag de entrega (congelar estado):
git tag -a v-pec1 -m "Entrega PEC1"
git push origin v-pec1

# Para PEC2/PEC3:
git tag -a v-pec2 -m "Entrega PEC2"
git push origin v-pec2

10) Planificación (Gantt)
-------------------------
# Fichero del proyecto:
gantt\esloar86_gantt.gan

# Exportar imagen para adjuntar en la memoria:
gantt\esloar86_gantt.png




Apéndice: Comandos útiles de Git
--------------------------------
# Estado y ramas
git status
git branch -vv
git remote -v

# Subir cambios
git add -A
git commit -m "mensaje"
git push

# Resolver “pull con historias no relacionadas” reseteando a remoto
git fetch origin
git reset --hard origin/main

# Eliminar archivo del historial (caso excepcional)
# (Requierió 'pip install git-filter-repo', y push --force)
git filter-repo --path runbook.md --invert-paths --force

FIN