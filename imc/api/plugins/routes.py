from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from imc.api.plugins import services
from imc.api.plugins.models import PluginCatalogResponse
from imc.databases.postgres.database import get_db


router = APIRouter(
    prefix="/plugin",
    tags=["plugin"],  # dependencies=[Depends(get_current_active_user)]
)


@router.get("", response_model=PluginCatalogResponse)
def get_plugin_catalog(db: Session = Depends(get_db)):
    """ """
    plugins = services.get_plugin_catalog(db)
    return PluginCatalogResponse(plugins=plugins)
