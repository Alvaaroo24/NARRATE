# Intelligent Manufacturing Custodian (IMC) - Smart Manufacturing Network (SMN)

Repositorio oficial con la implementación del código del **Intelligent Manufacturing Custodian (IMC)**, el centro cognitivo y neurálgico encargado de la supervisión, control y orquestación dinámica de la red distribuida *Smart Manufacturing Network* (SMN) dentro del proyecto europeo **NARRATE**. Este desarrollo ha sido realizado en colaboración con la empresa **NUNSYS**.

El núcleo de este Trabajo de Fin de Grado (TFG) consolida la transición arquitectónica desde un diseño monolítico rígido (basado en cadenas secuenciales de LangChain y un único agente *Plan-and-Execute*) hacia una **arquitectura multi-agente jerárquica y descentralizada** fundamentada en grafos de estados mediante el *framework* **LangGraph**. Esta reestructuración resuelve definitivamente los problemas de saturación de la ventana de contexto y elimina las alucinaciones en la invocación de interfaces web, alcanzando una eficacia del 100% en la resolución de incidencias logísticas complejas.

---

## Estructura del Repositorio y Arquitectura de Módulos

La topología del repositorio refleja la estricta segregación de responsabilidades del diseño arquitectónico en cinco grandes pilares:

### 1. `/agents` (Núcleo Computacional Multi-Agente)
Punto central y núcleo computacional del TFG. Aloja el desarrollo del sistema multi-agente, organizado en una estructura de directorios funcionalmente aislados para garantizar la completa separación de contextos:
- `/core`: Define el núcleo de orquestación del sistema multi-agente. Contiene `agent.py`, encargado de instanciar el grafo de estados (*StateGraph*) y el gestor de persistencia efímera (*MemorySaver*), permitiendo que el servidor opere sin estado (*stateless*) mientras preserva el contexto de memoria aislado por cada hilo de conversación (*thread_id*). Incluye también `react_prompt.py`, que aloja el *prompt* base del Agente Supervisor instruido mediante técnicas de *Few-Shot Learning*.
- `/orchestrator`: En `module.py` se define el **Enrutador de Consultas (Query Router)**. Este componente opera como un clasificador semántico de baja latencia (*Zero-Shot* con temperatura 0.0) que evalúa el mensaje entrante cruzándolo con el catálogo de riesgos. Según la intención detectada, enruta la petición hacia una Consulta Libre (Agente Supervisor), una Alerta IoT (`rag_mock`), o identifica un riesgo tipificado (`PLAN:<ID>`). Además, es el responsable de inyectar el protocolo de emergencia **SYSTEM OVERRIDE**, forzando al supervisor a acatar estrictamente el Plan de Respuesta predefinido.
- `/tools`: Implementa el patrón de diseño *Factory* para dotar al sistema de **Especialización Dinámica** en APIs externas.
  - `registry.py`: Registro y catálogo con persistencia relacional de sub-agentes especializados en APIs. La resolución de los secretos y claves de autenticación se extrae en texto plano de la base de datos desacoplándola del *prompt*.
  - `openapi_tool_factory.py`: Creación de herramientas HTTP mediante el patrón *Factory*. Realiza una destilación semántica y poda heurística de especificaciones OpenAPI/Swagger en tiempo real, transformándolas en manuales técnicos de uso determinista (*Cheat Sheets*).
  - `sub_agent_factory.py`: Creación de sub-agentes ReAct autónomos (`risk_api`, `neo4j_query_api` y `process_orchestration_api`) que envuelven la herramienta HTTP en sub-grafos anidados provistos de su propia memoria y ejemplos *Few-Shot*.
- `/rag_mock`: Sistema de Generación Aumentada por Recuperación (RAG) basado en ChromaDB y *embeddings* vectoriales para la asimilación y descripción técnica explicable de alertas automáticas de sensórica IoT. Fue desarrollado en la versión anterior y se mantiene sin modificaciones para servir como sistema de apoyo.

### 2. `/kong-local` (Capa Perimetral e Interoperabilidad API Gateway)
Capa de interoperabilidad y proxy inverso que centraliza la comunicación del sistema multi-agente con todos los microservicios mediante contenedores en Docker Compose.
- Despliegue de **Kong API Gateway** (v3.6) bajo el paradigma *DB-less* mediante el archivo de configuración declarativa `kong.yml`.
- Implementa autenticación segura ocultando credenciales (*key-auth* con `hide_credentials: true`), segregación por Listas de Control de Acceso (ACLs) y limitación de tasa (*rate-limiting* global de 100 peticiones por minuto).
- Integra observabilidad y trazabilidad distribuida mediante **Jaeger** y **Zipkin** propagando identificadores de correlación (`correlation-id` en cabecera `X-Request-ID`), junto con una interfaz unificada en **Swagger-UI**.

### 3. `/risk` (Módulo de Analítica y Estimación de Riesgos)
Contiene el código en el que se sustenta el **Módulo de Analítica y Estimación de Riesgos**. Actúa como un motor predictivo externo de Machine Learning para respaldar empíricamente el razonamiento del IMC:
- `riskAPI.py`: Levanta una API REST síncrona mediante el *framework* FastAPI para consultar la probabilidad de interrupción de los proveedores, fundamentada en inferencias de un algoritmo **XGBoost** (`XGBClassifier`). Soporta evaluaciones individuales e inferencias por lotes (*batch*), e incorpora simulaciones contrafactuales en tiempo real (**Análisis What-If**). Protegido por una capa de validación de esquemas en Pydantic (`CondicionesEscenario`).
- `optimizar_modelo.py`: Lógica algorítmica para la optimización de los hiperparámetros del modelo XGBoost mediante búsqueda sistemática aleatorizada (*Randomized Search*). El proceso de ajuste prioriza explícitamente la maximización del área bajo la curva Precision-Recall (**PR-AUC**) para combatir el fuerte desbalanceo de clases del sector industrial (72.5% vs 27.5%). Integra **joblib** para la persistencia binaria del *pipeline*.
- `generar_datos.py`: Script de generación estocástica de datos sintéticos (10,000 instancias) aplicando arquetipos de proveedores, variables observables, ocultas y un 5% de ruido de etiquetas (*label noise*).

### 4. `/imc` (Middleware Central y Proxy Inverso)
Componente intermediario que aísla perimetralmente el núcleo de Inteligencia Artificial.
- `imc_proxy.py`: Proxy inverso que canaliza las peticiones de la plataforma de monitorización, realiza la validación determinista de sesión mediante inyección de dependencias (`get_current_user`) y asocia el identificador verificado del operador antes de conectar con la red interna del motor de IA. Unifica los mensajes directos de chat y los flujos asíncronos de alertas físicas de la planta vía MQTT.

### 5. `/evaluation` (Framework de Benchmarking y Auditoría E2E)
Módulo dedicado a la validación cuantitativa del rendimiento, la estabilidad de respuesta y la explicabilidad del sistema síncrono:
- `evaluacion_analitica.py`: Suite de auditoría de Machine Learning que enfrenta el modelo XGBoost optimizado contra un *Baseline* de Regresión Logística. Ejecuta un análisis de rendimiento en el *Test Set* calculando el Error de Calibración Esperado (*Expected Calibration Error* - ECE) y fijando el umbral de decisión operativo en **0.335**. Genera de forma automatizada seis artefactos gráficos de diagnóstico (`grafico_01` al `06`) que incluyen curvas PR/ROC, matrices de confusión, curvas de calibración, densidades KDE y explicabilidad global mediante valores **SHAP**.
- `evaluator.py`: Orquestador de *benchmarking* automatizado que somete el *endpoint* síncrono del IMC (`/query`) a un test de estrés de **80 peticiones End-to-End** (4 escenarios industriales complejos de NARRATE sometidos a 20 iteraciones cada uno). Compila los resultados en dos entregables de auditoría:
  1. `evaluacion_multiagente_api_METRICAS-FINALES.xlsx`: Matriz de telemetría que registra latencias, consumo de tokens, longitud de trayectoria de pasos, conteos de recuperación de errores y la tasa de acciones válidas.
  2. `evaluacion_reasoning_steps_METRICAS-FINALES.json`: Volcado de memoria que audita y serializa el hilo de pensamiento interior (*reasoning logs*) de cada agente involucrado.

---

## Auditoría de Sistema

Para replicar la batería de pruebas empíricas y regenerar los entregables de validación, ejecuta desde el directorio raíz:

```bash
# 1. Generar los 6 gráficos de diagnóstico del motor predictivo y explicabilidad SHAP
python evaluacion_analitica.py

# 2. Lanzar el benchmark de estrés E2E del Orquestador Multi-Agente (Genera Excel y JSON)
python evaluator.py
