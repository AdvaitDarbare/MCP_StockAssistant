import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from apps.api.config import settings
from apps.api.agents.content_utils import normalize_content_to_text
from apps.api.agents.supervisor.state import SupervisorState
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries
from apps.api.agents.market_data.tools import (
    get_quote,
    get_historical_prices,
    get_company_profile,
    get_market_movers,
    get_stock_news,
    get_market_hours,
)
from apps.api.services.tool_contracts import (
    build_structured_tool_payload,
    render_structured_market_tool_payload,
)

SYSTEM_PROMPT = """You are the Market Data Agent.
Your role is to provide real-time and historical financial data, market news, and top movers.
You have access to tools for retrieving stock quotes, history, profiles, top gainers/losers, and stock-specific news.

Use the tools provided to answer the user's specific query.
Return your answer in a clear, concise format.
If you use a tool, summarize the data returned by the tool.
"""

tools = [get_quote, get_historical_prices, get_company_profile, get_market_movers, get_stock_news, get_market_hours]
llm = ChatAnthropic(model=settings.DEFAULT_MODEL, api_key=settings.ANTHROPIC_API_KEY)
llm_with_tools = llm.bind_tools(tools)

async def market_data_node(state: SupervisorState) -> dict:
    """Market Data Agent node execution."""
    # Extract the query relevant to this agent
    # In a real scenario, the router/planner might pass specific args.
    # For now, we use the last user message or the planned query.
    
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["market_data"],
    )
    agent_query = merge_queries(ready_tasks, prefix="Run these market data requests")
    
    if not agent_query:
        # Fallback to last user message
        messages = state.get("messages", [])
        if messages:
            agent_query = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        else:
            return {"agent_results": {"market_data": {"agent": "market_data", "error": "No query found"}}}

    deterministic = await _run_multi_symbol_history_compare(agent_query)
    if deterministic is not None:
        for task in ready_tasks:
            task_status_updates[task.task_id] = "completed"
        return {
            "agent_results": {
                "market_data": {
                    "agent": "market_data",
                    "content": deterministic["content"],
                    "symbols": deterministic["symbols"],
                    "data": deterministic["data"],
                    "error": None,
                }
            },
            "task_status": task_status_updates,
        }

    # Execute agent logic
    response = await llm_with_tools.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=agent_query)
    ])
    
    # Handle tool calls if any
    result_content = normalize_content_to_text(response.content)
    tool_data = None
    tool_symbols: list[str] = []
    
    if response.tool_calls:
        rendered_chunks: list[str] = []
        structured_results: list[dict] = []
        for tool_call in response.tool_calls[:6]:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args") or {}
            if not tool_name:
                continue

            selected_tool = next((t for t in tools if t.name == tool_name), None)
            if selected_tool is None:
                continue

            raw_tool_result = await selected_tool.ainvoke(tool_args)
            payload = build_structured_tool_payload(
                tool_name=tool_name,
                tool_input=tool_args,
                raw_output=raw_tool_result,
            )
            structured_results.append(payload)
            rendered_chunks.append(render_structured_market_tool_payload(payload))

            symbol = str((tool_args or {}).get("symbol", "")).upper().strip()
            if symbol and symbol not in tool_symbols:
                tool_symbols.append(symbol)

        if rendered_chunks:
            result_content = "\n\n".join(chunk for chunk in rendered_chunks if chunk)
            tool_data = {"tool_results": structured_results}
    
    status_value = "failed" if tool_data is None and not result_content else "completed"
    for task in ready_tasks:
        task_status_updates[task.task_id] = status_value

    return {
        "agent_results": {
            "market_data": {
                "agent": "market_data",
                "content": normalize_content_to_text(result_content),
                "symbols": tool_symbols,
                "data": tool_data,
                "error": None,
            }
        },
        "task_status": task_status_updates,
    }


async def _run_multi_symbol_history_compare(query: str) -> dict | None:
    if not _looks_like_history_request(query):
        return None

    symbols = _extract_symbols(query)
    if len(symbols) < 2:
        return None

    days = _extract_days(query)
    history_by_symbol: dict[str, list[dict]] = {}
    tool_results: list[dict] = []
    for symbol in symbols[:4]:
        rows = await get_historical_prices.ainvoke({"symbol": symbol, "days": days})
        row_list = [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        history_by_symbol[symbol] = row_list
        tool_results.append(
            build_structured_tool_payload(
                tool_name="get_historical_prices",
                tool_input={"symbol": symbol, "days": days},
                raw_output=row_list,
            )
        )

    if not any(history_by_symbol.values()):
        return None

    return {
        "content": _format_multi_symbol_history_output(history_by_symbol, days),
        "symbols": list(history_by_symbol.keys()),
        "data": {
            "tool_results": tool_results,
            "history_by_symbol": history_by_symbol,
            "days": days,
        },
    }


def _looks_like_history_request(query: str) -> bool:
    text = (query or "").lower()
    history_terms = ("price", "close", "history", "last", "past", "days", "trading days")
    compare_terms = ("compare", "vs", "versus", "both")
    return any(term in text for term in history_terms) and any(term in text for term in compare_terms)


def _extract_days(query: str) -> int:
    text = (query or "").lower()
    match = re.search(r"(?:last|past)\s+(\d{1,3})\s+day", text)
    if match:
        return max(2, min(90, int(match.group(1))))
    if "week" in text:
        return 7
    return 5


def _extract_symbols(text: str) -> list[str]:
    alias_map = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "rivian": "RIVN",
        "amazon": "AMZN",
        "alphabet": "GOOGL",
        "google": "GOOGL",
        "meta": "META",
    }
    lowered = (text or "").lower()

    symbols: list[str] = []
    for name, ticker in alias_map.items():
        if name in lowered and ticker not in symbols:
            symbols.append(ticker)

    ticker_candidates = re.findall(r"\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b", text or "")
    stop_words = {"THE", "AND", "FOR", "WITH", "PRICE", "LAST", "PAST", "DAYS", "BOTH", "VS", "USD"}
    for pair in ticker_candidates:
        token = (pair[0] or pair[1] or "").upper().strip()
        if not token or token in stop_words:
            continue
        if token not in symbols:
            symbols.append(token)
    return symbols


def _format_multi_symbol_history_output(history_by_symbol: dict[str, list[dict]], days: int) -> str:
    symbols = list(history_by_symbol.keys())
    rows_by_date: dict[str, dict[str, float]] = {}
    for symbol, rows in history_by_symbol.items():
        for row in rows:
            date_val = str(row.get("date", "")).strip()
            close_val = row.get("close")
            if not date_val or not isinstance(close_val, (int, float)):
                continue
            date_bucket = rows_by_date.setdefault(date_val, {})
            date_bucket[symbol] = float(close_val)

    ordered_dates = sorted(rows_by_date.keys())[-days:]
    header = "| Date | " + " | ".join(symbols) + " |"
    separator = "|" + "---|" * (len(symbols) + 1)
    table_lines = [header, separator]
    for date_val in ordered_dates:
        values = []
        for symbol in symbols:
            close = rows_by_date.get(date_val, {}).get(symbol)
            values.append(f"{close:.2f}" if isinstance(close, (int, float)) else "—")
        table_lines.append(f"| {date_val} | " + " | ".join(values) + " |")

    summary_lines: list[str] = []
    for symbol in symbols:
        rows = [r for r in history_by_symbol.get(symbol, []) if isinstance(r.get("close"), (int, float))]
        if len(rows) < 2:
            summary_lines.append(f"- {symbol}: insufficient recent rows returned.")
            continue
        window = rows[-days:] if len(rows) >= days else rows
        start = window[0]
        end = window[-1]
        start_close = float(start.get("close"))
        end_close = float(end.get("close"))
        pct = ((end_close - start_close) / start_close * 100.0) if start_close else 0.0
        summary_lines.append(
            f"- {symbol}: {str(start.get('date', ''))[:10]} ${start_close:.2f} -> "
            f"{str(end.get('date', ''))[:10]} ${end_close:.2f} ({pct:+.1f}%)."
        )

    lead = f"Here are the latest {days} trading-day closes for {', '.join(symbols)}."
    return "\n".join([lead, "", *summary_lines, "", *table_lines]).strip()
