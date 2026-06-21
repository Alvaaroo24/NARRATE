import uvicorn
import re
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Path, Body
from pydantic import BaseModel, Field


import joblib

print("Iniciando Risk API V5.1 - Entorno Industrial con Pipeline de Scikit-Learn...")

try:
    df = pd.read_csv("dataset.csv")

    pipeline_xgb = joblib.load("risk_pipeline.pkl")
except FileNotFoundError as e:
    print(f"ERROR FATAL: Archivo no encontrado. Detalles: {e}")
    exit()

id_col = "provider_id"
target = "disruption_risk"
PROVEEDORES_VALIDOS = set(df[id_col].unique())
PATRON_ID = r"^[A-Z]{2}_\d{3}$"

print("¡Pipeline V5.1 cargado con éxito!")


class CondicionesEscenario(BaseModel):
    supply_category: Optional[str] = None
    logistics_mode: Optional[str] = None

    machinery_oee_efficiency: Optional[float] = Field(None, ge=0.0, le=1.0)
    capacity_saturation_level_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    asset_age_years: Optional[float] = Field(None, ge=0.0)
    days_since_last_maintenance: Optional[int] = Field(None, ge=0)
    staff_turnover_rate_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    audit_compliance_score: Optional[float] = Field(None, ge=0.0, le=100.0)

    class Config:
        json_schema_extra = {
            "example": {
                "capacity_saturation_level_pct": 60.5,
                "climate_risk_index": 0.5,
            }
        }

    climate_risk_index: Optional[float] = Field(None, ge=0.0, le=1.0)
    average_lead_time_days: Optional[float] = Field(None, ge=0.0)
    quality_defect_ratio_pct: Optional[float] = Field(None, ge=0.0, le=100.0)


app = FastAPI(
    title="Risk API - Industrial Supply Chain V5.1",
    description="Motor predictivo optimizado para la detección de interrupciones en cadena de suministro.",
    version="5.1.0",
)


def _calcular_riesgo_modelo(id_input: str, condiciones_extra: dict = None) -> dict:
    datos_proveedor = df[df[id_col] == id_input].copy()

    if condiciones_extra:
        for columna, valor in condiciones_extra.items():
            if columna in datos_proveedor.columns:
                datos_proveedor[columna] = valor

    X_prov = datos_proveedor.drop(columns=[id_col, target])

    probabilidades = pipeline_xgb.predict_proba(X_prov)[:, 1]
    probabilidad_media = float(np.mean(probabilidades))

    umbral_optimo = 0.335

    if probabilidad_media >= umbral_optimo:
        nivel = "Alto"
    elif probabilidad_media >= (umbral_optimo * 0.6):
        nivel = "Medio"
    else:
        nivel = "Bajo"

    resultado = {
        "id": id_input,
        "riesgo": nivel,
        "probabilidad_fallo_pct": round(probabilidad_media * 100, 2),
        "umbral_decision_optimo": round(umbral_optimo * 100, 1),
        "tipo_consulta": "simulacion" if condiciones_extra else "historico_base",
    }

    if condiciones_extra:
        resultado["escenario_simulado"] = condiciones_extra

    return resultado


@app.post("/api/provider/{id_input}/simulate-risk")
def simular_riesgo_condicional(
    id_input: str = Path(..., description="ID del proveedor (ej. MS_001)"),
    condiciones: Optional[CondicionesEscenario] = Body(None),
):
    if not re.match(PATRON_ID, id_input):
        raise HTTPException(status_code=400, detail="Formato de ID incorrecto.")
    if id_input not in PROVEEDORES_VALIDOS:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    diccionario_condiciones = (
        condiciones.dict(exclude_unset=True, exclude_none=True) if condiciones else {}
    )
    return _calcular_riesgo_modelo(id_input, condiciones_extra=diccionario_condiciones)


@app.post("/api/risk/calcular-riesgo-batch")
def calcular_riesgo_lote(ids: List[str] = Body(...)):
    resultados = []
    for id_input in ids:
        if id_input in PROVEEDORES_VALIDOS:
            resultados.append(_calcular_riesgo_modelo(id_input))
        else:
            resultados.append({"id": id_input, "error": "No encontrado"})
    return resultados


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1024)
