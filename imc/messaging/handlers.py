from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

import imc.api.chat.services as services
from imc.modules.events.events import get_event_from_message, get_event_from_query
from imc.modules.data_managers.chat_manager import ChatManager
from imc.modules.data_managers.plan_manager import PlanManager
from imc.modules.data_managers.rules_manager import RulesManager
from imc.modules.data_managers.plugin_manager import PluginManager
from imc.modules.agents.orchestrator.module import OrchestratorAgent
from imc.modules.data_managers.risk_type_manager import RiskTypeManager
from imc.modules.data_managers.event_manager import EventManager

from imc.modules.events.models import MessageModel


async def process_message(msg, db: Session):
    """ """
    event = get_event_from_message(msg)

    chat_manager = ChatManager()
    plan_manager = PlanManager()
    rules_manager = RulesManager()
    plugin_manager = PluginManager()
    risk_type_manager = RiskTypeManager()
    event_manager = EventManager()

    orchestrator_agent = OrchestratorAgent(
        chat_manager=chat_manager,
        plan_manager=plan_manager,
        rules_manager=rules_manager,
        plugin_manager=plugin_manager,
        risk_type_manager=risk_type_manager,
        event_manager=event_manager,
    )
    return await orchestrator_agent.get_response(event, db)
