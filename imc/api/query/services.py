
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from imc.api.query.models import QueryInput
from imc.modules.agents.utils.models import QueryResponse
from imc.modules.events.events import get_event_from_query
from imc.modules.data_managers import (
    ChatManager,
    PlanManager,
    RulesManager,
    PluginManager,
    RiskTypeManager,
    EventManager
)
from imc.modules.agents.orchestrator.module import OrchestratorAgent


async def query(query_input: QueryInput, db: Session) -> QueryResponse:
    """
    """
    event = get_event_from_query(query_input)

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
        event_manager=event_manager
    )

    response = await orchestrator_agent.get_response(event, db)

    return response
