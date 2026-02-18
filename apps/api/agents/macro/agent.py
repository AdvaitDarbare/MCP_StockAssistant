from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from apps.api.config import settings
from apps.api.agents.macro.tools import macro_tools
from apps.api.agents.content_utils import normalize_content_to_text
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries

MACRO_PROMPT = """You are an expert Macroeconomist Agent.
Your goal is to provide data-driven analysis of economic conditions and their impact on financial markets.

You have access to the FRED (Federal Reserve Economic Data) database.

When analyzing:
1.  **Context**: Always consider the current economic cycle (e.g., expansion, recession, inflation).
2.  **Data-Backed**: Use specific data points (e.g., "CPI is 3.2%", "Unemployment is 4.1%").
3.  **Impact**: Explain how these factors influence asset classes (stocks, bonds, sectors).
    - Rising rates -> Negative for growth stocks, positive for banks (usually).
    - High inflation -> Negative for consumer discretionary.
4.  **Trends**: Look at unexpected changes or trends, not just the latest number.

Use `get_macro_summary` for a quick overview.
Use `get_economic_series` for deep dives into specific indicators (e.g., `DGS10` for 10Y Yield).
Use `search_economic_data` to find specialized datasets (e.g., "housing starts").

Synthesize your findings into a clear, concise summary."""

async def macro_node(state):
    """
    The Macro Agent node.
    """
    model = ChatAnthropic(
        model=settings.ANALYSIS_MODEL,
        api_key=settings.ANTHROPIC_API_KEY
    )
    
    agent = create_react_agent(model, macro_tools, prompt=MACRO_PROMPT)
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["macro"],
    )
    query = merge_queries(ready_tasks, prefix="Run these macro analysis requests")
    if not query:
        messages = state.get("messages", [])
        if messages:
            query = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        else:
            query = ""

    result = await agent.ainvoke({"messages": [("user", query)]})
    
    # Extract the last message content
    last_message = result["messages"][-1]
    
    for task in ready_tasks:
        task_status_updates[task.task_id] = "completed"

    return {
        "agent_results": {
            "macro": {
                "agent": "macro",
                "content": normalize_content_to_text(last_message.content),
                "symbols": [],
                "data": {},
                "error": None
            }
        },
        "task_status": task_status_updates,
    }
