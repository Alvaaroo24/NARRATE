import os
from dotenv import load_dotenv

load_dotenv("./.env")

from contextlib import asynccontextmanager
from imc.databases.chroma_mock.mock_vector_db import create_chroma_db_from_txt
import logging
import sys


# --- FIX: Attach a console handler and set proper level ---
root = logging.getLogger()
if not root.handlers:
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)

root.setLevel(logging.DEBUG)  # show all messages
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)

print(">>> logging fixed: root.handlers =", root.handlers)
# from dotenv import load_dotenv
# DOTENV_FILE = f"../.env"
# DOTENV_LOADED = load_dotenv(DOTENV_FILE)
from fastapi import FastAPI

import imc.api.plugins.routes as plugin_routes
import imc.api.query.routes as query_routes
import imc.api.chat.routes as chat_routes

# from imc.databases.postgres.database_async import async_session_manager
from imc.fastapi.server import create_app
from imc.fastapi.exception_handlers import register_exception_handlers

# Initialize the database session manager for async operations
# INIT_ASYNC_DB = os.getenv("INIT_DB", "False").lower() in ("true", "1", "t")

# if INIT_ASYNC_DB:  # disable for testing
#     database_name = os.getenv("POSTGRES_BDNAME")
#     database_user = os.getenv("POSTGRES_USER")
#     database_password = os.getenv("POSTGRES_PASSWORD")
#     database_host = os.getenv("POSTGRES_HOST")
#     database_port = os.getenv("POSTGRES_PORT")
#     SQLALCHEMY_DATABASE_URI_ASYNC = f"postgresql+asyncpg://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"
#     if SQLALCHEMY_DATABASE_URI_ASYNC is None:
#         raise RuntimeError("SQLALCHEMY_DATABASE_URI_ASYNC is not set")
#     else:
#         async_session_manager.init(host=SQLALCHEMY_DATABASE_URI_ASYNC)

# # Initialize kafka document client
# INIT_KAFKA = True

# try:
#     document_client = DocumentClient()
# except RuntimeError as e:
#     logger.error(e)
#     INIT_KAFKA = False

# Set app lifespan events
# @asynccontextmanager
# async def lifespan(app: FastAPI):
# # Startup events - start document client threads
# if INIT_KAFKA:
#     document_client.start()
# # create_collection_if_not_exist()
# yield
# # Shutdown events - close document client threads and database connection pool
# if INIT_KAFKA:
#     document_client.close()
# if INIT_ASYNC_DB and async_session_manager._engine is not None:
#     await async_session_manager.close()
# pass


from threading import Thread
from imc.messaging.consumer import start_consumer


def start_messaging_consumer():
    t = Thread(target=start_consumer, daemon=True)
    t.start()
    print(">>> [IMC] MQTT Consumer started in background thread.")


start_messaging_consumer()

app = create_app()
app.include_router(plugin_routes.router)
app.include_router(query_routes.router)
app.include_router(chat_routes.router)  # estaba comentada

create_chroma_db_from_txt("imc/databases/chroma_mock/mock_data.txt")


register_exception_handlers(app)

if __name__ == "__main__":
    # Run the FastAPI application
    import uvicorn

    # This shoud allways be executed inside a docker container
    # so host 0.0.0.0 is the correct one. We disable the bandit error
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="debug")
