import json
import asyncio
import paho.mqtt.client as mqtt

from imc.messaging.handlers import process_message
from imc.databases.postgres.database import SessionLocal
from imc.modules.events.models import MessageModel
import os
from dotenv import load_dotenv

load_dotenv()

BROKER_URL = os.getenv("MQTT_BROKER", "events.bluebridgesolutions.de")
BROKER_PORT = int(os.getenv("MQTT_PORT", 80))
BROKER_PATH = os.getenv("MQTT_PATH", "/ws")
TOPIC_IN = os.getenv("MQTT_TOPIC_ALERT", "narrate/alert")
TOPIC_OUT = os.getenv("MQTT_TOPIC_RESPONSE", "narrate/response")
TOPIC_GAS = os.getenv("MQTT_TOPIC_GAS", "narrate/gasLevel")
USERNAME = os.getenv("MQTT_USERNAME", "narrate")
PASSWORD = os.getenv("MQTT_PASSWORD", "narrate")


def on_message(client, userdata, msg):
    """Handle incoming MQTT messages from the alert topic."""
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[IMC] Alert received: {payload}")
    except json.JSONDecodeError:
        print("[IMC] Received invalid JSON")
        return

    db = SessionLocal()
    try:
        message_model = MessageModel(**payload)
        ai_result = asyncio.run(process_message(message_model, db))
        print(f"[IMC] AI Response: {ai_result}")

        client.publish(TOPIC_OUT, json.dumps(ai_result))

    except Exception as e:
        print(f"[IMC] Error processing message: {e}")

    finally:
        db.close()


def on_connect(client, userdata, flags, rc):
    """Trigger when MQTT connection is established."""
    print(f"[IMC] Connected (rc={rc})")
    client.subscribe([(TOPIC_IN, 0), (TOPIC_GAS, 0)])
    print(f"[IMC] Subscribed to {TOPIC_IN}")


def start_consumer():
    """Start the MQTT consumer with websocket transport."""
    try:
        client = mqtt.Client(transport="websockets")
        client.enable_logger()
        client.username_pw_set(USERNAME, PASSWORD)
        client.ws_set_options(path=BROKER_PATH)

        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(BROKER_URL, BROKER_PORT, keepalive=60)

        print("[IMC] MQTT consumer started")
        client.loop_start()

    except Exception as e:
        print(f"[IMC] MQTT Connection Error: {e}")
