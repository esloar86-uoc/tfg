#------------------------------
# 07_experimentos_E2_meta.py
#------------------------------
"""
E2: Texto (TF-IDF) + metadatos (canal, prioridad) con one-hot
Modelos: MultinomialNB, LogisticRegression (lbfgs, multinomial), LinearSVC
Split: train/valid (los mismos CSV exportados en cap.5.2)
Métrica de selección: F1-macro (validación cruzada estratificada en Train)
Salida: resultados/experimentos/YYYYMMDD_HHMMSS_E2_meta/
"""

import json
import warnings
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

# Silenciar avisos
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*liblinear*.")
warnings.filterwarnings("ignore", message=".*'n_jobs' > 1 does not have any effect*")

# Rutas base
BASE = Path(__file__).resolve().parents[2]  # repo root (../.. desde scripts)
DATA = BASE / "data" / "ml"
TRAIN_CSV = DATA / "train.csv"
VALID_CSV = DATA / "valid.csv"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = BASE / "resultados" / "experimentos" / f"{STAMP}_E2_meta"
OUT.mkdir(parents=True, exist_ok=True)

# Lectura CSV 
def read_csv_robusto(path: Path) -> pd.DataFrame:
    """Intenta sep autodetectado; sin perder filas.
       Solo como ÚLTIMO recurso, on_bad_lines='skip' (avisando)."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    # 1) Autodetección de separador y lectura estricta
    try:
        df = pd.read_csv(
            path,
            sep=None,                # autodetecta separador
            engine="python",
            encoding="utf-8-sig",
            quotechar='"',
            escapechar="\\",
            on_bad_lines="error"     # no perder filas
        )
        # Si la autodetección fallara, df tendría 1 sola columna
        if df.shape[1] == 1:
            raise ValueError("Autodetección de separador fallida (1 columna).")
        return df
    except Exception:
        # 2) Reintento manual con ';' y luego con ','
        for sep in (";", ","):
            try:
                df = pd.read_csv(
                    path,
                    sep=sep,
                    engine="python",
                    encoding="utf-8-sig",
                    quotechar='"',
                    escapechar="\\",
                    on_bad_lines="error"
                )
                if df.shape[1] > 1:
                    return df
            except Exception:
                pass

        # 3) Último recurso: saltar líneas conflictivas
        df = pd.read_csv(
            path,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
            quotechar='"',
            escapechar="\\",
            on_bad_lines="skip"
        )
        print(f"[AVISO] Se han omitido filas problemáticas al leer {path.name}. "
              f"Filas finales: {len(df)}")
        return df

train = read_csv_robusto(TRAIN_CSV)
valid = read_csv_robusto(VALID_CSV)

# Columnas esperadas
expected = {"id_ticket","texto","real_cat","canal","prioridad"}
missing_train = expected - set(train.columns)
missing_valid = expected - set(valid.columns)
if missing_train:
    raise ValueError(f"TRAIN: faltan columnas {missing_train}. "
                     f"Columnas encontradas: {list(train.columns)}")
if missing_valid:
    raise ValueError(f"VALID: faltan columnas {missing_valid}. "
                     f"Columnas encontradas: {list(valid.columns)}")

# Types y nulos
for col in ["texto","canal","prioridad","real_cat"]:
    train[col] = train[col].astype(str).fillna("")
    valid[col] = valid[col].astype(str).fillna("")

X_train = train[["texto","canal","prioridad"]]
y_train = train["real_cat"].astype(str)
X_valid = valid[["texto","canal","prioridad"]]
y_valid = valid["real_cat"].astype(str)

#  Preproceso 
text_vec = TfidfVectorizer(
    ngram_range=(1,2),
    min_df=2,
    max_df=0.9,
    sublinear_tf=True,
    strip_accents="unicode"
)

# Compatibilidad sklearn 
try:
    cat_enc = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
except TypeError:
    cat_enc = OneHotEncoder(handle_unknown="ignore", sparse=True)

preprocess = ColumnTransformer(
    transformers=[
        ("text", text_vec, "texto"),
        ("cat",  cat_enc,  ["canal","prioridad"]),
    ],
    sparse_threshold=0.3,
    remainder="drop"
)

#  Modelos y grids 
models = {
    "nb": {
        "estimator": MultinomialNB(),
        "param_grid": {"clf__alpha": [0.5, 1.0, 2.0]}
    },
    "lr": {
        "estimator": LogisticRegression(
            solver="lbfgs",
            max_iter=500,
            multi_class="multinomial",
            n_jobs=None,
            random_state=42
        ),
        "param_grid": {"clf__C": [0.5, 1.0, 2.0]}
    },
    "svm": {
        "estimator": LinearSVC(C=1.0, random_state=42),
        "param_grid": {"clf__C": [0.5, 1.0, 2.0]}
    }
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

def run_model(key, est, grid):
    pipe = Pipeline(steps=[("prep", preprocess), ("clf", est)])
    gs = GridSearchCV(
        estimator=pipe,
        param_grid=grid,
        scoring="f1_macro",
        n_jobs=-1,
        cv=cv,
        refit=True,
        verbose=0
    )
    gs.fit(X_train, y_train)

    # Validación en Valid
    y_pred = gs.predict(X_valid)
    acc = accuracy_score(y_valid, y_pred)
    f1m = f1_score(y_valid, y_pred, average="macro")
    rep_txt = classification_report(y_valid, y_pred, zero_division=0)

    # Guardar artefactos
    subdir = OUT / f"E2_{key}"
    subdir.mkdir(exist_ok=True, parents=True)
    with open(subdir / "best_params.json", "w", encoding="utf-8") as f:
        json.dump(gs.best_params_, f, ensure_ascii=False, indent=2)
    with open(subdir / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(rep_txt)
        f.write(f"\n\naccuracy={acc:.4f}  f1_macro={f1m:.4f}\n")

    # Matriz de confusión normalizada por filas
    labels = sorted(y_valid.unique())
    cm = confusion_matrix(y_valid, y_pred, labels=labels, normalize="true")
    fig = plt.figure(figsize=(7,6))
    plt.imshow(cm, interpolation="nearest")
    plt.title(f"Matriz de confusión (E2 {key})")
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.colorbar()
    plt.xlabel("Predicho")
    plt.ylabel("Real")
    for i in range(len(labels)):
        for j in range(len(labels)):
            plt.text(j, i, f"{cm[i, j]:.2f}", va="center", ha="center")
    plt.tight_layout()
    fig.savefig(subdir / "confusion_matrix.png", dpi=140)
    plt.close(fig)

    return {
        "modelo": key,
        "best_params": gs.best_params_,
        "accuracy_valid": acc,
        "f1_macro_valid": f1m
    }

resumen = [run_model(k, spec["estimator"], spec["param_grid"]) for k, spec in models.items()]

# Guardar resumen
df_res = pd.DataFrame(resumen).sort_values("f1_macro_valid", ascending=False)
df_res.to_csv(OUT / "E2_resumen_modelos.csv", index=False, sep=";")
with open(OUT / "E2_resumen_modelos.txt", "w", encoding="utf-8") as f:
    f.write(df_res.to_string(index=False))

print("Filas TRAIN:", len(train), " | Filas VALID:", len(valid))
print("Resultados en:", OUT)