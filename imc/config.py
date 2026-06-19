from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings:
    encrypt_secret_key: str = os.getenv("ENCRYPT_SECRET_KEY", "")
    max_retries_parser_error_func_call: int = int(
        os.getenv("MAX_RETRIES_PARSER_ERROR_FUNC_CALL", 5)
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_base_url: str = os.getenv("AZURE_OPENAI_BASE_URL", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "")
    azure_openai_model_deployment_name: str = os.getenv(
        "AZURE_OPENAI_MODEL_DEPLOYMENT_NAME", ""
    )
    azure_openai_embedding_model_deployment_name: str = os.getenv(
        "AZURE_OPENAI_EMBEDDING_MODEL_DEPLOYMENT_NAME", ""
    )

    # --- AÑADIDO PARA SOLUCIONAR LA BASE DE DATOS ---
    # 1. Leemos la URL del .env (para el motor síncrono)
    postgres_url: str = os.getenv(
        "POSTGRES_URL",
        "postgresql://imc_user:imc_password@host.docker.internal:5432/imc_db",
    )

    # 2. Creamos la URL asíncrona inyectando asyncpg automáticamente (para el motor asíncrono)
    database_url: str = postgres_url.replace("postgresql://", "postgresql+asyncpg://")


# Instanciamos la clase para que el resto de la app pueda importarla
settings = Settings()
