from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import load
from sklearn.metrics import classification_report, confusion_matrix

#------------------------
# Rutas base del proyecto
#------------------------
ROOT = Path(__file__).resolve().parents[2]

# CSV catalogado manual
L4_PATH = ROOT / "data" / "lotes" / "L4_manual_cat.csv"

# Carpeta del experimento E1 donde está el SVM ganador
RUN_E1 = ROOT / "resultados" / "modelos_produccion" / "SVM_v1_1_L1"

MODEL_PATH = RUN_E1 / "model.joblib"
LABELS_PATH = RUN_E1 / "labels.json"

# Carpeta de salida para este lote
OUT_DIR = ROOT / "resultados" / "lotes" / "L4_SVM_v1_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

#------------------------
# 1) Cargar datos de L4
#------------------------
print(f"Leyendo CSV de L4 desde: {L4_PATH}")
df = pd.read_csv(L4_PATH, sep=";", encoding="utf-8")

# Asegurar nombres
if "resumen" not in df.columns or "descripcion" not in df.columns:
    raise ValueError("No encuentro columnas 'resumen' y 'descripcion' en L4_manual_cat.csv")

if "categoria" not in df.columns:
    raise ValueError("No encuentro columna 'categoria' (etiqueta real) en L4_manual_cat.csv")

# Construir columna de texto como en TRAIN/VALID (con resumen + descripcion)
df["texto"] = (
    df["resumen"].fillna("").astype(str)
    + " "
    + df["descripcion"].fillna("").astype(str)
).str.strip()

# Etiquetado real (corregido por mi)
df["real_cat"] = df["categoria"].astype(str).str.strip()

print("Ejemplo de texto y etiqueta real:")
print(df[["id_ticket", "real_cat", "texto"]].head(3))

#-----------------------------
# 2) Carga modelo y etiquetas
#-----------------------------
print(f"Cargando modelo desde: {MODEL_PATH}")
pipe = load(MODEL_PATH)

print(f"Cargando etiquetas desde: {LABELS_PATH}")
with open(LABELS_PATH, encoding="utf-8") as f:
    labels_info = json.load(f)
labels = labels_info["labels"]
labels_arr = np.array(labels)

print("Etiquetas usadas por el modelo:", labels)

#-----------------------
# 3) Inferencia sobre L4
#-----------------------
# El pipeline E1 fue entrenado con un dataframe que tenía una columna llamada 'texto', se la paso
X_L4 = df[["texto"]]

print("Lanzando predicciones...")
y_pred_idx = pipe.predict(X_L4)  # devuelve índices

# Mapear índices a etiquetas de texto usando labels_arr
df["pred_cat"] = labels_arr[y_pred_idx]

# Flag de acierto
df["ok"] = (df["real_cat"] == df["pred_cat"]).astype(int)

print("Primeras predicciones:")
print(df[["id_ticket", "real_cat", "pred_cat", "ok"]].head(10))

#------------------------------------
# 4) Métricas: classification_report
#------------------------------------
report = classification_report(
    df["real_cat"],
    df["pred_cat"],
    labels=labels,
    digits=3,
    zero_division=0
)

report_path = OUT_DIR / "L4_report_v1_1.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nReporte guardado en: {report_path}\n")
print(report)

#-----------------------------------
# 5) Matriz de confusión normalizada
#-----------------------------------
cm = confusion_matrix(
    df["real_cat"],
    df["pred_cat"],
    labels=labels
)

# Normalizar por filas (cada fila suma 1)
cm_sum = cm.sum(axis=1, keepdims=True)
cm_norm = np.divide(cm, cm_sum, where=cm_sum != 0)

fig = plt.figure(figsize=(8, 6))
plt.imshow(cm_norm, interpolation="nearest")
plt.title("Matriz de confusión — L4 vs SVM E1 (normalizada)")
plt.xlabel("Predicha")
plt.ylabel("Real")
plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
plt.yticks(range(len(labels)), labels)
plt.colorbar()
plt.tight_layout()

cm_path = OUT_DIR / "L4_confusion_v1_1.png"
fig.savefig(cm_path, dpi=160)
plt.close(fig)

print(f"Matriz guardada en: {cm_path}")

#----------------------------------
# 6) CSV de predicciones por ticket
#----------------------------------
pred_path = OUT_DIR / "L4_predicciones_v1_0.csv"
df[["id_ticket", "real_cat", "pred_cat", "ok"]].to_csv(
    pred_path, sep=";", index=False, encoding="utf-8"
)

print(f"CSV de predicciones guardado en: {pred_path}")
print("\nLote L4 procesado correctamente.")
