# Intelligent Manufacturing Custodian (IMC) - Smart Manufacturing Network (SMN)

Repositorio oficial con la implementación del código del **Intelligent Manufacturing Custodian (IMC)**, el centro cognitivo y neurálgico encargado de la supervisión, control y orquestación dinámica de la red distribuida *Smart Manufacturing Network* (SMN) dentro del proyecto europeo **NARRATE**. Este desarrollo ha sido realizado en colaboración con la empresa **NUNSYS**.

El núcleo de este Trabajo de Fin de Grado (TFG) consolida la transición arquitectónica desde un diseño monolítico rígido (basado en cadenas secuenciales de LangChain y un único agente *Plan-and-Execute*) hacia una **arquitectura multi-agente jerárquica y descentralizada** fundamentada en grafos de estados mediante el *framework* **LangGraph**. Esta reestructuración resuelve definitivamente los problemas de saturación de la ventana de contexto y elimina las alucinaciones en la invocación de interfaces web, alcanzando una eficacia del 100% en la resolución de incidencias logísticas complejas.

---

## Estructura del Repositorio y Arquitectura de Módulos

### `/agents`
Punto central y núcleo computacional del TFG. Aloja el desarrollo del sistema multi-agente, organizado en una estructura de directorios funcionalmente aislados para garantizar la completa separación de contextos:
- `/core`: Define el núcleo de orquestación del sistema multi-agente. Contiene `agent.py`, encargado de instanciar el grafo de estados (*StateGraph*) y el gestor de persistencia efímera (*MemorySaver*), permitiendo que el servidor opere sin estado (*stateless*) mientras preserva el contexto de memoria aislado por cada hilo de conversación (*thread_id*). Incluye también `react_prompt.py`, que aloja el *prompt* base del Agente Supervisor instruido mediante técnicas de *Few-Shot Learning*.
- `/orchestrator`: En `module.py` se define el **Enrutador de Consultas (Query Router)**. Este componente opera como un clasificador semántico de baja latencia (*Zero-Shot* con temperatura 0.0) que evalúa el mensaje entrante cruzándolo con el catálogo de riesgos. Según la intención detectada, enruta la petición hacia una Consulta Libre (Agente Supervisor), una Alerta IoT (`rag_mock`), o identifica un riesgo tipificado (`PLAN:<ID>`). Además, es el responsable de inyectar el protocolo de emergencia **SYSTEM OVERRIDE**, forzando al supervisor a acatar estrictamente el Plan de Respuesta predefinido.
- `/tools`: Implementa el patrón de diseño *Factory* para dotar al sistema de **Especialización Dinámica** en APIs externas.
  - `registry.py`: Registro y catálogo con persistencia relacional de sub-agentes especializados en APIs.
  - `openapi_tool_factory.py`: Creación de herramientas HTTP mediante el patrón *Factory*. Realiza una destilación semántica y poda heurística de especificaciones OpenAPI/Swagger en tiempo real, transformándolas en manuales técnicos de uso determinista (*Cheat Sheets*).
  - `sub_agent_factory.py`: Creación de sub-agentes ReAct autónomos (`risk_api`, `neo4j_query_api` y `process_orchestration_api`) que envuelven la herramienta HTTP en sub-grafos anidados provistos de su propia memoria y ejemplos *Few-Shot*.
- `/rag_mock`: Sistema de Generación Aumentada por Recuperación (RAG) basado en ChromaDB y *embeddings* vectoriales para la asimilación y descripción técnica explicable de alertas automáticas de sensórica IoT. Fue desarrollado en la versión anterior y se mantiene sin modificaciones.
- `/utils`: Contiene la tecnología de criptografía del sistema multi-agente. Fue desarrollado en la versión anterior y no lo he modificado.

### `/risk`
Contiene el código en el que se sustenta el **Módulo de Analítica y Estimación de Riesgos**. Actúa como un motor predictivo externo de Machine Learning para respaldar empíricamente el razonamiento del IMC:
- `riskAPI.py`: Levanta una API REST síncrona mediante el *framework* FastAPI para consultar la probabilidad probabilística de interrupción de los proveedores, fundamentada en inferencias de un algoritmo **XGBoost** (`XGBClassifier`). Soporta evaluaciones individuales e inferencias por lotes (*batch*), e incorpora simulaciones contrafactuales en tiempo real (**Análisis What-If**).
- `optimizar_modelo.py`: Lógica algorítmica para la optimización de los hiperparámetros del modelo XGBoost mediante búsqueda sistemática aleatorizada (*Randomized Search*). El proceso de ajuste prioriza explícitamente la maximización del área bajo la curva Precision-Recall (**PR-AUC**) para combatir el fuerte desbalanceo de clases del sector industrial (72.5% de envíos seguros frente a un 27.5% de interrupciones). Los hiperparámetros ganadores se consumen en `riskAPI.py`.
- `generar_datos.py`: Generador estocástico que construye el conjunto de datos sintético `dataset.csv` (10.000 instancias), aplicando máscaras lógicas de sesgo basadas en arquetipos de proveedores (peligrosos, promedio y excelentes) e introduciendo variables observables, variables ocultas y un 5% de ruido de etiquetas (*label noise*).

### `/kong-local`
Directorio donde se configura y genera la capa de interoperabilidad centralizada y proxy inverso **API Gateway** mediante contenedores Docker Compose y la tecnología Kong (v3.6 en modo *DB-less* con configuración declarativa en `kong.yml`). Impone políticas de seguridad multicapa: autenticación estricta purgando credenciales (*key-auth* con `hide_credentials: true`), limitación de tasa (*rate limiting* de 100 peticiones por minuto) y trazabilidad distribuida continua (Jaeger y Zipkin mediante `correlation-id`). Los *endpoints* definidos son los utilizados en los Casos de Uso de la evaluación del sistema multi-agente.

### `/imc`
Directorio raíz del **Intelligent Manufacturing Custodian**, el centro neurálgico del proyecto NARRATE.
- Los módulos `/api`, `/databases` (persistencia relacional PostgreSQL y vectorial ChromaDB), `/fastapi` y `/messaging` (mensajería asíncrona MQTT y RabbitMQ) ya estaban desarrollados en la Versión Anterior del IMC. Los cambios que he efectuado han sido para integrarlos con mi sistema multi-agente.
- Del mismo modo, los módulos previos `/data_managers`, `/events` y `/llms` únicamente han sido modificados para la integración con el sistema multi-agente.
- El módulo `/utils` ha sido modificado para crear modelos de respuesta y contexto adaptados al sistema multi-agente (esquemas de validación estrictos provistos por Pydantic que articulan el sistema simbólico), y para añadir el registro de métricas de ejecución (`ExecutionMetrics` evaluando latencia, tokens y completitud de tareas) para la evaluación.

---

## Principios Heurísticos y Tecnológicos del Diseño

- **Colaboración Neuro-Simbólica y Autocorrección (*Self-Correction*)**: La sinergia entre el motor neuronal probabilístico (LLM) y las restricciones de un ecosistema simbólico determinista (esquemas Pydantic y *parsers* OpenAPI) dota a los agentes de capacidades de autorreparación. Si una API rechaza una llamada por un error de tipado o discrepancia de parámetros, el agente pausa el plan, resuelve la anomalía de forma autónoma consultando el inventario y reintenta la acción sin propagar el fallo al usuario.
- **Conciencia de Esquema (*Schema Awareness*) y Política de *Zero Guessing***: El Agente Supervisor tiene estrictamente prohibido intentar adivinar, intuir o autocompletar identificadores técnicos (*IDs*). Ante cualquier entidad descrita por su nombre comercial en lenguaje natural, el orquestador está forzado por contrato a realizar primero una delegación de búsqueda a la base estructural para recuperar el ID exacto antes de operar.
- **Protocolo de Lotes (*Strict Batching Protocol*) y Abstracción Web**: Se prohíbe al supervisor estructurar URLs, rutas o métodos HTTP. Su comunicación hacia los sub-agentes se realiza mediante instrucciones puramente lógicas en lenguaje natural que agrupan todos los objetivos concurrentes en un único bloque (*batching*), delegando al sub-agente la ejecución de peticiones HTTP paralelas (*Parallel Tool Calling*) para eludir bloqueos por límite de tasa.
- **Seguridad *Zero-Knowledge* (Conocimiento Cero)**: El modelo de lenguaje opera completamente desacoplado del material criptográfico. Jamás manipula ni visualiza claves de acceso; en su lugar, interceptores perimetrales en el *pipeline* de la herramienta HTTP interactúan con un módulo criptográfico externo para descifrar en memoria volátil e inyectar de forma transparente los *tokens* de autenticación en las cabeceras de red.
- **Introspección y Explicabilidad (XAI)**: Al finalizar cada resolución, los sub-agentes adjunten obligatoriamente una firma de auditoría detallando los *endpoints* e interfaces web realmente ejecutados (`[SYSTEM META: EXECUTED ENDPOINTS]`), dotando de total transparencia al proceso de toma de decisiones.
- **Rendimiento Comprobado en Benchmarks**: La evaluación empírica demuestra que la arquitectura propuesta alcanza un **Task Completion Rate (TCR) del 100%** en todos los escenarios industriales complejos (frente al fracaso absoluto del 0% TCR de la versión previa monolítica), consolidando una latencia predecible, sumamente estable y con una varianza notablemente reducida.

---

## Configuración del Entorno (.env)
Para proteger los datos de **NUNSYS** y garantizar la estricta **Seguridad *Zero-Knowledge*** de la arquitectura, el archivo `.env` de producción se omite del repositorio público. Para desplegar una instancia local funcional del **Intelligent Manufacturing Custodian (IMC)**, se debe crear un archivo `.env` en la raíz que defina dos grandes bloques de configuración:

- **Motor Cognitivo y Seguridad**: Requiere la clave simétrica `ENCRYPT_SECRET_KEY` para aislar y cifrar los *tokens* de las APIs externas. También agrupa las credenciales de Azure OpenAI, especificando los nombres de despliegue tanto para el LLM principal (`gpt-4o`) como para el modelo de vectorización (`embedding`).
- **Persistencia y Mensajería IoT**: Define la URI de conexión a la base de datos relacional PostgreSQL (`POSTGRES_URL`) apuntando a la base de datos `imc_db`. Además, configura las credenciales de acceso al *broker* de mensajería asíncrona MQTT (`events.bluebridgesolutions.de`) y sus respectivos tópicos de alerta y respuesta para interactuar con la planta en tiempo real.
