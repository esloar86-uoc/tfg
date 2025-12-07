from pathlib import Path
import pandas as pd

#------------------------
# Rutas base del proyecto
#------------------------
ROOT = Path(__file__).resolve().parents[2]

# CSV manual (verdad terreno) y predicciones de L1
L1_MANUAL = ROOT / "data" / "lotes" / "L1_manual_cat.csv"
L1_PRED   = ROOT / "resultados" / "lotes" / "L1_SVM_v1" / "L1_predicciones_v1_0.csv"

# Salida
OUT_CSV = ROOT / "data" / "lotes" / "L1_errores_NET_SRV_POL.csv"

#-----------------
# 1) Cargar datos
#-----------------
print(f"Leyendo L1_manual_cat desde: {L1_MANUAL}")
df_manual = pd.read_csv(L1_MANUAL, sep=";", encoding="utf-8")

print(f"Leyendo predicciones L1 desde: {L1_PRED}")
df_pred = pd.read_csv(L1_PRED, sep=";", encoding="utf-8")

# nombres
if "id_ticket" not in df_manual.columns or "categoria" not in df_manual.columns:
    raise ValueError("L1_manual_cat.csv debe tener columnas 'id_ticket' y 'categoria'.")

if not {"id_ticket", "real_cat", "pred_cat", "ok"}.issubset(df_pred.columns):
    raise ValueError("L1_predicciones_v1_0.csv debe tener columnas id_ticket, real_cat, pred_cat, ok.")

#---------------------------------------
# 2) Unir verdad + predicciones
#---------------------------------------
df = df_pred.merge(
    df_manual,
    on="id_ticket",
    how="left",
    suffixes=("", "_manual")
)

# Comprobar coherencia de etiquetas
df["real_cat_manual"] = df["categoria"].astype(str).str.strip()
df["real_cat_predfile"] = df["real_cat"].astype(str).str.strip()

# Siempre la manual como real
df["real_cat"] = df["real_cat_manual"]

#----------------------------------
# 3) Filtrar errores en NET/SRV/POL
#----------------------------------
CLASES_DEBILES = ["NET", "SRV", "POL"]

mask_error = (df["ok"] == 0) & (df["real_cat"].isin(CLASES_DEBILES))
df_err = df[mask_error].copy()

print(f"Total de errores en NET/SRV/POL: {len(df_err)}")

# Texto como en el entrenamiento (resumen + descripcion)
df_err["texto"] = (
    df_err["resumen"].fillna("").astype(str)
    + " "
    + df_err["descripcion"].fillna("").astype(str)
).str.strip()

# Sólo columnas para reentrenar
df_out = df_err[[
    "id_ticket",
    "real_cat",
    "pred_cat", # lo que dijo el modelo v1.0
    "resumen",
    "descripcion",
    "texto",
]]

# Guardar
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df_out.to_csv(OUT_CSV, sep=";", index=False, encoding="utf-8")

print(f"CSV de errores guardado en: {OUT_CSV}")
print(df_out.head())