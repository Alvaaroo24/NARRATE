import json
from langchain.chains import create_retrieval_chain
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains.combine_documents import create_stuff_documents_chain
from imc.config import settings
from imc.modules.llms.llm import llm as LLM
from langchain_core.prompts import ChatPromptTemplate

# Importamos ResponseModel y ContextModel
from imc.modules.agents.utils.models import ResponseModel, ContextModel


def query_chroma_rag(question: str, event_payload: dict = None):
    """Query an existing Chroma DB using Azure Chat and embeddings, considering full payload and specific telemetry."""

    embeddings = AzureOpenAIEmbeddings(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_base_url,
        azure_deployment=settings.azure_openai_embedding_model_deployment_name,
        openai_api_version=settings.azure_openai_api_version,
    )
    with open("imc/databases/chroma_mock/mock_data.txt", "r", encoding="utf-8") as f:
        additional_context = f.read()

    vectordb = Chroma(
        persist_directory="imc/databases/chroma_mock", embedding_function=embeddings
    )
    retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    llm = LLM

    # 1. Extracción segura de los parámetros específicos (Ajusta las keys según tu JSON real)
    sensor_type = event_payload.get("sensorType", "N/A") if event_payload else "N/A"
    threshold = event_payload.get("threshold", "N/A") if event_payload else "N/A"
    current_value = (
        event_payload.get("currentValue", event_payload.get("actualValue", "N/A"))
        if event_payload
        else "N/A"
    )
    units = event_payload.get("units", "N/A") if event_payload else "N/A"
    machine_id = event_payload.get("machineId", "N/A") if event_payload else "N/A"

    # Convertimos el payload completo a string por si hay información adicional útil
    payload_str = (
        json.dumps(event_payload, ensure_ascii=False)
        if event_payload
        else "No additional payload"
    )

    # 2. Actualizamos el template estructurando las métricas críticas
    prompt = ChatPromptTemplate.from_template(
        """You are an intelligent assistant helping answer user questions based on the provided context.
        
    Primary Alert / Query:
    {input}
    
    Critical Telemetry Metrics:
    - Machine ID: {machine_id}
    - Sensor Type: {sensor_type}
    - Current Value: {current_value} {units}
    - Threshold: {threshold} {units}
    
    Full Event Payload (Raw Metadata):
    {payload}
    
    Context:
    {context}
    
    Additional context:
    {additional_context}

    Provide a clear and concise answer based only on the context above. Pay special attention to the Critical Telemetry Metrics to formulate your response.
    If the context does not contain enough information, say you don't know.
    """
    )

    combine_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, combine_chain)

    # 3. Inyectamos las variables extraídas en la invocación de la cadena
    result = rag_chain.invoke(
        {
            "input": question,
            "machine_id": machine_id,
            "sensor_type": sensor_type,
            "current_value": current_value,
            "threshold": threshold,
            "units": units,
            "payload": payload_str,
            "additional_context": additional_context,
        }
    )

    print("Answer:\n", result["answer"])

    doc_count = len(result.get("context", []))

    # 4. Modificamos los logs para reflejar de forma clara las métricas específicas
    params_to_log = {
        "query": question,
        "telemetry": {
            "machine_id": machine_id,
            "sensor_type": sensor_type,
            "current_value": current_value,
            "threshold": threshold,
            "units": units,
        },
    }

    if event_payload:
        params_to_log["raw_payload"] = event_payload

    params_str = json.dumps(params_to_log, ensure_ascii=False)

    rag_step = [
        {
            "value": f"Machine/IoT alert detected. Querying technical manuals database.\nTool: vector_db_retriever\nParameters: {params_str}"
        },
        {
            "response": f"Semantic search completed. {doc_count} relevant context snippets retrieved."
        },
    ]

    return ResponseModel(
        question=question,
        answer=result["answer"],
        context=ContextModel(
            context_documents=result["context"],
            reasoning_steps=[rag_step],
        ),
    )
