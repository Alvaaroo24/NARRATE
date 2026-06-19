from typing import List, Any
from pydantic import BaseModel, Field

class ResponseModel(BaseModel):
    answer: str = Field(..., description="Generated answer to the user's question")
    context: List[Any] = Field(..., description="List of context documents used to form the answer")
    
