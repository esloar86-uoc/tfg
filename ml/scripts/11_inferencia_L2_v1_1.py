from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import load
from sklearn.metrics import classification_report, confusion_matrix

#-------------------------
# Rutas base del proyecto
#-------------------------
ROOT = Path(__file__).resolve().parents[2]

# CSV L2
L2_PATH = ROOT / "data" / "lotes" / "L2_manual_cat.csv"

# Carpeta modelo SVM v1.1 entrenado con los errores de L1
RUN_V11 = ROOT / "resultados" / "modelos_produccion" / "SVM_v1_1_L1"
MODEL_PATH = RUN_V11 / "model.joblib"
LABELS_PATH = RUN_V11 / "labels.json"

# Carpeta de salida para este nuevo lote
OUT_DIR = ROOT / "resultados" / "lotes" / "L2_SVM_v1_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

#-----------------------
# 1) Cargar datos de L2
#-----------------------
print(f"Leyendo CSV de L2 desde: {L2_PATH}")
df = pd.read_csv(L2_PATH, sep=";", encoding="utf-8")

# Comprobaciones mínimas
for col in ("resumen", "descripcion", "categoria"):
    if col not in df.columns:
        raise ValueError(f"No se encuentra la columna '{col}' en L2_manual_cat.csv")

# Construir columna de texto como en TRAIN/VALID
df["texto"] = (
    df["resumen"].fillna("").astype(str)
    + " "
    + df["descripcion"].fillna("").astype(str)
).str.strip()

# Etiqueta real (manual)
df["real_cat"] = df["categoria"].astype(str).str.strip()

print("Ejemplo de texto y etiqueta real en L2:")
print(df[["id_ticket", "real_cat", "texto"]].head(3))

#-------------------------------
# 2) Cargar modelo y labels v1.1
#-------------------------------
print(f"Cargando modelo v1.1 desde: {MODEL_PATH}")
pipe = load(MODEL_PATH)

print(f"Cargando etiquetas v1.1 desde: {LABELS_PATH}")
with open(LABELS_PATH, encoding="utf-8") as f:
    labels_info = json.load(f)
labels = labels_info["labels"]
labels_arr = np.array(labels)

print("Etiquetas usadas por el modelo v1.1:", labels)

#------------------------
# 3) Inferencia sobre L2
#------------------------
# El pipeline v1.1 se entrenó con columnas texto/canal/prioridad,
# pero sólo usa 'texto'. Por seguridad le pasamos las tres si existen.
cols_X = ["texto"]
for extra_col in ("canal", "prioridad"):
    if extra_col in df.columns:
        cols_X.append(extra_col)

X_L2 = df[cols_X]

print("Lanzando predicciones sobre L2...")
y_pred_idx = pipe.predict(X_L2)  # índices 0..n_clases-1
df["pred_cat"] = labels_arr[y_pred_idx]

# Flag de acierto
df["ok"] = (df["real_cat"] == df["pred_cat"]).astype(int)

print("Primeras predicciones en L2:")
print(df[["id_ticket", "real_cat", "pred_cat", "ok"]].head(10))

#-----------------------------------
# 4) Métricas: classification_report
#-----------------------------------
report = classification_report(
    df["real_cat"],
    df["pred_cat"],
    labels=labels,
    digits=3,
    zero_division=0,
)

report_path = OUT_DIR / "L2_report_v1_1.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nReporte guardado en: {report_path}\n")
print(report)

#----------------------
# 5) Matriz normalizada
#----------------------
cm = confusion_matrix(
    df["real_cat"],
    df["pred_cat"],
    labels=labels,
)

cm_sum = cm.sum(axis=1, keepdims=True)
cm_norm = np.divide(cm, cm_sum, where=cm_sum != 0)

fig = plt.figure(figsize=(8, 6))
plt.imshow(cm_norm, interpolation="nearest")
plt.title("Matriz de confusión — L2 vs SVM v1.1 (normalizada)")
plt.xlabel("Predicha")
plt.ylabel("Real")
plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
plt.yticks(range(len(labels)), labels)
plt.colorbar()
plt.tight_layout()

cm_path = OUT_DIR / "L2_confusion_v1_1.png"
fig.savefig(cm_path, dpi=160)
plt.close(fig)

print(f"Matriz de confusión guardada en: {cm_path}")

#----------------------------------
# 6) CSV de predicciones por ticket
#----------------------------------
pred_path = OUT_DIR / "L2_predicciones_v1_1.csv"
df[["id_ticket", "real_cat", "pred_cat", "ok"]].to_csv(
    pred_path, sep=";", index=False, encoding="utf-8"
)

print(f"CSV de predicciones guardado en: {pred_path}")
print("\n Lote L2 procesado correctamente con el modelo v1.1.")