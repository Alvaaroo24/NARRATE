from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.databases.postgres.models_sqlalchemy import RiskType
from imc.modules.agents.utils.models import RiskTypeData


class RiskTypeManagerBase(ABC):
    @abstractmethod
    async def get_risk_type(self, id: int, db: Session) -> RiskTypeData:
        pass
    @abstractmethod
    async def get_risk_types(self, db: Session) -> List[RiskTypeData]:
        pass

    @abstractmethod
    async def save_risk_type(self, db:AsyncSession, plan):
        pass


class RiskTypeManager(RiskTypeManagerBase):
    async def get_risk_type(self, id: int, db: Session) -> RiskTypeData:
        risk_type: RiskType | None = db.scalars(select(RiskType).where(RiskType.id == id)).first()
        
        if risk_type is None:
            return None
        
        return RiskTypeData(
            id=risk_type.id,
            name=risk_type.name,
            description=risk_type.description,
            plan_id=risk_type.plan_id
        )
    async def get_risk_types(self, db: Session) -> list[RiskTypeData]:
        risk_types_data_object: list[RiskType] = db.scalars(select(RiskType)).all()

        return [
            RiskTypeData(
                id=risk_type.id,
                name=risk_type.name,
                description=risk_type.description,
                plan_id=risk_type.plan_id
            ) for risk_type in risk_types_data_object
        ]
    
    async def save_risk_type(self, db, plan):
        pass