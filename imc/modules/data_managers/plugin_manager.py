from abc import ABC, abstractmethod
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.databases.postgres.models_sqlalchemy import Plugin
from imc.api.plugins.models import PluginInfo


class PluginManagerBase(ABC):
    @abstractmethod
    async def get_plugins(self, db: Session) -> list[PluginInfo]:
        pass


class PluginManager(PluginManagerBase):
    async def get_plugins(self, db: Session) -> list[PluginInfo]:
        plugin_object: list[Plugin] = db.scalars(select(Plugin)).all()
        return [
            PluginInfo(     
                id=plugin.id,
                url=plugin.base_url,
                title=plugin.name,
                description=plugin.description,
                schema_url=plugin.openapi_url,
            ) for plugin in plugin_object
        ]