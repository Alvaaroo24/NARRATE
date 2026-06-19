from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.api.query.models import QueryInput
from imc.modules.agents.utils.models import QueryResponse
import imc.api.query.services as services
from imc.databases.postgres.database import get_db
from imc.databases.postgres.database_async import get_db_async


router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query(query_input: QueryInput, db: Session = Depends(get_db)):
    """
    """
    try:
        response = await services.query(query_input=query_input, db=db)
    except Exception as e:
        print(e)
        # TODO: Manage exceptions
        raise HTTPException(status_code=500, detail="Unexpected error")

    return response
