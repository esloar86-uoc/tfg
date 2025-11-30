from pathlib import Path
import json

import numpy as np
import pandas as pd
from joblib import dump

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC

#--------------------
# Rutas y constantes
#--------------------
ROOT = Path(__file__).resolve().parents[2]

TRAIN_CSV = ROOT / "data" / "ml" / "train.csv"
VALID_CSV = ROOT / "data" / "ml" / "valid.csv"
L1_ERRORS = ROOT / "data" / "lotes" / "L1_errores_NET_SRV_POL.csv"

MODEL_DIR = ROOT / "resultados" / "modelos_produccion" / "SVM_v1_1_L1"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

#------------
# Utilidades
#------------
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres esperados y valida presencia de id_ticket, texto, real_cat, canal, prioridad
    (canal/prioridad pueden venir como id_canal/id_prioridad y se renombran)
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    ren = {}
    if "id_canal" in df.columns and "canal" not in df.columns:
        ren["id_canal"] = "canal"
    if "id_prioridad" in df.columns and "prioridad" not in df.columns:
        ren["id_prioridad"] = "prioridad"
    if "categoria" in df.columns and "real_cat" not in df.columns:
        ren["categoria"] = "real_cat"
    df.rename(columns=ren, inplace=True)

    required = ["id_ticket", "texto", "real_cat", "canal", "prioridad"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas requeridas {missing}. Columnas presentes: {list(df.columns)}"
        )

    df["texto"] = df["texto"].astype(str)
    df["real_cat"] = df["real_cat"].astype(str)
    df["canal"] = df["canal"].astype(str)
    df["prioridad"] = df["prioridad"].astype(str)

    return df[required]


def read_any_csv(path: Path) -> pd.DataFrame:
    """
    Lee un CSV exportado desde MySQL Workbench detectando separador/encoding.
    Misma lógica que 06_experimentos_baselines.py.
    """
    tried = []
    for enc in ("utf-8-sig", "utf-8"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc)
                if df.shape[1] == 1:
                    tried.append((enc, sep, "1col"))
                    continue
                return df
            except Exception as e:
                tried.append((enc, sep, str(e)))
                continue

    # Último intento: autodetección de separador
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    return df


def read_ml_csv(path: Path) -> pd.DataFrame:
    """
    Envuelve read_any_csv y normaliza nombres de columnas
    """
    df = read_any_csv(path)
    return normalize_columns(df)


def make_preprocessor():
    text_feat = "texto"

    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        strip_accents="unicode",
        lowercase=True,
    )

    pre = ColumnTransformer(
        transformers=[("tfidf", tfidf, text_feat)],
        remainder="drop",
        sparse_threshold=1.0,
    )
    return pre


#-------------------------
# 1) Cargar train y valid
#-------------------------
print(f"Leyendo TRAIN desde: {TRAIN_CSV}")
train = read_ml_csv(TRAIN_CSV)

print(f"Leyendo VALID desde: {VALID_CSV}")
valid = read_ml_csv(VALID_CSV)

print(f"Tamaño train original: {len(train)}")
print(f"Tamaño valid: {len(valid)}")

#------------------------
# 2) Cargar errores de L1
#------------------------
print(f"Leyendo errores de L1 desde: {L1_ERRORS}")
err = pd.read_csv(L1_ERRORS, sep=";", encoding="utf-8")

# DF con las mismas columnas que train
extra = pd.DataFrame(
    {
        "id_ticket": err["id_ticket"].astype(str),
        "texto": err["texto"].astype(str),
        "real_cat": err["real_cat"].astype(str),
        # Se rellena canal/prioridad con valores genéricos; el modelo v1.1 sólo usa texto
        "canal": "lote_L1",
        "prioridad": "lote_L1",
    }
)

print(f"Número de ejemplos extra de L1: {len(extra)}")

#------------------------------
# 3) Unir train + errores de L1
#------------------------------
train_aug = pd.concat([train, extra], ignore_index=True)
print(f"Tamaño train aumentado: {len(train_aug)}")

#-----------------------
# 4) Codificar etiquetas
#-----------------------
le = LabelEncoder()
y_train = le.fit_transform(train_aug["real_cat"])
y_valid = le.transform(valid["real_cat"])

labels = list(le.classes_)
print("Etiquetas del modelo v1.1:", labels)

#-------------------------------------------
# 5) Definir y entrenar el pipeline SVM v1.1
#-------------------------------------------
pre = make_preprocessor()
clf = LinearSVC(C=1.0, random_state=RANDOM_STATE)

pipe = Pipeline(steps=[("pre", pre), ("clf", clf)])

X_train = train_aug[["texto", "canal", "prioridad"]]
X_valid = valid[["texto", "canal", "prioridad"]]

print("Entrenando modelo SVM v1.1...")
pipe.fit(X_train, y_train)

#---------------------
# 6) Evaluar en VALID
#---------------------
y_valid_pred = pipe.predict(X_valid)

f1_macro = f1_score(y_valid, y_valid_pred, average="macro")
report = classification_report(
    y_valid,
    y_valid_pred,
    target_names=labels,
    digits=3,
    zero_division=0,
)
cm = confusion_matrix(y_valid, y_valid_pred)

print("\nF1-macro en VALID (v1.1):", round(f1_macro, 3))
print("\nReporte clasificación (VALID):\n")
print(report)

#------------------------------
# 7) Guardar modelo y métricas
#------------------------------
print(f"\nGuardando modelo v1.1 en: {MODEL_DIR}")
dump(pipe, MODEL_DIR / "model.joblib")

with open(MODEL_DIR / "labels.json", "w", encoding="utf-8") as f:
    json.dump({"labels": labels}, f, ensure_ascii=False, indent=2)

with open(MODEL_DIR / "classification_report_valid.txt", "w", encoding="utf-8") as f:
    f.write(report)

with open(MODEL_DIR / "metrics_valid.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "train_original_size": int(len(train)),
            "train_augmented_size": int(len(train_aug)),
            "extra_from_L1": int(len(extra)),
            "valid_size": int(len(valid)),
            "f1_macro_valid_v1_1": float(f1_macro),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

# Matriz de confusión normalizada para VALID
cm_sum = cm.sum(axis=1, keepdims=True)
cm_norm = np.divide(cm, cm_sum, where=cm_sum != 0)

import matplotlib.pyplot as plt

fig = plt.figure(figsize=(8, 6))
plt.imshow(cm_norm, interpolation="nearest")
plt.title("Matriz de confusión — SVM v1.1 (VALID)")
plt.xlabel("Predicha")
plt.ylabel("Real")
plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
plt.yticks(range(len(labels)), labels)
plt.colorbar()
plt.tight_layout()
(fig := fig).savefig(MODEL_DIR / "confusion_valid.png", dpi=160)
plt.close(fig)

print("\nEntrenamiento de SVM v1.1 completado.")