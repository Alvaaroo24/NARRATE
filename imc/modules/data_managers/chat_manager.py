from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
import re

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from imc.databases.postgres.models_sqlalchemy import Message, Chat
from imc.modules.agents.utils.models import ResponseModel, HistoryData
from imc.modules.data_managers.utils import create_chat_title_from_query


class ChatManagerBase(ABC):
    @abstractmethod
    async def get_event_id_from_chat_id(self, chat_id: int, db: Session) -> int:
        pass
    @abstractmethod
    async def create_chat(self, event_id: int, user_id: int, first_message: str, db: Session) -> int:
        pass
    @abstractmethod
    async def get_history(self, chat_id: int, db: Session) -> list[HistoryData]:
        pass
    
    @abstractmethod
    def parse_history_answers(self, history:list[HistoryData]) -> list[str]:
        pass

    @abstractmethod
    async def add_message(self, chat_id: int, user_id: int, message: ResponseModel, db:Session):
        pass


class ChatManager(ChatManagerBase):
    async def get_event_id_from_chat_id(self, chat_id: int, db: Session) -> int:
        chat: Chat | None = db.scalars(select(Chat).where(Chat.id == chat_id)).first()

        if chat is None:
            return None
        
        return chat.event_id

    async def create_chat(self, event_id: int, user_id: int, first_message: str, db: Session) -> int:
        chat_title: str = await create_chat_title_from_query(query=first_message)
        new_chat = Chat(
            title=chat_title,
            event_id=event_id,
            created_by = user_id
        )
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)

        return new_chat.id

    async def get_history(self, chat_id: int, db: Session) -> list[HistoryData]:
        message_object: list[Message] = db.scalars(select(Message).filter(Message.chat_id==chat_id)).all()
        return [
            HistoryData(
                id=message.id,
                question=message.question,
                answer=message.answer,
                chat_id=message.chat_id
            ) for message in message_object
        ]
        
    def parse_history_answers(self, history: list[HistoryData]) -> list[str]:
        raw_answers = [a.answer for a in history if a.answer is not None]
        parsed_answers = []
        for answer in raw_answers:
            match = re.search(r"'answer':\s*'(.*?)',\s*'reasoning_steps'", answer, re.DOTALL)
            if match:
                parsed_answers.append(match.group(1).strip())
                
        return parsed_answers
    
    async def add_message(self, chat_id: int, user_id: int, message: ResponseModel, db:Session):
        # We save answer and reasoning steps in the answer column of the table messages # TODO: Save reasoning steps in a new column?
        answer = {
            "answer": message.answer,
            "reasoning_steps": message.context.reasoning_steps
        }
        new_message = Message(
            question=message.question,
            answer=str(jsonable_encoder(answer)),
            response_time_ms=1200,
            chat_id=chat_id,
            created_by=user_id
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        pass