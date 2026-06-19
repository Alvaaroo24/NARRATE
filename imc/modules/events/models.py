# imc/modules/events/models.py
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class EventModel(BaseModel):
    chat_id: Optional[int] = None
    user_id: Optional[int] = 1
    query: str
    event_type: str
    risk_type_id: Optional[int] = None

    # Añadimos esto para conservar cualquier telemetría extra
    model_config = {"extra": "allow"}


class MessageModel(BaseModel):
    event_id: Optional[int] = Field(default=None, alias="eventId")
    event_type: str = Field(alias="eventType")
    time: int
    time_hr: str = Field(alias="timeHR")

    alert: Optional[str] = None
    data: Optional[dict] = None

    register1: Optional[float] = None
    register2: Optional[float] = None
    register3: Optional[float] = None

    chat_id: Optional[int] = None
    user_id: Optional[int] = None

    # Actualizamos el model_config para permitir campos extra
    model_config = {"populate_by_name": True, "extra": "allow"}

    @model_validator(mode="before")
    def convert_event_id(cls, values):
        if "eventId" in values and isinstance(values["eventId"], str):
            values["eventId"] = int(values["eventId"])
        return values


class MessagingAIResponseModel(BaseModel):
    severity: Optional[str] = "high"
    status: Optional[str] = "solved"
    solution_text: str
