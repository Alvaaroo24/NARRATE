# admin_load_keys.py
import sqlite3
import os

# Obtenemos la ruta absoluta de la carpeta donde está este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Unimos esa ruta con el nombre del archivo
API_DB_NAME = os.path.join(BASE_DIR, "api_keys.db")

import logging


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


def load_all_keys():
    print("--- 🛠️ Cargando Credenciales en SQLite (api_keys.db) ---")

    # 1. Aseguramos que la tabla exista
    init_api_db()  #

    # 2. Definimos las claves basadas en tu configuración de Kong
    # risk usa la clave del grupo A
    # blueprint y gmao comparten la clave del grupo BC
    credentials = [
        {"service": "risk", "key": "user-a-key"},
        {"service": "blueprint", "key": "user-bc-key"},
        {
            "service": "monsta",
            "key": "user-a-key",
        },  # <--- AÑADIDO PARA MONSTA        # (Puedes dejar gmao y narrate si los vas a usar en el futuro)
    ]

    for cred in credentials:
        try:
            # La función add_credential realiza un 'INSERT OR REPLACE'
            add_credential(
                service_name=cred["service"],
                key_value=cred["key"],
                header_name="apikey",
            )
            print(f"✅ Credencial guardada para: {cred['service']}")
        except Exception as e:
            print(f"❌ Error al guardar {cred['service']}: {e}")

    print("🚀 ¡Proceso finalizado! Las claves están listas en api_keys.db.")


if __name__ == "__main__":
    load_all_keys()
