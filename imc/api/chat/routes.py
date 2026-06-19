from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.future import select
from sqlalchemy.orm import Session

from imc.api.chat.models import ChatSuccessful
import imc.api.chat.services as services
from imc.databases.postgres.database import get_db


router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatSuccessful)
def create_chat(db: Session = Depends(get_db)):
    try:
        response = services.create_chat(db=db)
    except Exception as e:
        print(e)
        # TODO: Manage exceptions
        raise HTTPException(status_code=500, detail="Unexpected error")

    return response
