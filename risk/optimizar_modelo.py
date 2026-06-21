import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import (
    StratifiedKFold,
    RandomizedSearchCV,
    cross_val_predict,
    train_test_split,
)
from sklearn.metrics import confusion_matrix
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt

print("=== OPTIMIZADOR AVANZADO XGBOOST: ORIENTADO A COSTES (SIN DATA LEAKAGE) ===")


def calculate_ece(y_true, y_prob, n_bins=10):
    """Calcula el Expected Calibration Error (ECE)"""
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins)
    bins = np.linspace(0.0, 1.0 + 1e-8, n_bins + 1)
    binids = np.digitize(y_prob, bins) - 1
    bin_total = np.bincount(binids, minlength=len(bins))
    nonzero = bin_total != 0
    bin_preds = (
        np.bincount(binids, weights=y_prob, minlength=len(bins))[nonzero]
        / bin_total[nonzero]
    )
    bin_true = (
        np.bincount(binids, weights=y_true, minlength=len(bins))[nonzero]
        / bin_total[nonzero]
    )
    bin_weights = bin_total[nonzero] / len(y_true)
    return np.sum(bin_weights * np.abs(bin_true - bin_preds))


df = pd.read_csv("dataset.csv")
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
import joblib

X = df.drop(columns=["provider_id", "disruption_risk"])
y = df["disruption_risk"]

variables_categoricas = ["supply_category", "logistics_mode"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

preprocesador = ColumnTransformer(
    transformers=[
        (
            "cat",
            OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False),
            variables_categoricas,
        )
    ],
    remainder="passthrough",
)

pipeline = Pipeline(
    [
        ("prep", preprocesador),
        ("xgb", xgb.XGBClassifier(objective="binary:logistic", random_state=42)),
    ]
)

ratio_desbalanceo = (len(y_train) - sum(y_train)) / sum(y_train)
espacio_parametros = {
    "xgb__max_depth": [3, 4, 5, 6],
    "xgb__learning_rate": [0.01, 0.05, 0.1, 0.2],
    "xgb__n_estimators": [100, 200, 300],
    "xgb__subsample": [0.7, 0.8, 0.9, 1.0],
    "xgb__colsample_bytree": [0.7, 0.8, 0.9, 1.0],
    "xgb__scale_pos_weight": [1],
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
busqueda_aleatoria = RandomizedSearchCV(
    estimator=pipeline,
    param_distributions=espacio_parametros,
    n_iter=20,
    scoring="average_precision",
    cv=cv,
    verbose=1,
    random_state=42,
    n_jobs=-1,
    refit=True,
)

busqueda_aleatoria.fit(X_train, y_train)
mejor_modelo = busqueda_aleatoria.best_estimator_

joblib.dump(mejor_modelo, "risk_pipeline.pkl")
print("Mejores Hiperparámetros encontrados en Train:")
for param, valor in busqueda_aleatoria.best_params_.items():
    print(f" - {param}: {valor}")
