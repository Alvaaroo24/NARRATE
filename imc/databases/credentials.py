import sqlite3
import json
import os
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from langchain_openai import AzureOpenAIEmbeddings
from imc.config import settings
import chromadb


# Obtenemos la ruta absoluta de la carpeta donde está este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Unimos esa ruta con el nombre del archivo
API_DB_NAME = os.path.join(BASE_DIR, "api_keys.db")


def init_api_db():
    """Inicializa solo la tabla de credenciales en api_key.db"""
    conn = sqlite3.connect(API_DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_credentials (
            service_name TEXT PRIMARY KEY,
            key_value TEXT NOT NULL,
            header_name TEXT DEFAULT 'apikey'
        )
    """)
    conn.commit()
    conn.close()


def add_credential(service_name, key_value, header_name="apikey"):
    """Guarda una credencial en api_key.db"""
    init_api_db()  # Asegura que la tabla exista
    conn = sqlite3.connect(API_DB_NAME)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT OR REPLACE INTO api_credentials (service_name, key_value, header_name)
            VALUES (?, ?, ?)
            """,
            (service_name, key_value, header_name),
        )
        conn.commit()
        print(
            f"✅ Credencial para '{service_name}' guardada/actualizada en {API_DB_NAME}."
        )
    except Exception as e:
        print(f"❌ Error al guardar credencial: {e}")
    finally:
        conn.close()


def get_all_credentials():
    """Lee las credenciales desde api_key.db"""
    init_api_db()
    conn = sqlite3.connect(API_DB_NAME)
    c = conn.cursor()
    c.execute("SELECT service_name, key_value, header_name FROM api_credentials")
    rows = c.fetchall()
    conn.close()

    auth_store = {}
    for service, value, header in rows:
        clean_name = service.lower().strip()
        auth_store[clean_name] = {"value": value, "header": header}

    return auth_store
