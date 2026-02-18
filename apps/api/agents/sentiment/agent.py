"""Sentiment Agent — Reddit, news, and congressional trading sentiment."""

import asyncio
import logging

import anthropic

from apps.api.config import settings
from apps.api.agents.supervisor.task_runtime import get_ready_tasks_for_agent, merge_queries
from apps.api.services import reddit_client, tavily_client

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def execute(query: str) -> dict:
    """Aggregate sentiment from multiple sources."""
    query_lower = query.lower()
    symbols = _extract_symbols(query)

    results = {}
    all_symbols = list(symbols)

    # Determine which sentiment sources to query
    wants_reddit = any(w in query_lower for w in ["reddit", "social", "sentiment", "wsb", "wallstreetbets"])
    wants_capitol = any(w in query_lower for w in ["congress", "capitol", "political", "politician", "senator", "representative"])
    wants_news = any(w in query_lower for w in ["news", "headline"])

    # Default: if a symbol is mentioned, get all sentiment sources
    if symbols and not (wants_reddit or wants_capitol or wants_news):
        wants_reddit = True
        wants_news = True

    # If no specific request, get trending
    if not symbols and not wants_capitol:
        wants_reddit = True

    tasks = []

    if symbols:
        for sym in symbols[:2]:
            if wants_reddit:
                tasks.append(("reddit", sym, reddit_client.get_stock_sentiment(sym)))
            if wants_news:
                tasks.append(("news", sym, tavily_client.get_news_sentiment(sym)))
            if wants_capitol:
                tasks.append(("capitol", sym, tavily_client.get_political_trades(sym)))
    else:
        if wants_reddit:
            tasks.append(("reddit_trending", None, reddit_client.get_trending_posts(limit=15)))
        if wants_capitol:
            tasks.append(("capitol_trending", None, tavily_client.get_political_trades()))

    # Execute all tasks concurrently
    if tasks:
        coros = [t[2] for t in tasks]
        task_results = await asyncio.gather(*coros, return_exceptions=True)

        for (source, sym, _), result in zip(tasks, task_results):
            if isinstance(result, Exception):
                continue
            if result:
                key = f"{source}:{sym}" if sym else source
                results[key] = result

    # Format the output
    formatted = _format_sentiment(results, symbols)

    return {
        "agent": "sentiment",
        "content": formatted,
        "symbols": all_symbols,
        "data": results,
        "error": None,
    }


async def sentiment_node(state) -> dict:
    """LangGraph node wrapper for sentiment agent."""
    plan = state.get("plan")
    current_task_status = dict(state.get("task_status", {}) or {})
    task_status_updates: dict[str, str] = {}
    ready_tasks = get_ready_tasks_for_agent(
        plan=plan,
        task_status=current_task_status,
        agent_names=["sentiment"],
    )
    query = merge_queries(ready_tasks, prefix="Run these sentiment analysis requests")

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
        "agent_results": {"sentiment": result},
        "task_status": task_status_updates,
    }


def _format_sentiment(results: dict, symbols: list[str]) -> str:
    parts = []

    for key, data in results.items():
        if key.startswith("reddit:"):
            sym = key.split(":")[1]
            parts.append(
                f"**Reddit Sentiment — {sym}**\n"
                f"Overall: {data.get('overall_sentiment', 'N/A').upper()} "
                f"(Score: {data.get('sentiment_score', 'N/A')})\n"
                f"Posts analyzed: {data.get('post_count', 0)}"
            )
            posts = data.get("posts", [])[:3]
            if posts:
                for p in posts:
                    parts.append(f"  - r/{p.get('subreddit', '')}: {p.get('title', '')[:80]} (Score: {p.get('score', 0)})")

        elif key == "reddit_trending":
            posts = data.get("posts", [])[:8]
            if posts:
                lines = ["**Trending on Reddit**"]
                for p in posts:
                    sentiment_label = p.get("sentiment", {}).get("label", "neutral")
                    lines.append(
                        f"  r/{p.get('subreddit', '')} | {p.get('title', '')[:70]} "
                        f"(Score: {p.get('score', 0)}, {sentiment_label})"
                    )
                parts.append("\n".join(lines))

        elif key.startswith("news:"):
            sym = key.split(":")[1]
            parts.append(
                f"**News Sentiment — {sym}**\n"
                f"Overall: {data.get('news_sentiment', 'N/A').upper()} "
                f"(Score: {data.get('sentiment_score', 'N/A')})"
            )
            articles = data.get("articles", [])[:3]
            if articles:
                for a in articles:
                    parts.append(f"  - {a.get('title', '')[:80]}")

        elif key.startswith("capitol"):
            title = "Congressional Trading Activity"
            if ":" in key:
                sym = key.split(":")[1]
                title = f"Congressional Trading — {sym}"

            search_results = data.get("results", [])[:5]
            if search_results:
                lines = [f"**{title}**"]
                for r in search_results:
                    lines.append(f"  - {r.get('title', '')[:80]}")
                parts.append("\n".join(lines))

    return "\n\n".join(parts) if parts else "No sentiment data available for this query."


def _extract_symbols(query: str) -> list[str]:
    import re
    dollar = re.findall(r'\$([A-Z]{1,5})\b', query)
    upper = re.findall(r'\b([A-Z]{2,5})\b', query)
    common = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "WAS",
              "ONE", "OUR", "OUT", "HAS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD",
              "GET", "GOT", "SHOW", "NEWS", "REDDIT", "WHAT", "FROM", "WITH"}
    filtered = [w for w in upper if w not in common]
    return list(dict.fromkeys(dollar + filtered))[:5]
