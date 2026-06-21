import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
import shap
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    fbeta_score,
    precision_score,
    recall_score,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
    roc_auc_score,
)
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline


def calculate_ece(y_true, y_prob, n_bins=10):
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


print("1. Cargando datos y capturando Pipeline XGBoost optimizado...")

df = pd.read_csv("dataset.csv")

X = df.drop(columns=["provider_id", "disruption_risk"])
y = df["disruption_risk"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

variables_categoricas = ["supply_category", "logistics_mode"]
variables_numericas = [col for col in X.columns if col not in variables_categoricas]

prep_lr = ColumnTransformer(
    transformers=[
        (
            "cat",
            OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False),
            variables_categoricas,
        ),
        ("num", StandardScaler(), variables_numericas),
    ]
)

modelo_lr = Pipeline(
    [
        ("prep", prep_lr),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ]
)

print(" -> Entrenando Baseline (Regresión Logística)...")
modelo_lr.fit(X_train, y_train)

print(" -> Cargando XGBoost desde 'risk_pipeline.pkl' (No requiere fit)...")
modelo_xgb = joblib.load("risk_pipeline.pkl")


y_prob_lr = modelo_lr.predict_proba(X_test)[:, 1]
y_prob_xgb = modelo_xgb.predict_proba(X_test)[:, 1]

UMBRAL_OPTIMO = 0.335
y_pred_lr = (y_prob_lr >= UMBRAL_OPTIMO).astype(int)
y_pred_xgb = (y_prob_xgb >= UMBRAL_OPTIMO).astype(int)

print("\n=== ANÁLISIS DE RENDIMIENTO COMPARATIVO (Test Set) ===")

pr_auc_xgb = average_precision_score(y_test, y_prob_xgb)
roc_auc_xgb = roc_auc_score(y_test, y_prob_xgb)
precision_xgb = precision_score(y_test, y_pred_xgb, zero_division=0)
recall_xgb = recall_score(y_test, y_pred_xgb)
f2_score_xgb = fbeta_score(y_test, y_pred_xgb, beta=2)
ece_xgb = calculate_ece(y_test, y_prob_xgb)

pr_auc_lr = average_precision_score(y_test, y_prob_lr)
roc_auc_lr = roc_auc_score(y_test, y_prob_lr)
precision_lr = precision_score(y_test, y_pred_lr, zero_division=0)
recall_lr = recall_score(y_test, y_pred_lr)
f2_score_lr = fbeta_score(y_test, y_pred_lr, beta=2)
ece_lr = calculate_ece(y_test, y_prob_lr)

print(f"{'Métrica':<12} | {'XGBoost':<10} | {'LogReg (Base)':<15} | {'Interpretación'}")
print("-" * 85)
print(
    f"{'ROC-AUC':<12} | {roc_auc_xgb:<10.4f} | {roc_auc_lr:<15.4f} | Área bajo la curva ROC (Capacidad general)"
)
print(
    f"{'PR-AUC':<12} | {pr_auc_xgb:<10.4f} | {pr_auc_lr:<15.4f} | Área curva Precision-Recall (Específico minoritaria)"
)
print(
    f"{'F2-Score':<12} | {f2_score_xgb:<10.4f} | {f2_score_lr:<15.4f} | Balance penalizando FN (Mayor es mejor)"
)
print(
    f"{'Precision':<12} | {precision_xgb:<10.4f} | {precision_lr:<15.4f} | De las alertas, % que son reales"
)
print(
    f"{'Recall':<12} | {recall_xgb:<10.4f} | {recall_lr:<15.4f} | De los fallos reales, % detectados"
)
print(
    f"{'ECE':<12} | {ece_xgb:<10.4f} | {ece_lr:<15.4f} | Error de calibración (Menor es mejor)"
)

print("\nGenerando gráficos...")
plt.style.use("seaborn-v0_8-whitegrid")

plt.figure(figsize=(8, 6))
prec_vals_xgb, rec_vals_xgb, _ = precision_recall_curve(y_test, y_prob_xgb)
prec_vals_lr, rec_vals_lr, _ = precision_recall_curve(y_test, y_prob_lr)

plt.plot(
    rec_vals_xgb,
    prec_vals_xgb,
    color="#2980b9",
    lw=2,
    label=f"XGBoost (PR-AUC={pr_auc_xgb:.3f})",
)
plt.plot(
    rec_vals_lr,
    prec_vals_lr,
    color="#7f8c8d",
    lw=2,
    linestyle="--",
    label=f"LogReg (PR-AUC={pr_auc_lr:.3f})",
)
plt.plot(
    recall_xgb,
    precision_xgb,
    marker="o",
    markersize=8,
    color="#c0392b",
    label=f"Umbral XGB ({UMBRAL_OPTIMO})",
)

plt.title("Curva Precision-Recall Comparativa", fontsize=14)
plt.xlabel("Recall", fontsize=12)
plt.ylabel("Precision", fontsize=12)
plt.legend()
plt.tight_layout()
plt.savefig("grafico_01_curva_pr.png", dpi=300)
plt.close()

plt.figure(figsize=(8, 6))
fpr_xgb, tpr_xgb, _ = roc_curve(y_test, y_prob_xgb)
fpr_lr, tpr_lr, _ = roc_curve(y_test, y_prob_lr)

plt.plot(
    fpr_xgb,
    tpr_xgb,
    color="#2980b9",
    lw=2,
    label=f"XGBoost (ROC-AUC={roc_auc_xgb:.3f})",
)
plt.plot(
    fpr_lr,
    tpr_lr,
    color="#7f8c8d",
    lw=2,
    linestyle="--",
    label=f"LogReg (ROC-AUC={roc_auc_lr:.3f})",
)
plt.plot([0, 1], [0, 1], color="black", linestyle=":", label="Modelo Aleatorio")

plt.title("Curva ROC Comparativa", fontsize=14)
plt.xlabel("Tasa de Falsos Positivos (FPR)", fontsize=12)
plt.ylabel("Tasa de Verdaderos Positivos (TPR)", fontsize=12)
plt.legend()
plt.tight_layout()
plt.savefig("grafico_02_curva_roc.png", dpi=300)
plt.close()

plt.figure(figsize=(6, 5))
cm_xgb = confusion_matrix(y_test, y_pred_xgb)
sns.heatmap(
    cm_xgb,
    annot=True,
    fmt="d",
    cmap="Blues",
    cbar=False,
    annot_kws={"size": 14},
)
plt.title(
    f"Matriz de Confusión XGBoost\n(Umbral Operativo: {UMBRAL_OPTIMO})", fontsize=14
)
plt.xlabel("Predicción del Modelo", fontsize=12)
plt.ylabel("Realidad Histórica", fontsize=12)
plt.xticks([0.5, 1.5], ["0: Seguro", "1: Riesgo"])
plt.yticks([0.5, 1.5], ["0: Seguro", "1: Riesgo"])
plt.tight_layout()
plt.savefig("grafico_03_matriz_confusion.png", dpi=300)
plt.close()

plt.figure(figsize=(8, 6))
prob_true_xgb, prob_pred_xgb = calibration_curve(y_test, y_prob_xgb, n_bins=10)
prob_true_lr, prob_pred_lr = calibration_curve(y_test, y_prob_lr, n_bins=10)

plt.plot(
    prob_pred_xgb,
    prob_true_xgb,
    marker="o",
    color="#27ae60",
    label=f"XGBoost (ECE={ece_xgb:.3f})",
)
plt.plot(
    prob_pred_lr,
    prob_true_lr,
    marker="s",
    color="#7f8c8d",
    linestyle="--",
    label=f"LogReg (ECE={ece_lr:.3f})",
)
plt.plot([0, 1], [0, 1], "k:", label="Calibración Perfecta")

plt.title("Gráfico de Calibración de Probabilidades", fontsize=14)
plt.xlabel("Probabilidad Predicha Media", fontsize=12)
plt.ylabel("Fracción de Casos Reales", fontsize=12)
plt.legend()
plt.tight_layout()
plt.savefig("grafico_04_calibracion.png", dpi=300)
plt.close()

plt.figure(figsize=(9, 6))

prob_seguro = y_prob_xgb[y_test == 0]
prob_riesgo = y_prob_xgb[y_test == 1]

sns.kdeplot(
    prob_seguro,
    color="#27ae60",
    fill=True,
    alpha=0.5,
    linewidth=2,
    label="0: Seguro (Realidad)",
)
sns.kdeplot(
    prob_riesgo,
    color="#c0392b",
    fill=True,
    alpha=0.5,
    linewidth=2,
    label="1: Interrupción (Realidad)",
)

plt.axvline(
    x=UMBRAL_OPTIMO,
    color="black",
    linestyle="--",
    lw=2.5,
    label=f"Umbral Operativo XGB ({UMBRAL_OPTIMO})",
)

plt.axvspan(UMBRAL_OPTIMO, 1, ymax=0.3, color="#27ae60", alpha=0.1)
plt.axvspan(0, UMBRAL_OPTIMO, ymax=0.3, color="#c0392b", alpha=0.1)

plt.title(
    "Distribución de Probabilidades Predichas vs. Realidad",
    fontsize=14,
    fontweight="bold",
)
plt.xlabel("Probabilidad Predicha por XGBoost", fontsize=12)
plt.ylabel("Densidad", fontsize=12)
plt.legend(loc="upper right")
plt.tight_layout()
plt.savefig("grafico_05_distribucion_kde.png", dpi=300)
plt.close()

print(" -> Generando SHAP Summary Plot para XGBoost...")

estimador_xgb = modelo_xgb.named_steps["xgb"]
preprocesador_xgb = modelo_xgb.named_steps["prep"]

X_test_preprocesado = preprocesador_xgb.transform(X_test)
nombres_features = preprocesador_xgb.get_feature_names_out()

explainer = shap.TreeExplainer(estimador_xgb)
shap_values = explainer(X_test_preprocesado)

plt.figure(figsize=(10, 6))
shap.summary_plot(
    shap_values,
    X_test_preprocesado,
    feature_names=nombres_features,
    show=False,
    plot_size=(10, 6),
)
plt.title("Impacto de las Variables en el Riesgo (Valores SHAP)", fontsize=14)
plt.tight_layout()
plt.savefig("grafico_06_shap_summary.png", dpi=300)
plt.close()

print("\n¡Evaluación completada! Gráficos 01 al 06 generados con éxito.")
