from pathlib import Path
import json

import numpy as np
import pandas as pd
from joblib import load
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt

#------------
# Rutas base
#------------
ROOT = Path(__file__).resolve().parents[2]

CSV_L4 = ROOT / "data" / "lotes" / "L4_manual_cat.csv"

# Modelo v1.1 (entrenado en 10_entrenar_svm_v1_1.py)
MODEL_DIR = ROOT / "resultados" / "modelos_produccion" / "SVM_v1_1_L1"
MODEL_PATH = MODEL_DIR / "model.joblib"
LABELS_PATH = MODEL_DIR / "labels.json"

OUT_DIR = ROOT / "resultados" / "lotes" / "L4_SVM_v1_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

#----------------------
# 1) Cargar datos de L4
#----------------------
print(f"Leyendo CSV de L4 desde: {CSV_L4}")
df = pd.read_csv(CSV_L4, sep=";", encoding="utf-8")

# Comprobaciones mínimas
for col in ("resumen", "descripcion", "categoria"):
    if col not in df.columns:
        raise ValueError(f"No se encuentra la columna '{col}' en L4_manual_cat.csv")

# Texto igual que en TRAIN/VALID
df["texto"] = (
    df["resumen"].fillna("").astype(str)
    + " "
    + df["descripcion"].fillna("").astype(str)
).str.strip()

# Etiqueta real (manual)
df["real_cat"] = df["categoria"].astype(str).str.strip()

print("Ejemplo de texto y etiqueta real en L4:")
print(df[["id_ticket", "real_cat", "texto"]].head(3))

#---------------------------------
# 2) Carga modelo y etiquetas v1.1
#---------------------------------
print(f"Cargando modelo v1.1 desde: {MODEL_PATH}")
pipe = load(MODEL_PATH)

print(f"Cargando etiquetas v1.1 desde: {LABELS_PATH}")
with open(LABELS_PATH, encoding="utf-8") as f:
    labels_info = json.load(f)
labels = labels_info["labels"]
labels_arr = np.array(labels)

print("Etiquetas usadas por el modelo v1.1:", labels)

#-----------------------
# 3) Inferencia sobre L4
#-----------------------
cols_X = ["texto"]
for extra_col in ("canal", "prioridad"):
    if extra_col in df.columns:
        cols_X.append(extra_col)

X_L3 = df[cols_X]

print("Lanzando predicciones sobre L4...")
y_pred_idx = pipe.predict(X_L3)
df["pred_cat"] = labels_arr[y_pred_idx]

# Flag de acierto
df["ok"] = (df["real_cat"] == df["pred_cat"]).astype(int)

print("Primeras predicciones en L4:")
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

report_path = OUT_DIR / "L4_report_v1_1.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nClassification report guardado en: {report_path}\n")
print(report)

#-----------------------------------
# 5) Matriz de confusión normalizada
#-----------------------------------
cm = confusion_matrix(
    df["real_cat"],
    df["pred_cat"],
    labels=labels,
)

cm_sum = cm.sum(axis=1, keepdims=True)
cm_norm = np.divide(cm, cm_sum, where=cm_sum != 0)

fig = plt.figure(figsize=(8, 6))
plt.imshow(cm_norm, interpolation="nearest")
plt.title("Matriz de confusión — L3 vs SVM v1.1 (normalizada)")
plt.xlabel("Predicha")
plt.ylabel("Real")
plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
plt.yticks(range(len(labels)), labels)
plt.colorbar()
plt.tight_layout()

cm_path = OUT_DIR / "L4_confusion_v1_1.png"
fig.savefig(cm_path, dpi=160)
plt.close(fig)

print(f"Matriz de confusión guardada en: {cm_path}")

#----------------------------------
# 6) CSV de predicciones por ticket
#----------------------------------
pred_path = OUT_DIR / "L4_predicciones_v1_1.csv"
df[["id_ticket", "real_cat", "pred_cat", "ok"]].to_csv(
    pred_path, sep=";", index=False, encoding="utf-8"
)

print(f"CSV de predicciones guardado en: {pred_path}")
print("\nLote L4 procesado con el modelo v1.1.")