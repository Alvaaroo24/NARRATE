En la carpeta /risk se encuentra el código en el que se sustenta el Módulo de Estimación de Riesgos.
  - riskAPI.py: Lanza una API para consultar el riesgo de los proveedores, basándose en las predicciones realizadas por un modelo XGBoost.
  - optimizar_modelo.py: El código con el que se optimiza el modelo XGBoost. Los híperparametros obtenidos se usan en riskAPI.py
  - generar_datos.py: Genera los datos sintéticos dataset.csv

En la carpeta /kong-local se genera el API Gateway. Los endpoints definidos son los usados en los Casos de Uso de la Evaluación del sistema multi-agente.

En la carpeta /imc se encuentra el Intelligent Manufacturing Custodian, centro neurálgico del proyecto NARRATE.

Los módulos /api, /databases, /fastapi y /messaging ya estaban desarrollados en la Versión Anterior del IMC. Los cambios que he efectúado han sido para integralos con mi sistema multi-agente.

Del mismo modo, los módulos /data_managers, /events y /llms únicamente han sido modificados para la integración con el sistema multi-agente.

El módulo /utils ha sido modificado para crear modelos de respuesta y contexto adaptados al sistema multi-agente, y añadir registro de métricas para la evaluación.

El punto central de mi TFG, el desarrollo del sistema multi-agente, se encuentra en el módulo /agents. Dentro de este directorio defino una estructura de directorios aislados para cada funcionalidad:
  - /core
    - Se define el núcleo del sistema multi-agente: el inicalizador de agentes en agent.py y el prompt del Agente Supervisor (Few-Shot Learning) en react_prompt.py.
  - /orchestrator
    - En module.py, se define el Enrutador de Consultas. Según la naturaleza de la consulta/alerta recibida, se decide que flujo de trabajo se seguirá para resolverla (info en el TFG).
  - /rag_mock
    - Desarrollado en la versión anterior. No lo he modificado.
  - /tools
    - En este módulo se definen los sub-agentes creados mediante el patrón Factory.
    - registry.py: Registro de sub-agentes especializados en APIs. (Tecnologías nombradas en el TFG)
    - openapi_tool_factory.py: Creación de herramientas HTTP mediante patrón Factory. (Tecnologías nombradas en el TFG)
    - sub_agent_factory.py: Creación de sub-agentes especializados que envuelven la herramienta HTTP. (Tecnologías nombradas en el TFG)
  - /utils
    - Tecnología de criptografía del sistema multi-agente. Desarrollado en la versión anterior.
    
