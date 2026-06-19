from typing import Any, Optional

from pydantic import BaseModel


class QueryInput(BaseModel):
    chat_id: Optional[int] = None
    user_id: Optional[int] = 1
    query: str

    