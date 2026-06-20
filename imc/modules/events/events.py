from imc.modules.events.models import EventModel, MessageModel
from imc.api.query.models import QueryInput


def get_event_from_query(query_input: QueryInput) -> EventModel:
    event_type = "chat_query"
    event_model = EventModel(
        chat_id=query_input.chat_id,
        user_id=query_input.user_id,
        query=query_input.query,
        event_type=event_type,
    )
    return event_model


def get_event_from_message(message: MessageModel) -> EventModel:
    """Construye el EventModel procesando campos específicos según el event_type,
    conservando todo el payload de MQTT."""

    if message.event_type == "argonGasLevel":
        query_text = (
            f"Argon Gas Level Alert - R1: {message.register1}, "
            f"R2: {message.register2}, R3: {message.register3}"
        )
    else:
        query_text = message.alert if message.alert else "Unspecified Sensor Alert"

    event_data = message.model_dump()

    event_data["query"] = query_text
    event_data["chat_id"] = None
    event_data["user_id"] = None

    event_model = EventModel(**event_data)

    return event_model
