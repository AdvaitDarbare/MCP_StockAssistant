import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from apps.api.config import settings
from apps.api.agents.content_utils import normalize_content_to_text
from apps.api.agents.supervisor.state import SupervisorState
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries
from apps.api.agents.technical_analysis.tools import calculate_sma_tool, calculate_rsi_tool, calculate_macd_tool

# Define tools
tools = [calculate_sma_tool, calculate_rsi_tool, calculate_macd_tool]

# Initialize LLM with tools
llm = ChatAnthropic(model=settings.DEFAULT_MODEL, api_key=settings.ANTHROPIC_API_KEY)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a Technical Analysis Specialist.
Your job is to analyze stock market data using technical indicators like SMA, RSI, and MACD.
Use the provided tools to calculate these indicators and provide a summary of the technical outlook.
Do not make up data. Always use the tools."""

async def technical_analysis_node(state: SupervisorState) -> dict:
    """Executes the Technical Analysis Agent."""
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["technical_analysis", "technicals"],
    )
    agent_query = merge_queries(ready_tasks, prefix="Run these technical analysis requests")
    if not agent_query:
        agent_query = state["messages"][-1].content

    # Check for dependency data (Market Data)
    market_data_context = ""
    market_data_raw: list[dict] | None = None
    agent_results = state.get("agent_results", {})
    if "market_data" in agent_results:
        md_result = agent_results["market_data"]
        if md_result.get("data"):
            md_data = md_result["data"]
            market_data_raw = _extract_price_data(md_data, agent_query)
            market_data_context = (
                "\n\nAVAILABLE MARKET DATA:\n"
                f"{market_data_raw}\n\n"
                "IMPORTANT: When calling technical tools, YOU MUST pass the 'price_data' argument using the data above."
            )

    # Execute agent logic
    response = await llm_with_tools.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT + market_data_context),
        HumanMessage(content=agent_query)
    ])
    
    result_content = response.content
    tool_data = None
    
    execution_error = None
    if response.tool_calls:
        # Execute tools manually for this simple node
        # We'll execute the first tool call for simplicity in V1
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = dict(tool_call.get("args") or {})
        
        selected_tool = next((t for t in tools if t.name == tool_name), None)
        if selected_tool:
            if isinstance(market_data_raw, list):
                tool_args["price_data"] = market_data_raw

            try:
                tool_result = selected_tool.invoke(tool_args)
                tool_data = tool_result

                # Re-invoke LLM with tool result to get final answer
                final_response = await llm_with_tools.ainvoke([
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=agent_query),
                    response,
                    ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=str(tool_result),
                        name=tool_name
                    )
                ])
                result_content = final_response.content
            except Exception as exc:
                execution_error = str(exc)
                result_content = (
                    "I could not complete technical indicator calculations from the available price payload. "
                    f"Error: {execution_error}"
                )

    task_state = "failed" if execution_error else "completed"
    for task in ready_tasks:
        task_status_updates[task.task_id] = task_state

    return {
        "agent_results": {
            "technical_analysis": {
                "agent": "technical_analysis",
                "content": normalize_content_to_text(result_content),
                "symbols": [],
                "data": tool_data,
                "error": execution_error,
            }
        },
        "task_status": task_status_updates,
    }


def _extract_price_data(md_data, query: str) -> list[dict]:
    if isinstance(md_data, list):
        return [row for row in md_data if isinstance(row, dict)]

    if not isinstance(md_data, dict):
        return []

    raw = md_data.get("raw")
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]

    output = md_data.get("output")
    if isinstance(output, list):
        return [row for row in output if isinstance(row, dict)]

    history_by_symbol = md_data.get("history_by_symbol")
    target_symbol = _extract_first_symbol(query)
    if isinstance(history_by_symbol, dict):
        if target_symbol and isinstance(history_by_symbol.get(target_symbol), list):
            return [row for row in history_by_symbol[target_symbol] if isinstance(row, dict)]
        for rows in history_by_symbol.values():
            if isinstance(rows, list) and rows:
                return [row for row in rows if isinstance(row, dict)]

    tool_results = md_data.get("tool_results")
    if isinstance(tool_results, list):
        for payload in tool_results:
            if not isinstance(payload, dict):
                continue
            if str(payload.get("tool", "")).strip() != "get_historical_prices":
                continue
            out = payload.get("output")
            if isinstance(out, list):
                if not target_symbol:
                    return [row for row in out if isinstance(row, dict)]
                filtered = [
                    row for row in out
                    if isinstance(row, dict) and str(row.get("symbol", "")).upper() == target_symbol
                ]
                if filtered:
                    return filtered
                return [row for row in out if isinstance(row, dict)]

    return []


def _extract_first_symbol(text: str) -> str:
    matches = re.findall(r"\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b", text or "")
    stop_words = {"RSI", "MACD", "SMA", "EMA", "VWAP", "AND", "THE"}
    for pair in matches:
        token = (pair[0] or pair[1] or "").upper().strip()
        if token and token not in stop_words:
            return token
    return ""
