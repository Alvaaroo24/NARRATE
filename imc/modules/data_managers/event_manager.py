from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.databases.postgres.models_sqlalchemy import Event, EventSource
from imc.modules.agents.utils.models import EventData


class EventManagerBase(ABC):
    @abstractmethod
    async def get_event(self, id: int, db: Session) -> EventData:
        pass

    @abstractmethod
    async def save_event(self, payload: str, risk_type_id: int, event_type: str, db:Session):
        pass


class EventManager(EventManagerBase):
    async def get_event(self, id: int, db: Session) -> EventData:
        event: Event | None = db.scalars(select(Event).where(Event.id == id)).first()

        if event is None:
            return None
        
        return EventData(
            id=event.id,
            payload=event.payload,
            risk_type_id=event.risk_type_id
        )
    
    async def save_event(self, payload: str, risk_type_id: int, event_type: str, db:Session) -> int:
        # TODO: More detailed data here like external_id and severity. They could be attributes of the EventModel
        if event_type == "chat_query":
            source = EventSource.USER
        else:
            source = EventSource.DETECTOR # TODO: Other possible sources for rabbitmq messages?
        new_event = Event(
            payload=payload,
            risk_type_id=risk_type_id,
            source=source
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        return new_event.id