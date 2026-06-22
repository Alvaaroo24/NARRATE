import json
import time
import pandas as pd
import requests

URL_ORQUESTADOR = "http://localhost:8010/query"
ITERACIONES_PER_CASE = 20
OUTPUT_XLSX = "evaluacion_multiagente_api_METRICAS-FINALES.xlsx"
OUTPUT_JSON = "evaluacion_reasoning_steps_METRICAS-FINALES.json"
# OUTPUT_XLSX = "evaluacion_multiagente_api_METRICAS-OLD-FINALES.xlsx"
# OUTPUT_JSON = "evaluacion_reasoning_steps_METRICAS-OLD-FINALES.json"

TEST_CASES = {
    "1_Exploracion_Dinamica": "Show me the risk associated with all the suppliers of the product called Bespoke Baby Cot.",
    "2_Plan_Respuesta_Estricto": "We have a problem. Our supplier (ID: MS_002) has just informed us that they will not be able to deliver the components in time for this week's production.",
    "3_Plan_Incompleto_Improvisacion": "Give me all alternative suppliers for the product VS160-CH, which is supplied by SUP007, and sort them by the delivery time.",
    "4_Recomendacion_Condicionada": "Recommend all the suppliers associated with the product called Bespoke Baby Cot whose risk is not High assuming a climate risk index of 0.5 and a saturation level of 60%.",
}


def run_evaluation():
    print(
        f"🚀 Iniciando evaluación E2E vía API REST ({ITERACIONES_PER_CASE} iteraciones por caso)..."
    )
    print(f"📡 Endpoint objetivo: {URL_ORQUESTADOR}")

    results_data = []
    reasoning_logs = []

    TU_USER_ID_REAL = 1

    for case_name, query_text in TEST_CASES.items():
        print(f"\n🧪 Evaluando Caso: {case_name}")

        current_chat_id = None

        for i in range(ITERACIONES_PER_CASE):
            print(
                f"   ▶ Iteración {i + 1}/{ITERACIONES_PER_CASE}... ", end="", flush=True
            )

            query_visual = f"[Test: {case_name} | Iteración {i + 1}]\n{query_text}"

            payload = {
                "query": query_visual,
                "user_id": TU_USER_ID_REAL,
                "event_type": "evaluation_script",
            }

            if current_chat_id is not None:
                payload["chat_id"] = current_chat_id

            try:
                t0 = time.time()
                response = requests.post(URL_ORQUESTADOR, json=payload, timeout=120)
                latencia_red = time.time() - t0

                if response.status_code != 200:
                    print(f"❌ FALLO HTTP {response.status_code}")
                    registrar_fallo(
                        results_data,
                        reasoning_logs,
                        case_name,
                        i + 1,
                        query_text,
                        f"HTTP {response.status_code}",
                    )
                    continue

                data = response.json()

                if current_chat_id is None:
                    current_chat_id = data.get("chat_id")

                response_body = data.get("response", {})
                context_data = response_body.get("context", {})
                metrics = context_data.get("metrics", {})

                respuesta_texto = response_body.get("answer", "")
                exito_tecnico = context_data.get("success", False)
                pasos_razonamiento = context_data.get("reasoning_steps", [])

                latencia_interna = metrics.get("latency_seconds", latencia_red)
                tokens = metrics.get("total_tokens", 0)
                pasos = metrics.get("trajectory_steps", 0)
                recuperaciones = metrics.get("error_recovery_count", 0)
                ratio_validas = metrics.get("valid_actions_rate", 0.0)

                results_data.append(
                    {
                        "Escenario": case_name,
                        "Iteracion": i + 1,
                        "Latencia_Total_s": latencia_interna,
                        "Tokens": tokens,
                        "Pasos": pasos,
                        "Recuperaciones_Error": recuperaciones,
                        "Tasa_Acciones_Validas": ratio_validas,
                        "Exito_Tecnico": int(exito_tecnico),
                        "Respuesta_LLM": respuesta_texto,
                    }
                )

                reasoning_logs.append(
                    {
                        "Escenario": case_name,
                        "Iteracion": i + 1,
                        "Chat_ID": current_chat_id,
                        "Reasoning_Steps": pasos_razonamiento,
                    }
                )

                print(f"✅ OK (Chat ID: {current_chat_id})")

            except requests.exceptions.RequestException as e:
                print(f"❌ Error de conexión: {e}")
                registrar_fallo(
                    results_data, reasoning_logs, case_name, i + 1, query_text, str(e)
                )
            except Exception as e:
                print(f"❌ Error de parseo: {e}")
                registrar_fallo(
                    results_data, reasoning_logs, case_name, i + 1, query_text, str(e)
                )

    df = pd.DataFrame(results_data)
    try:
        df.to_excel(OUTPUT_XLSX, index=False, engine="openpyxl")
        print(f"\n💾 Métricas exportadas exitosamente a '{OUTPUT_XLSX}'")
    except Exception as e:
        print(f"\n❌ Error al guardar el Excel (¿Falta instalar 'openpyxl'?): {e}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(reasoning_logs, f, indent=4, ensure_ascii=False)
    print(f"🧠 Pasos de razonamiento exportados a '{OUTPUT_JSON}'")


def registrar_fallo(
    results_data, reasoning_logs, case_name, iteracion, query_text, error_msg
):
    """Helper para registrar fallos tanto en métricas como en logs de razonamiento."""
    results_data.append(
        {
            "Escenario": case_name,
            "Iteracion": iteracion,
            "Latencia_Total_s": 0.0,
            "Tokens": 0,
            "Pasos": 0,
            "Recuperaciones_Error": 0,
            "Tasa_Acciones_Validas": 0.0,
            "Exito_Tecnico": 0,
            "Respuesta_LLM": f"ERROR: {error_msg}",
        }
    )

    reasoning_logs.append(
        {
            "Escenario": case_name,
            "Iteracion": iteracion,
            "Chat_ID": None,
            "Reasoning_Steps": [f"ERROR CRÍTICO: {error_msg}"],
        }
    )


if __name__ == "__main__":
    run_evaluation()
