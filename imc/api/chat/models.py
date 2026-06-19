from typing import Optional
from pydantic import BaseModel


class ChatSuccessful(BaseModel):
    successful: bool
    chat_id: Optional[int] = None