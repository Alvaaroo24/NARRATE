import json
import uuid
from typing import Optional, Dict, Any, Union, List
from langchain_core.tools import Tool, StructuredTool
from langchain_core.messages import HumanMessage, AIMessage

from pydantic import BaseModel, Field

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


class APISchema(BaseModel):
    method: str = Field(
        ..., description="The exact HTTP method (GET, POST, PUT, DELETE)."
    )
    url: str = Field(
        ...,
        description="The relative PATH or full URL (e.g., '/products' or '/users/123').",
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Dictionary of Query Params."
    )
    body: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None, description="Dictionary or List for the JSON Body."
    )


class AgentInput(BaseModel):
    instructions: str = Field(
        ...,
        description=(
            "EXACT instruction for the sub-agent. "
            "RULE: If you are executing a plan retrieved from memory, "
            "YOU ARE FORBIDDEN to summarize or paraphrase. Send clear, natural language instructions containing the logical action and the strictly required technical IDs or parameters. DO NOT send HTTP methods or URLs. "
        ),
    )


def create_specialized_agent_tool(
    llm, api_tool: Tool, name: str, title: str, internal_doc: str, description: str
) -> Tool:
    """
    Creates a Sub-agent using create_react_agent, optimized to avoid Rate Limits (429).
    """

    def tools_wrapper(
        method: str, url: str, params: dict = None, body: dict = None
    ) -> str:
        payload = {"method": method, "url": url, "params": params, "body": body}
        return api_tool.func(json.dumps(payload))

    structured_api_tool = StructuredTool.from_function(
        func=tools_wrapper,
        name=api_tool.name,
        description=api_tool.description,
        args_schema=APISchema,
    )

    tools = [structured_api_tool]

    system_prompt_content = f"""You are the Specialist Agent in: {title}.
    Your internal ID is: {name}.

    --- GOLDEN RULE: THINK BEFORE ACTING ---
    1. Read the instruction from the Orchestrator.
    2. Consult your API MANUAL to find the correct endpoint.
    3. Generate the call to the 'APISchema' tool.

    --- API MANUAL (CHEAT SHEET) ---
    {internal_doc}

    ======================================================================
    FEW-SHOT EXAMPLES: TRANSLATING INSTRUCTIONS TO API CALLS
    ======================================================================
    Observe how to translate Orchestrator instructions into tool calls based on your manual:

    Example 1: Single ID Processing
    Orchestrator Instruction: "Simulate risk for the supplier ID: CS_005."
    Thought: I need to simulate risk for ID CS_005. Looking at my manual, the endpoint is POST /api/provider/{{id_input}}/simulate-risk. I will substitute {{id_input}} with CS_005.
    Tool Call: APISchema(method="POST", url="/api/provider/CS_005/simulate-risk", params=None, body={{}})

    Example 2: Parallel Batch Processing
    Orchestrator Instruction: "Check the status for the following product IDs simultaneously: PROD_01, PROD_02"
    Thought: I have two IDs. The manual says the status endpoint is GET /api/v1/products/{{id}}/status. I must execute parallel tool calls, one for each ID.
    Tool Call 1: APISchema(method="GET", url="/api/v1/products/PROD_01/status", params=None, body=None)
    Tool Call 2: APISchema(method="GET", url="/api/v1/products/PROD_02/status", params=None, body=None)

    Example 3: Missing ID Fallback
    Orchestrator Instruction: "Get data for the company 'TechCorp'."
    Thought: The instruction provides a Name ('TechCorp'), but my manual requires an ID for all endpoints. I cannot invent a route.
    Response: "MISSING ID. I do not have a search endpoint by name. ORCHESTRATOR: Use another agent to map this name to its ID and call me back."
    """

    checkpointer = MemorySaver()

    sub_agent_graph = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        prompt=system_prompt_content,
    )

    def run_sub_agent(instructions: str) -> str:
        try:
            ephemeral_thread_id = str(uuid.uuid4())
            config = {
                "configurable": {"thread_id": ephemeral_thread_id},
                "recursion_limit": 15,
            }

            inputs = {"messages": [HumanMessage(content=instructions)]}
            result = sub_agent_graph.invoke(inputs, config=config)

            last_message = result["messages"][-1]
            content_response = last_message.content

            executed_trace = []
            for m in result["messages"]:
                if (
                    isinstance(m, AIMessage)
                    and hasattr(m, "tool_calls")
                    and m.tool_calls
                ):
                    for tc in m.tool_calls:
                        args = tc.get("args", {})
                        method = args.get("method", "GET")
                        url = args.get("url", "")
                        if url:
                            executed_trace.append(f"{method} {url}")

            unique_trace = list(dict.fromkeys(executed_trace))

            if unique_trace:
                technical_footer = (
                    "\n\n--- [SYSTEM META: EXECUTED ENDPOINTS] ---\n"
                    + "\n".join(unique_trace)
                )
                return content_response + technical_footer

            return content_response

        except Exception as e:
            if "RecursionLimit" in str(e):
                return f"Task too complex (Limit Reached). Partial data."
            return f"Error in agent {name}: {str(e)}"

    return StructuredTool.from_function(
        func=run_sub_agent,
        name=f"agent_{name}",
        description=f"Use this agent to consult: {description}. Pass the exact instruction.",
        args_schema=AgentInput,
    )
