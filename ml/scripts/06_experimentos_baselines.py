#------------------------------
# 06_experimentos_baselines.py
#------------------------------
import json, os, sys, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import dump

from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
import matplotlib.pyplot as plt

# Suprimir avisos "deprecated"
warnings.filterwarnings("ignore", category=FutureWarning)

#----------------
# Configuración
#----------------
RANDOM_STATE = 42
N_JOBS = -1
CV_FOLDS = 5

ROOT = Path(__file__).resolve().parents[2]                   # .../GIT
DATA_ML = ROOT / "data" / "ml"
RESULTS_ROOT = ROOT / "Resultados" / "experimentos"          # <- Respeta tu carpeta
RUN_DIR = RESULTS_ROOT / time.strftime("%Y%m%d_%H%M%S_baselines")
RUN_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_CSV = DATA_ML / "train.csv"
VALID_CSV = DATA_ML / "valid.csv"

#-----------
# Utilidades
#-----------
def read_any_csv(path: Path) -> pd.DataFrame:
    """
    Lee un CSV exportado desde MySQL Workbench detectando separador/encoding.
    Prueba UTF-8 con/sin BOM y ;/, y si falla, usa sep=None (engine='python').
    """
    tried = []
    for enc in ("utf-8-sig", "utf-8"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc)
                if df.shape[1] == 1:           # probablemente separador distinto
                    tried.append((enc, sep, "1col"))
                    continue
                return df
            except Exception as e:
                tried.append((enc, sep, str(e)))
                continue
    # último intento con autodetección
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres esperados y valida presencia:
    id_ticket, texto, real_cat, canal, prioridad
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
        raise ValueError(f"Faltan columnas requeridas {missing}. Columnas presentes: {list(df.columns)}")

    # tipos básicos
    df["texto"] = df["texto"].astype(str)
    df["real_cat"] = df["real_cat"].astype(str)
    df["canal"] = df["canal"].astype(str)
    df["prioridad"] = df["prioridad"].astype(str)
    return df[required]

#-------------
# Carga datos
#-------------
train = normalize_columns(read_any_csv(TRAIN_CSV))
valid = normalize_columns(read_any_csv(VALID_CSV))

# target
le = LabelEncoder()
y_train = le.fit_transform(train["real_cat"])
y_valid = le.transform(valid["real_cat"])
labels = list(le.classes_)
with open(RUN_DIR / "labels.json", "w", encoding="utf-8") as f:
    json.dump({"labels": labels}, f, ensure_ascii=False, indent=2)

#--------------------------
# Preprocesado + modelos
#--------------------------
def make_preprocessor(with_meta: bool):
    text_feat = "texto"
    cat_feats = ["canal", "prioridad"]

    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        strip_accents="unicode",
        lowercase=True,
    )

    if with_meta:
        pre = ColumnTransformer(
            transformers=[
                ("tfidf", tfidf, text_feat),
                ("oh", OneHotEncoder(handle_unknown="ignore"), cat_feats),
            ],
            remainder="drop",
            sparse_threshold=1.0,
        )
    else:
        pre = ColumnTransformer(
            transformers=[("tfidf", tfidf, text_feat)],
            remainder="drop",
            sparse_threshold=1.0,
        )
    return pre

MODELOS = {
    "nb": (
        MultinomialNB(),
        {"clf__alpha": [0.5, 1.0, 2.0]},
    ),
    "logreg": (
        # lbfgs soporta multiclase; sin n_jobs -> sin warnings
        LogisticRegression(max_iter=4000, solver="lbfgs", multi_class="auto"),
        {"clf__C": [0.5, 1.0, 2.0]},
    ),
    "svm": (
        LinearSVC(),
        {"clf__C": [0.5, 1.0, 2.0]},
    ),
}

def run_block(name, X_train, y_train, X_valid, y_valid, with_meta):
    pre = make_preprocessor(with_meta)
    resultados = {}

    for key, (est, grid) in MODELOS.items():
        pipe = Pipeline(steps=[("pre", pre), ("clf", est)])
        skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
        gscv = GridSearchCV(
            pipe,
            param_grid=grid,
            cv=skf,
            scoring="f1_macro",
            n_jobs=N_JOBS,
            verbose=0,
        )
        gscv.fit(X_train, y_train)

        best = gscv.best_estimator_
        y_pred = best.predict(X_valid)
        f1m = f1_score(y_valid, y_pred, average="macro")
        report = classification_report(
            y_valid, y_pred, target_names=labels, digits=4, zero_division=0
        )
        cm = confusion_matrix(y_valid, y_pred, labels=range(len(labels)))

        out_dir = RUN_DIR / f"{name}_{key}"
        out_dir.mkdir(exist_ok=True, parents=True)
        dump(best, out_dir / "model.joblib")

        pred_df = pd.DataFrame({
            "id_ticket": valid["id_ticket"].values,
            "y_true": le.inverse_transform(y_valid),
            "y_pred": le.inverse_transform(y_pred),
            "ok": (y_pred == y_valid).astype(int),
        })
        pred_df.to_csv(out_dir / "predicciones_valid.csv", index=False, sep=";", encoding="utf-8")

        with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump({
                "with_meta": with_meta,
                "best_params": gscv.best_params_,
                "cv_best_f1_macro": float(gscv.best_score_),
                "valid_f1_macro": float(f1m),
            }, f, ensure_ascii=False, indent=2)

        with open(out_dir / "classification_report.txt", "w", encoding="utf-8") as f:
            f.write(report)

        # Matriz de confusión normalizada por filas
        cm_sum = cm.sum(axis=1, keepdims=True)
        cm_norm = np.divide(cm, cm_sum, where=cm_sum != 0)
        fig = plt.figure(figsize=(8, 6))
        plt.imshow(cm_norm, interpolation="nearest")
        plt.title(f"Matriz de confusión — {name}/{key}")
        plt.xlabel("Predicha"); plt.ylabel("Real")
        plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
        plt.yticks(range(len(labels)), labels)
        plt.colorbar()
        plt.tight_layout()
        fig.savefig(out_dir / "confusion_matrix.png", dpi=160)
        plt.close(fig)

        resultados[key] = {
            "best_params": gscv.best_params_,
            "cv_best_f1_macro": float(gscv.best_score_),
            "valid_f1_macro": float(f1m),
            "pred_path": str(out_dir / "predicciones_valid.csv"),
            "report_path": str(out_dir / "classification_report.txt"),
            "cm_path": str(out_dir / "confusion_matrix.png"),
        }

    with open(RUN_DIR / f"{name}_summary.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

#-----------------
# Ejecutar E1 y E2
#-----------------
Xtr = train[["texto", "canal", "prioridad"]]
Xva = valid[["texto", "canal", "prioridad"]]

run_block("E1_texto", Xtr[["texto"]], y_train, Xva[["texto"]], y_valid, with_meta=False)
run_block("E2_texto_meta", Xtr, y_train, Xva, y_valid, with_meta=True)

print(f"Resultados en: {RUN_DIR}")