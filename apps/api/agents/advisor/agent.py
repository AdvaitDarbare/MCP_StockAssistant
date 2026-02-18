import re
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from apps.api.agents.advisor.tools import advisor_tools, get_quote, get_historical_prices, get_stock_news
from apps.api.agents.content_utils import normalize_content_to_text, truncate_text
from apps.api.config import settings
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries

# System prompt for the Advisor Agent
ADVISOR_PROMPT = """You are an expert Investment Advisor and Financial Analyst. 
Your goal is to provide concise, data-grounded analysis with clear uncertainty.

You have access to real-time market data and research context.
When asked for advice or a move-explainer:
1. **Use Evidence First**: Prioritize facts from tools and provided specialist context.
2. **No Unsupported Claims**: If evidence is missing, say so explicitly.
3. **Recency Discipline**: For "past week" requests, quantify the move and use dated events from the last 7 calendar days.
4. **Risk Awareness**: Include downside/invalidating factors.
5. **Risk Perspective**: Explain downside and invalidation clearly.

If you are asked to buy or sell, you can recommend a thesis, entry zone, and risk controls.
Do not execute any trade.

Formatting rules:
- Use a 3-part structure:
  1) Direct answer first line: `**Direct answer:** ...`
  2) Short breakdown using `###` section anchors and bullet points.
  3) End with `**Next step:** ...`
- Bold the core concept of each section.
- Use markdown tables for compact comparisons when relevant.
- Keep output under ~220 words unless user asks for a deep dive.
- Do not output JSON/Python objects.
"""

async def advisor_node(state):
    """
    The Advisor agent node.
    """
    model = ChatAnthropic(
        model=settings.DEFAULT_MODEL,
        api_key=settings.ANTHROPIC_API_KEY
    )
    agent = create_react_agent(model, advisor_tools, prompt=ADVISOR_PROMPT)
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["advisor"],
    )
    query = merge_queries(ready_tasks, prefix="Run these advisory requests")
    if not query:
        messages = state.get("messages", [])
        if messages:
            query = messages[-1].content if hasattr(messages[-1], "content") else str(messages[-1])
        else:
            query = ""

    user_query = _latest_user_query(state)
    deterministic = await _run_price_move_explainer_if_applicable(state, user_query or query)
    if deterministic is not None:
        for task in ready_tasks:
            task_status_updates[task.task_id] = "failed" if deterministic.get("error") else "completed"
        return {
            "agent_results": {"advisor": deterministic},
            "task_status": task_status_updates,
        }

    context = _build_specialist_context(state.get("agent_results", {}))
    advisor_query = query
    if context:
        advisor_query = (
            f"User request:\n{query}\n\n"
            f"Specialist context from this run:\n{context}\n\n"
            "Use this context first, then call tools only if needed to fill critical gaps."
        )

    result = await agent.ainvoke({"messages": [("user", advisor_query)]})
    last_message = result["messages"][-1]
    content = normalize_content_to_text(last_message.content if hasattr(last_message, "content") else str(last_message))
    for task in ready_tasks:
        task_status_updates[task.task_id] = "completed"

    return {
        "agent_results": {
            "advisor": {
                "agent": "advisor",
                "content": content,
                "symbols": [],
                "data": {"tool_results": _extract_tool_results(result)},
                "error": None,
            }
        },
        "task_status": task_status_updates,
    }


def _build_specialist_context(agent_results: dict) -> str:
    if not isinstance(agent_results, dict) or not agent_results:
        return ""
    lines: list[str] = []
    for agent_name, payload in agent_results.items():
        if not isinstance(payload, dict):
            continue
        content = normalize_content_to_text(payload.get("content", ""))
        if not content:
            continue
        lines.append(f"- {agent_name}: {truncate_text(content, 700)}")
    return "\n".join(lines)


def _extract_tool_results(result: dict) -> list[dict]:
    out: list[dict] = []
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            if not isinstance(call, dict):
                continue
            name = str(call.get("name", "")).strip()
            args = call.get("args", {}) if isinstance(call.get("args"), dict) else {}
            if not name:
                continue
            symbol = str(args.get("symbol", "")).upper() if args.get("symbol") else ""
            out.append({"tool": name, "symbol": symbol})
    return out


async def _run_price_move_explainer_if_applicable(state, query: str):
    if not _is_price_move_query(query):
        return None

    symbol = _resolve_symbol(query, state)
    if not symbol:
        return None

    horizon_days = _extract_horizon_days(query)
    horizon_label = _horizon_label(horizon_days)
    quote = await get_quote.ainvoke({"symbol": symbol})
    history = _history_from_market_data_state(state)
    if not history:
        history = await get_historical_prices.ainvoke({"symbol": symbol, "days": max(15, horizon_days + 8)})
    news = await get_stock_news.ainvoke({"symbol": symbol, "limit": 6})

    history_list = history if isinstance(history, list) else []
    news_list = news if isinstance(news, list) else []
    move = _compute_recent_move(history_list, horizon_days=horizon_days)
    stale = _is_stale(
        move["end_date"],
        max_age_days=max(3, min(10, horizon_days + 1)),
    ) if move is not None else True
    reversal = _compute_reversal_snapshot(history_list, horizon_days=horizon_days)
    sentiment_text = _sentiment_snippet(state, symbol)

    if move is None:
        answer = (
            f"I couldn't compute a reliable move for {symbol} over {horizon_label} from available price history. "
            "I can summarize headlines, but the exact move pattern is uncertain."
        )
    elif stale:
        answer = (
            f"I can't reliably explain {symbol} over {horizon_label} because the latest history point is "
            f"{move['end_date']}, which is stale for this attribution window."
        )
    else:
        direction = "up" if move["pct_change"] >= 0 else "down"
        query_lower = (query or "").lower()
        asks_up_then_drop = ("up" in query_lower or "rise" in query_lower) and (
            "drop" in query_lower or "fell" in query_lower or "down" in query_lower
        )
        if asks_up_then_drop and reversal.get("has_reversal"):
            answer = (
                f"{symbol} did rise and then drop over {horizon_label}: it moved up into {reversal['peak_date']} "
                f"and then pulled back about {abs(reversal['peak_to_end_pct']):.1f}% into the latest close."
            )
        elif "up" in query_lower and move["pct_change"] < 0:
            answer = (
                f"Available data does not show {symbol} up over {horizon_label}; it shows about "
                f"{abs(move['pct_change']):.1f}% down."
            )
        else:
            answer = (
                f"{symbol} is {direction} about {abs(move['pct_change']):.1f}% over {horizon_label} in available data; "
                "the move appears tied to a mix of news flow and sentiment, not one single confirmed catalyst."
            )

    latest_price = quote.get("price") if isinstance(quote, dict) else None
    price_parts: list[str] = []
    if move is not None:
        price_parts.append(
            f"{move['start_date']} ${move['start_close']:.2f} -> {move['end_date']} ${move['end_close']:.2f} ({move['pct_change']:+.1f}%)"
        )
    if reversal.get("has_reversal"):
        price_parts.append(
            f"peaked on {reversal['peak_date']} at ${reversal['peak_close']:.2f}, then moved {reversal['peak_to_end_pct']:+.1f}% to the latest close"
        )
    if isinstance(latest_price, (int, float)):
        price_parts.append(f"latest quote ${float(latest_price):.2f}")
    if stale and move is not None:
        price_parts.append(f"history may be stale (latest bar {move['end_date']})")

    drivers: list[str] = []
    if news_list:
        for item in news_list[:3]:
            headline = str(item.get("headline", "")).strip()
            if not headline:
                continue
            source = str(item.get("source", "")).strip() or "source n/a"
            timestamp = str(item.get("timestamp", "")).strip()
            date_part = timestamp[:10] if timestamp else "date n/a"
            drivers.append(f"{date_part} ({source}): {headline}")
    else:
        drivers.append("No company-specific news headlines were returned by the connected feed.")

    price_rows: list[tuple[str, str]] = []
    if move is not None:
        price_rows.append(("Window", f"{move['start_date']} to {move['end_date']}"))
        price_rows.append(
            ("Net move", f"${move['start_close']:.2f} -> ${move['end_close']:.2f} ({move['pct_change']:+.1f}%)")
        )
    if reversal.get("has_reversal"):
        price_rows.append(
            (
                "Reversal",
                f"Peak {reversal['peak_date']} at ${reversal['peak_close']:.2f}, then {reversal['peak_to_end_pct']:+.1f}%",
            )
        )
    if isinstance(latest_price, (int, float)):
        price_rows.append(("Latest quote", f"${float(latest_price):.2f}"))
    if stale and move is not None:
        price_rows.append(("Data freshness", f"Stale (latest bar {move['end_date']})"))

    lines = [f"**Direct answer:** {answer}", ""]

    if price_rows:
        lines.extend(
            [
                "### Price Action",
                "",
                "| Metric | Value |",
                "|---|---|",
            ]
        )
        for metric, value in price_rows:
            safe_value = str(value).replace("|", "\\|")
            lines.append(f"| **{metric}** | {safe_value} |")
        lines.append("")

    lines.extend(["### Likely Drivers", ""])
    for driver in drivers:
        lines.append(f"- **Catalyst:** {driver}")

    if sentiment_text:
        lines.append(f"- **Sentiment check:** {sentiment_text}")

    lines.extend(
        [
            "",
            "### Risk & Confidence",
            "",
            "- **Counterpoint:** Short-term moves can be flow-driven and reverse quickly if volume fades.",
            f"- **Confidence:** {_confidence_label(move, news_list, sentiment_text, stale, horizon_label)}.",
            "- **Method note:** Attribution here is correlation-based from available tools, not proof of causation.",
            "",
            "**Next step:** Want a catalyst probability breakdown with a trade plan (entry, invalidation, stop)?",
        ]
    )

    return {
        "agent": "advisor",
        "content": "\n".join(lines).strip(),
        "symbols": [symbol],
        "data": {
            "tool_results": [
                {"tool": "get_quote", "symbol": symbol},
                {"tool": "get_historical_prices", "symbol": symbol},
                {"tool": "get_stock_news", "symbol": symbol},
            ],
            "quote": quote,
            "history_points": len(history_list),
            "news_count": len(news_list),
        },
        "error": None,
    }


def _is_price_move_query(query: str) -> bool:
    q = (query or "").lower()
    movement_terms = ("go up", "went up", "up in price", "price increase", "surge", "jump", "rally", "rise", "drop", "down")
    why_terms = ("why", "what caused", "what drove", "reason", "factor", "contributing", "explain")
    horizon_terms = ("past week", "last week", "this week", "recently", "past", "last", "days", "day")
    has_motion = any(m in q for m in movement_terms)
    has_intent = any(w in q for w in why_terms)
    has_horizon = any(h in q for h in horizon_terms)
    return (has_motion and has_intent) or (has_motion and has_horizon)


def _extract_horizon_days(query: str) -> int:
    q = (query or "").lower()
    match = re.search(r"(?:past|last)\s+(\d{1,3})\s+day", q)
    if match:
        return max(1, min(90, int(match.group(1))))
    if "past week" in q or "last week" in q or "this week" in q:
        return 7
    if "past month" in q or "last month" in q:
        return 30
    return 7


def _horizon_label(days: int) -> str:
    if days == 1:
        return "the last 1 trading day"
    return f"the last {days} trading days"


def _resolve_symbol(query: str, state) -> str:
    # Explicit tickers first: $RIVN or RIVN
    dollar = re.findall(r"\$([A-Z]{1,5})\b", query or "")
    if dollar:
        return dollar[0].upper()
    upper = re.findall(r"\b([A-Z]{2,5})\b", query or "")
    if upper:
        return upper[0].upper()

    alias_map = {
        "rivian": "RIVN",
        "apple": "AAPL",
        "microsoft": "MSFT",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "amazon": "AMZN",
        "meta": "META",
        "google": "GOOGL",
        "alphabet": "GOOGL",
    }
    q = (query or "").lower()
    for name, ticker in alias_map.items():
        if name in q:
            return ticker

    # Fallback: symbols collected by prior agents in this run.
    results = state.get("agent_results", {})
    if isinstance(results, dict):
        for payload in results.values():
            if not isinstance(payload, dict):
                continue
            symbols = payload.get("symbols", [])
            if isinstance(symbols, list) and symbols:
                return str(symbols[0]).upper()
    return ""


def _compute_recent_move(history: list[dict], horizon_days: int = 7) -> dict | None:
    rows = [h for h in history if isinstance(h, dict) and isinstance(h.get("close"), (int, float))]
    if len(rows) < 2:
        return None
    needed = max(2, horizon_days + 1)
    window = rows[-needed:] if len(rows) >= needed else rows
    start = window[0]
    end = window[-1]
    start_close = float(start.get("close"))
    end_close = float(end.get("close"))
    if start_close == 0:
        return None
    pct_change = ((end_close - start_close) / start_close) * 100.0
    return {
        "start_date": str(start.get("date", ""))[:10],
        "end_date": str(end.get("date", ""))[:10],
        "start_close": start_close,
        "end_close": end_close,
        "pct_change": pct_change,
    }


def _compute_reversal_snapshot(history: list[dict], horizon_days: int = 7) -> dict:
    rows = [h for h in history if isinstance(h, dict) and isinstance(h.get("close"), (int, float))]
    needed = max(2, horizon_days + 1)
    window = rows[-needed:] if len(rows) >= needed else rows
    if len(window) < 3:
        return {"has_reversal": False}

    start = window[0]
    end = window[-1]
    peak = max(window, key=lambda r: float(r.get("close", 0)))
    start_close = float(start.get("close"))
    peak_close = float(peak.get("close"))
    end_close = float(end.get("close"))
    if start_close <= 0 or peak_close <= 0:
        return {"has_reversal": False}

    start_to_peak_pct = ((peak_close - start_close) / start_close) * 100.0
    peak_to_end_pct = ((end_close - peak_close) / peak_close) * 100.0
    has_reversal = start_to_peak_pct > 0.5 and peak_to_end_pct < -0.5
    return {
        "has_reversal": has_reversal,
        "peak_date": str(peak.get("date", ""))[:10],
        "peak_close": peak_close,
        "start_to_peak_pct": start_to_peak_pct,
        "peak_to_end_pct": peak_to_end_pct,
    }


def _history_from_market_data_state(state) -> list[dict]:
    results = state.get("agent_results", {})
    if not isinstance(results, dict):
        return []
    market = results.get("market_data")
    if not isinstance(market, dict):
        return []
    payload = market.get("data")
    if not isinstance(payload, dict):
        return []
    output = payload.get("output")
    raw = payload.get("raw")
    if isinstance(output, list):
        return [row for row in output if isinstance(row, dict)]
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    return []


def _sentiment_snippet(state, symbol: str) -> str:
    results = state.get("agent_results", {})
    if not isinstance(results, dict):
        return ""
    sentiment = results.get("sentiment")
    if not isinstance(sentiment, dict):
        return ""
    text = normalize_content_to_text(sentiment.get("content", ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    upper_symbol = (symbol or "").upper()
    if upper_symbol and upper_symbol not in text.upper():
        return "No stock-specific social sentiment signal found in this run."
    return truncate_text(text, 180)


def _confidence_label(move: dict | None, news: list[dict], sentiment: str, stale: bool, horizon_label: str) -> str:
    if stale:
        return f"Low (stale price history for {horizon_label} attribution)"
    score = 0
    if move is not None:
        score += 1
    if len(news) >= 2:
        score += 1
    if sentiment:
        score += 1
    if score >= 3:
        return "Medium-High (price move + multiple headlines + sentiment signals)"
    if score == 2:
        return "Medium (partial evidence across price and catalyst data)"
    return "Low-Medium (limited supporting evidence from available feeds)"


def _latest_user_query(state) -> str:
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            return str(getattr(msg, "content", "") or "")
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", "") or "")
    return ""


def _is_stale(date_text: str, max_age_days: int = 7) -> bool:
    if not date_text:
        return True
    try:
        dt = datetime.strptime(date_text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return True
    now = datetime.now(timezone.utc)
    return (now - dt).days > max_age_days
