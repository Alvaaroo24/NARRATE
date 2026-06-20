from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field


class ExecutionMetrics(BaseModel):
    latency_seconds: float = Field(0.0, description="End-to-End Latency")
    total_tokens: int = Field(0, description="Consumo total de tokens")
    trajectory_steps: int = Field(
        0, description="Longitud de la Trayectoria (número de pasos)"
    )
    error_recovery_count: int = Field(
        0, description="Veces que el agente se autocorigió"
    )
    valid_actions_rate: float = Field(
        0.0, description="Ratio de llamadas a herramientas exitosas vs fallidas"
    )


class ContextModel(BaseModel):
    reasoning_steps: Optional[List[Any]] = Field(
        default_factory=list,
        description="List of all reasoning and tool steps taken by the agent.",
    )
    success: Optional[bool] = Field(
        None, description="Whether the execution completed successfully."
    )
    error_message: Optional[str] = Field(
        None, description="Any error that occurred during execution."
    )
    context_documents: Optional[List[Any]] = Field(default_factory=list)
    metrics: Optional[ExecutionMetrics] = Field(
        None, description="Métricas de evaluación del TFG"
    )


class StepModel(BaseModel):
    action: Optional[str] = Field(
        None, description="The name of the executed tool (Tool Call)."
    )
    action_input: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="The parameters sent to the tool."
    )
    observation: Optional[Any] = Field(
        None, description="The result returned by the tool (Tool Message)."
    )
    thought: Optional[str] = Field(
        None, description="The agent's reasoning before or after the action."
    )


class ResponseModel(BaseModel):
    question: str = Field(..., description="The input question to the agent.")
    answer: Optional[Any] = Field(
        None, description="The final answer returned by the agent."
    )
    context: ContextModel


class QueryResponse(BaseModel):
    chat_id: Optional[int] = None
    response: Any


class PlanData(BaseModel):
    id: int
    name: str
    description: str
    instructions: str


class RuleData(BaseModel):
    id: int
    name: str
    description: str
    expression: str
    priority: int


class HistoryData(BaseModel):
    id: int
    question: str
    answer: str
    chat_id: int


class RiskTypeData(BaseModel):
    id: int
    name: str
    description: str
    plan_id: int


class EventData(BaseModel):
    id: Optional[int] = None
    payload: str
    risk_type_id: Optional[int] = None
