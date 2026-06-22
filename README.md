# Intelligent Manufacturing Custodian (IMC) - Smart Manufacturing Network (SMN)

Repositorio oficial con la implementación del código del **Intelligent Manufacturing Custodian (IMC)**, el centro cognitivo y neurálgico encargado de la supervisión, control y orquestación dinámica de la red distribuida *Smart Manufacturing Network* (SMN) dentro del proyecto europeo **NARRATE**. Este desarrollo ha sido realizado en colaboración con la empresa **NUNSYS**.

El núcleo de este Trabajo de Fin de Grado (TFG) consolida la transición arquitectónica desde un diseño monolítico rígido (basado en cadenas secuenciales de LangChain y un único agente *Plan-and-Execute*) hacia una **arquitectura multi-agente jerárquica y descentralizada** fundamentada en grafos de estados mediante el *framework* **LangGraph**. Esta reestructuración resuelve definitivamente los problemas de saturación de la ventana de contexto y elimina las alucinaciones en la invocación de interfaces web, alcanzando una eficacia del 100% en la resolución de incidencias logísticas complejas.

---

## Estructura del Repositorio y Arquitectura de Módulos

La topología del repositorio refleja la estricta segregación de responsabilidades del diseño arquitectónico en cuatro grandes pilares:

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

---

## Características Principales y Rendimiento

- **Razonamiento ReAct y Conciencia de Esquema (*Schema Awareness*)**: Implementación estricta de resolución previa de identificadores unívocos para erradicar las alucinaciones en los parámetros de red.
- **Protocolo de Autocorrección (*Self-Correction*)**: Capacidad de atrapar errores de API en tiempo de ejecución y subsanar dinámicamente el mapeo de entidades sin interrumpir el flujo.
- **Rendimiento Comprobado en Benchmarks**: La evaluación empírica demuestra que la arquitectura propuesta alcanza un **Task Completion Rate (TCR) del 100%** en todos los escenarios industriales complejos (frente al fracaso absoluto del 0% TCR de la versión previa monolítica), consolidando una latencia predecible, sumamente estable y con una varianza notablemente reducida.

---

## Configuración del Entorno (.env)

Para proteger los datos de **NUNSYS** y garantizar la ciberseguridad de la red, el archivo `.env` de producción se omite del repositorio público. Para desplegar una instancia local funcional del **Intelligent Manufacturing Custodian (IMC)**, se debe crear un archivo `.env` en la raíz que defina la configuración sensible gestionada centralizadamente mediante `pydantic_settings`:

- **Motor Cognitivo Azure OpenAI**: Define las credenciales y claves de acceso (`AZURE_OPENAI_API_KEY`), especificando los nombres de despliegue tanto para el LLM principal (`gpt-4o`) como para el modelo de vectorización (`embedding`).
- **Persistencia y Mensajería IoT**: Define la URI de conexión a la base de datos relacional PostgreSQL (`POSTGRES_URL`) apuntando a la base de datos `imc_db`. Además, configura las credenciales de acceso al *broker* de mensajería asíncrona MQTT y sus respectivos tópicos de alerta y respuesta para interactuar con la planta en tiempo real.
