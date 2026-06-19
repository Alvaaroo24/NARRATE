# Standard imports
from typing import Any, Optional

# Third party imports
from pydantic import BaseModel


class PluginCatalogResponse(BaseModel):
    """Pydantic model that represents the standard response structure for the plugin catalog process"""

    plugins: list[Any]


class PluginInfo(BaseModel):
    """Modelo adaptado a models_sqlalchemy.py"""

    id: int
    name: str
    description: str
    base_url: Optional[str] = None
    openapi_url: Optional[str] = None
    active: bool = True


class PluginCreate(BaseModel):
    """Modelo para que el sistema multi-agente pueda crear plugins nuevos"""

    name: str
    description: str
    base_url: Optional[str] = None
    openapi_url: Optional[str] = None
    active: bool = True
