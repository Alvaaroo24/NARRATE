from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import List

from imc.modules.agents.tools.registry import get_initial_tools, _APP_STATE


def initialize_agent(llm, tools_override: List = None, system_instructions: str = None):
    """
    Initialize the standard Agent.
    """
    if tools_override:
        tools = tools_override
    else:
        tools = get_initial_tools() + _APP_STATE.get("dynamic_tools", [])

    checkpointer = MemorySaver()

    agent_graph = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        prompt=system_instructions,
    )

    return agent_graph, None
