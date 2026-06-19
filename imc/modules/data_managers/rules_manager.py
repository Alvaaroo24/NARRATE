from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.databases.postgres.models_sqlalchemy import Rule
from imc.modules.agents.utils.models import RuleData


class RulesManagerBase(ABC):
    @abstractmethod
    async def get_rules(self, db: Session) -> list[RuleData]:
        pass


class RulesManager(RulesManagerBase):
    async def get_rules(self, db: Session) -> list[RuleData]:
        rule_object: list[Rule] = db.scalars(select(Rule)).all()
        return [
            RuleData(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                expression=rule.expression,
                priority=rule.priority
            ) for rule in rule_object
        ]