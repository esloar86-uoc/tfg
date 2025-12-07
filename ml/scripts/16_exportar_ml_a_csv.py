from pathlib import Path
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[2]

# 1) De dónde sale cada CSV de predicciones
EXPERIMENTOS = [
    # E1 – baselines sobre VALID
    dict(
        id_experimento=1,
        experimento="E1",
        dataset="VALID",
        modelo_version="E1_NB",
        csv_pred=ROOT
        / "resultados"
        / "experimentos"
        / "20251111_130612_baselines"
        / "E1_texto_nb"
        / "predicciones_valid.csv",
    ),
    dict(
        id_experimento=1,
        experimento="E1",
        dataset="VALID",
        modelo_version="E1_RL",
        csv_pred=ROOT
        / "resultados"
        / "experimentos"
        / "20251111_130612_baselines"
        / "E1_texto_logreg"
        / "predicciones_valid.csv",
    ),
    dict(
        id_experimento=1,
        experimento="E1",
        dataset="VALID",
        modelo_version="E1_SVM",
        csv_pred=ROOT
        / "resultados"
        / "experimentos"
        / "20251111_130612_baselines"
        / "E1_texto_svm"
        / "predicciones_valid.csv",
    ),
    # L4 – evaluación manual (producción)
    dict(
        id_experimento=3,
        experimento="L4",
        dataset="L4_manual",
        modelo_version="SVM_v1.1",
        csv_pred=ROOT
        / "resultados"
        / "lotes"
        / "L4_SVM_v1_1"
        / "L4_predicciones_v1_1.csv",
    ),
]

# Orden coherente de etiquetas
LABELS = ["ACC", "APP", "HW", "MAIL", "NET", "POL", "SRV", "SW"]

rows_global = []
rows_clase = []
rows_cm = []

for cfg in EXPERIMENTOS:
    print(f"Leyendo CSV de predicciones: {cfg['csv_pred']}")
    df = pd.read_csv(cfg["csv_pred"], sep=";", encoding="utf-8")

    # Detectar columnas de etiqueta real/predicha
    posibles_reales = ["real_cat", "categoria", "y_true", "label", "real"]
    posibles_pred = ["pred_cat", "prediccion", "y_pred", "label_pred", "pred"]

    col_real = next((c for c in posibles_reales if c in df.columns), None)
    col_pred = next((c for c in posibles_pred if c in df.columns), None)

    if col_real is None or col_pred is None:
        raise ValueError(
            f"No encontradas columnas de etiqueta real/predicha en {cfg['csv_pred']}. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    y_true = df[col_real]
    y_pred = df[col_pred]

    report = classification_report(
        y_true,
        y_pred,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )

    n_muestras = len(df)

    # Tabla global
    rows_global.append(
        {
            "experimento": cfg["experimento"],
            "id_experimento": cfg["id_experimento"],
            "modelo_version": cfg["modelo_version"],
            "dataset": cfg["dataset"],
            "accuracy_pct": round(report["accuracy"] * 100, 2),
            "f1_macro_pct": round(report["macro avg"]["f1-score"] * 100, 2),
            "f1_weighted_pct": round(report["weighted avg"]["f1-score"] * 100, 2),
            "precision_macro_pct": round(report["macro avg"]["precision"] * 100, 2),
            "recall_macro_pct": round(report["macro avg"]["recall"] * 100, 2),
            "n_muestras": n_muestras,
        }
    )

    # Tabla por clase
    for label in LABELS:
        m = report[label]
        rows_clase.append(
            {
                "experimento": cfg["experimento"],
                "id_experimento": cfg["id_experimento"],
                "modelo_version": cfg["modelo_version"],
                "dataset": cfg["dataset"],
                "real_cat": label,
                "precision_pct": round(m["precision"] * 100, 2),
                "recall_pct": round(m["recall"] * 100, 2),
                "f1_pct": round(m["f1-score"] * 100, 2),
                "soporte_n": int(m["support"]),
            }
        )

    # Matriz de confusión
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    for i, real in enumerate(LABELS):
        for j, pred in enumerate(LABELS):
            n = int(cm[i, j])
            rows_cm.append(
                {
                    "experimento": cfg["experimento"],
                    "id_experimento": cfg["id_experimento"],
                    "modelo_version": cfg["modelo_version"],
                    "dataset": cfg["dataset"],
                    "real_cat": real,
                    "pred_cat": pred,
                    "n": n,
                }
            )

OUT_DIR = ROOT / "resultados" / "ml_resumen"
OUT_DIR.mkdir(parents=True, exist_ok=True)

pd.DataFrame(rows_global).to_csv(OUT_DIR / "ml_resultado_global.csv", index=False)
pd.DataFrame(rows_clase).to_csv(OUT_DIR / "ml_resultado_por_clase.csv", index=False)
pd.DataFrame(rows_cm).to_csv(OUT_DIR / "ml_confusion.csv", index=False)

print("CSV generados en:", OUT_DIR)