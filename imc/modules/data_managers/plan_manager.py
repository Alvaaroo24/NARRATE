from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.databases.postgres.models_sqlalchemy import Plan
from imc.modules.agents.utils.models import PlanData


class PlanManagerBase(ABC):
    @abstractmethod
    async def get_plans(self, db: Session) -> List[PlanData]:
        pass
    
    @abstractmethod
    async def get_plan(self, id: int, db: Session) -> PlanData:
        pass

    @abstractmethod
    async def save_plan(self, db:AsyncSession, plan):
        pass


class PlanManager(PlanManagerBase):
    async def get_plans(self, db: Session) -> list[PlanData]:
        plan_list_object: list[Plan] = db.scalars(select(Plan)).all()
        return [
            PlanData(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                instructions=plan.instructions
            ) for plan in plan_list_object
        ]
    
    async def get_plan(self, id: int, db: Session) -> PlanData:
        plan: Plan | None = db.scalars(select(Plan).where(Plan.id == id)).first()

        if plan is None:
            return None
        
        return PlanData(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            instructions=plan.instructions
        )
    
    async def save_plan(self, db, plan):
        pass