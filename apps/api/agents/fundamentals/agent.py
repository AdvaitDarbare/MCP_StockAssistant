"""Fundamental Analysis Agent — company research, analyst ratings, insider trades, news."""

import json
import logging
import re

import anthropic

from apps.api.config import settings
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries
from apps.api.services import finviz_client
from apps.api.services.tool_contracts import build_structured_tool_payload

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


TOOLS = [
    {
        "name": "get_company_overview",
        "description": "Get company fundamentals: sector, market cap, P/E, revenue, margins, employees, etc.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "get_analyst_ratings",
        "description": "Get analyst ratings, price targets, and recommendation changes.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
    {
        "name": "get_insider_trades",
        "description": "Get insider trading activity — officer and director buys/sells.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_company_news",
        "description": "Get recent news articles about a company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["symbol"],
        },
    },
]


async def execute(query: str) -> dict:
    """Execute fundamental analysis for the given query."""
    client = _get_client()

    try:
        response = await client.messages.create(
            model=settings.ROUTING_MODEL,
            max_tokens=1500,
            system="You are a fundamental analysis specialist. Use the tools to research companies. Focus on key financial metrics, analyst opinions, and insider activity.",
            tools=TOOLS,
            messages=[{"role": "user", "content": query}],
        )

        results = []
        symbols = []

        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                sym = tool_input.get("symbol", "")
                if sym:
                    symbols.append(sym)

                if tool_name == "get_company_overview":
                    data = await finviz_client.get_company_overview(sym)
                    results.append(
                        {
                            "tool": tool_name,
                            "symbol": sym,
                            "data": data,
                            "structured": build_structured_tool_payload(tool_name, {"symbol": sym}, data),
                        }
                    )

                elif tool_name == "get_analyst_ratings":
                    data = await finviz_client.get_analyst_ratings(sym)
                    results.append(
                        {
                            "tool": tool_name,
                            "symbol": sym,
                            "data": data,
                            "structured": build_structured_tool_payload(tool_name, {"symbol": sym}, data),
                        }
                    )

                elif tool_name == "get_insider_trades":
                    data = await finviz_client.get_insider_trades(sym, limit=tool_input.get("limit", 10))
                    results.append(
                        {
                            "tool": tool_name,
                            "symbol": sym,
                            "data": data,
                            "structured": build_structured_tool_payload(
                                tool_name,
                                {"symbol": sym, "limit": tool_input.get("limit", 10)},
                                data,
                            ),
                        }
                    )

                elif tool_name == "get_company_news":
                    data = await finviz_client.get_company_news(sym, limit=tool_input.get("limit", 10))
                    results.append(
                        {
                            "tool": tool_name,
                            "symbol": sym,
                            "data": data,
                            "structured": build_structured_tool_payload(
                                tool_name,
                                {"symbol": sym, "limit": tool_input.get("limit", 10)},
                                data,
                            ),
                        }
                    )

            elif block.type == "text":
                results.append({"tool": "text", "data": block.text})

        # Backfill missing symbols when the LLM under-selects tool calls.
        extracted_symbols = _extract_symbols(query)
        overview_symbols = {
            str(item.get("symbol", "")).upper()
            for item in results
            if isinstance(item, dict) and item.get("tool") == "get_company_overview"
        }
        missing_symbols = [sym for sym in extracted_symbols if sym not in overview_symbols]
        for sym in missing_symbols:
            data = await finviz_client.get_company_overview(sym)
            results.append(
                {
                    "tool": "get_company_overview",
                    "symbol": sym,
                    "data": data,
                    "structured": build_structured_tool_payload("get_company_overview", {"symbol": sym}, data),
                }
            )
            symbols.append(sym)

        formatted = _format_results(results)

        return {
            "agent": "fundamentals",
            "content": formatted,
            "symbols": list(set(symbols)),
            "data": {"tool_results": results},
            "error": None,
        }

    except Exception as e:
        logger.warning("Fundamentals agent error: %s", e)
        return {
            "agent": "fundamentals",
            "content": f"Error in fundamental analysis: {str(e)}",
            "symbols": [],
            "data": None,
            "error": str(e),
        }


async def fundamentals_node(state) -> dict:
    """LangGraph node wrapper for fundamentals agent."""
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["fundamentals"],
    )
    query = merge_queries(ready_tasks, prefix="Compare and execute these fundamentals requests")

    if not query:
        messages = state.get("messages", [])
        if messages:
            query = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        else:
            query = ""

    result = await execute(query)
    for task in ready_tasks:
        task_status_updates[task.task_id] = "failed" if result.get("error") else "completed"
    return {
        "agent_results": {"fundamentals": result},
        "task_status": task_status_updates,
    }


def _format_results(results: list[dict]) -> str:
    parts = []

    for r in results:
        if r["tool"] == "text":
            parts.append(r["data"])

        elif r["tool"] == "get_company_overview" and r.get("data"):
            d = r["data"]
            parts.append(
                f"**{_display(d.get('symbol'))}** — {_display(d.get('company'))}\n"
                f"Sector: {_display(d.get('sector'))} | Industry: {_display(d.get('industry'))}\n"
                f"Market Cap: {_display(d.get('market_cap'))} | P/E: {_display(d.get('pe'))} | Forward P/E: {_display(d.get('forward_pe'))}\n"
                f"EPS: {_display(d.get('eps'))} | Revenue: {_display(d.get('revenue'))} | Profit Margin: {_display(d.get('profit_margin'))}\n"
                f"ROE: {_display(d.get('roe'))} | Debt/Eq: {_display(d.get('debt_eq'))} | Dividend: {_display(d.get('dividend_yield'))}\n"
                f"Target Price: {_display(d.get('target_price'))} | Beta: {_display(d.get('beta'))}"
            )

        elif r["tool"] == "get_analyst_ratings" and r.get("data"):
            d = r["data"]
            ratings = d.get("ratings", [])
            if ratings:
                lines = [f"**Analyst Ratings for {d.get('symbol', '')}** ({len(ratings)} recent)"]
                for rating in ratings[:5]:
                    lines.append(
                        f"  {rating.get('date', '')} — {rating.get('analyst', '')}: "
                        f"{rating.get('action', '')} → {rating.get('rating', '')} "
                        f"(PT: {rating.get('price_target', 'N/A')})"
                    )
                parts.append("\n".join(lines))

        elif r["tool"] == "get_insider_trades" and r.get("data"):
            d = r["data"]
            trades = d.get("insider_trades", [])
            if trades:
                lines = [f"**Insider Trading for {d.get('symbol', '')}** ({len(trades)} recent)"]
                for t in trades[:5]:
                    lines.append(
                        f"  {t.get('date', '')} — {t.get('insider', '')}: "
                        f"{t.get('transaction', '')} | Value: {t.get('value', 'N/A')}"
                    )
                parts.append("\n".join(lines))

        elif r["tool"] == "get_company_news" and r.get("data"):
            d = r["data"]
            news = d.get("news", [])
            if news:
                lines = [f"**Recent News for {d.get('symbol', '')}**"]
                for article in news[:5]:
                    lines.append(f"  {article.get('date', '')} — {article.get('headline', '')} ({article.get('source', '')})")
                parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else "No fundamental data available."


def _extract_symbols(text: str) -> list[str]:
    if not text:
        return []
    stop_words = {
        "SEC",
        "EPS",
        "PE",
        "DCF",
        "RSI",
        "MACD",
        "ETF",
        "USD",
        "CEO",
        "CFO",
    }
    matches = re.findall(r"\b[A-Z]{1,5}\b", text)
    deduped: list[str] = []
    for item in matches:
        sym = item.upper()
        if sym in stop_words:
            continue
        if sym not in deduped:
            deduped.append(sym)
    return deduped


def _display(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, list):
        cleaned = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(cleaned) if cleaned else "N/A"
    text = str(value).strip()
    return text if text else "N/A"
