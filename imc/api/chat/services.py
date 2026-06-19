from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from imc.api.chat.models import ChatSuccessful
from imc.databases.postgres.models_sqlalchemy import Chat



def create_chat(db: Session) -> ChatSuccessful:
    """
    """
    new_chat = Chat(
        title = "new_chat",
        event_id=1,
        created_by=1
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return ChatSuccessful(successful=True,chat_id=new_chat.id)