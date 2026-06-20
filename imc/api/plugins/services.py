import logging
from fastapi import HTTPException, status
import psycopg2
from sqlalchemy.orm import Session

from imc.databases.postgres.models_sqlalchemy import Plugin
from imc.api.plugins.models import PluginCreate


def get_plugin_catalog(db: Session):
    """
    Returns the plugins catalog using only the fields available in the shared DB.
    """
    try:
        plugins = db.query(Plugin).all()

        plugin_list = []
        for plugin in plugins:
            plugin_dict = {
                "id": plugin.id,
                "name": plugin.name,
                "description": plugin.description,
                "base_url": plugin.base_url,
                "openapi_url": plugin.openapi_url,
                "active": plugin.active,
            }
            plugin_list.append(plugin_dict)

    except (Exception, psycopg2.Error) as e:
        logging.exception(e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while searching plugin catalog",
        )

    if not plugin_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No plugins found",
        )

    return plugin_list


def save_plugin_to_db(db: Session, plugin_data: PluginCreate):
    """
    Función para que el Orchestrator o cualquier agente guarde un nuevo plugin.
    Aparecerá automáticamente en el Monitoring Platform.
    Si el plugin ya existe, actualiza sus datos en lugar de fallar.
    """
    try:
        existing_plugin = (
            db.query(Plugin).filter(Plugin.name == plugin_data.name).first()
        )

        if existing_plugin:
            existing_plugin.description = plugin_data.description
            existing_plugin.base_url = plugin_data.base_url
            existing_plugin.openapi_url = plugin_data.openapi_url
            existing_plugin.active = plugin_data.active

            db.commit()
            db.refresh(existing_plugin)
            return existing_plugin

        new_plugin = Plugin(
            name=plugin_data.name,
            description=plugin_data.description,
            base_url=plugin_data.base_url,
            openapi_url=plugin_data.openapi_url,
            active=plugin_data.active,
        )
        db.add(new_plugin)
        db.commit()
        db.refresh(new_plugin)
        return new_plugin

    except Exception as e:
        logging.exception(f"Error saving plugin to DB: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while saving the plugin",
        )


def delete_plugin_from_db(db: Session, plugin_name: str):
    """
    Función para que un agente elimine un plugin usando su nombre.
    """
    try:
        plugin = db.query(Plugin).filter(Plugin.name == plugin_name).first()
        if not plugin:
            return False

        db.delete(plugin)
        db.commit()
        return True

    except Exception as e:
        logging.exception(f"Error deleting plugin from DB: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error while deleting the plugin",
        )
