import pandas as pd
import numpy as np
from scipy.stats import truncnorm, beta, gamma, expon

print("=== GENERADOR DE DATOS: ARQUETIPOS DE PROVEEDOR (V6) ===")

np.random.seed(42)
n_registros = 10000

proveedores_ids = [
    "MS_001",
    "MS_002",
    "MS_003",
    "MS_004",
    "MS_005",
    "MS_006",
    "CS_001",
    "CS_002",
    "CS_003",
    "CS_005",
]

ids_generados = np.random.choice(proveedores_ids, n_registros)

mask_peligrosos = np.isin(ids_generados, ["MS_003", "CS_002"])
mask_excelentes = np.isin(ids_generados, ["CS_001", "MS_004", "MS_006"])

oee_base = beta.rvs(a=8, b=2, size=n_registros)
sat_base = beta.rvs(a=7, b=3, size=n_registros) * 100
defectos_base = truncnorm.rvs(
    (0 - 5) / 3, (20 - 5) / 3, loc=5, scale=3, size=n_registros
)
auditoria_base = np.clip(np.random.normal(75, 15, size=n_registros), 0, 100)

eficiencia_oee = np.where(
    mask_peligrosos,
    oee_base * 0.80,
    np.where(mask_excelentes, np.clip(oee_base * 1.15, 0, 1), oee_base),
)

saturacion_capacidad = np.where(
    mask_peligrosos,
    np.clip(sat_base + 15, 0, 100),
    np.where(mask_excelentes, np.clip(sat_base - 10, 0, 100), sat_base),
)

ratio_defectos_calidad = np.where(
    mask_peligrosos,
    defectos_base * 1.5,
    np.where(mask_excelentes, defectos_base * 0.5, defectos_base),
)

score_compliance_auditoria = np.where(
    mask_peligrosos,
    np.clip(auditoria_base - 15, 0, 100),
    np.where(mask_excelentes, np.clip(auditoria_base + 10, 0, 100), auditoria_base),
)

riesgo_climatico = np.clip(expon.rvs(scale=0.2, size=n_registros), 0, 1)
antiguedad_activos = np.random.uniform(1, 20, size=n_registros)
rotacion_personal = truncnorm.rvs(
    (0 - 10) / 15, (40 - 10) / 15, loc=10, scale=15, size=n_registros
)
lead_time_promedio = gamma.rvs(a=5, scale=1.2, size=n_registros)

datos = {
    "provider_id": ids_generados,
    "supply_category": np.random.choice(
        ["Componentes Críticos", "Materia Prima", "Embalaje Industrial"], n_registros
    ),
    "logistics_mode": np.random.choice(
        ["Marítimo", "Terrestre-OTM", "Aéreo-Express"], n_registros
    ),
    "climate_risk_index": np.round(riesgo_climatico, 2),
    "machinery_oee_efficiency": np.round(eficiencia_oee, 2),
    "asset_age_years": np.round(antiguedad_activos, 1),
    "capacity_saturation_level_pct": np.round(saturacion_capacidad, 1),
    "staff_turnover_rate_pct": np.round(rotacion_personal, 1),
    "audit_compliance_score": np.round(score_compliance_auditoria, 1),
    "average_lead_time_days": np.round(lead_time_promedio, 1),
    "quality_defect_ratio_pct": np.round(ratio_defectos_calidad, 2),
    "days_since_last_maintenance": np.random.randint(0, 365, n_registros),
}

df = pd.DataFrame(datos)


factor_gestion = np.random.normal(0, 15, n_registros)
mantenimiento_chapuza = np.where(
    (df["days_since_last_maintenance"] < 30) & (np.random.rand(n_registros) < 0.10),
    35,
    0,
)

score_total = (
    np.where(
        df["capacity_saturation_level_pct"] > 85,
        (df["capacity_saturation_level_pct"] - 85) * 3,
        0,
    )
    + (df["staff_turnover_rate_pct"] * 0.8)
    + ((1 - df["machinery_oee_efficiency"]) * 35)
    + (df["asset_age_years"] * 1.2)
    + ((100 - df["audit_compliance_score"]) * 0.4)
    + (df["climate_risk_index"] * 25)
    + np.where(df["supply_category"] == "Componentes Críticos", 15, 0)
    + np.where(df["logistics_mode"] == "Marítimo", 10, 0)
    + factor_gestion
    + mantenimiento_chapuza
    + np.random.normal(0, 12, n_registros)
)

umbral = np.percentile(score_total, 75)
riesgo_base = np.where(score_total >= umbral, 1, 0)

df["disruption_risk"] = np.where(
    np.random.rand(n_registros) < 0.05, 1 - riesgo_base, riesgo_base
)

df.to_csv("dataset.csv", index=False)
print(
    f"Dataset V6 generado. Tasa de interrupción global: {df['disruption_risk'].mean():.2%}"
)
