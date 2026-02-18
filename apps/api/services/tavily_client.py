"""Tavily client for web search — used by Sentiment agent for news and Capitol trades."""

import asyncio
import httpx

from apps.api.config import settings
from apps.api.services.cache import cache_get_or_fetch

TAVILY_URL = "https://api.tavily.com/search"

FINANCIAL_DOMAINS = [
    "reuters.com", "bloomberg.com", "wsj.com", "cnbc.com",
    "marketwatch.com", "seekingalpha.com", "finance.yahoo.com",
    "barrons.com", "investopedia.com", "fool.com",
]

CAPITOL_DOMAINS = [
    "capitoltrades.com", "quiverquant.com", "reuters.com",
    "bloomberg.com", "wsj.com", "cnbc.com",
]


async def search(
    query: str,
    domains: list[str] | None = None,
    max_results: int = 5,
    search_depth: str = "advanced",
) -> dict | None:
    """Search the web via Tavily API."""
    if not settings.TAVILY_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "api_key": settings.TAVILY_API_KEY,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
            }
            if domains:
                payload["include_domains"] = domains

            resp = await client.post(TAVILY_URL, json=payload, timeout=15.0)
            if resp.status_code != 200:
                return None

            data = resp.json()
            return {
                "query": query,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0),
                    }
                    for r in data.get("results", [])
                ],
            }
    except Exception as e:
        print(f"Tavily search error: {e}")
        return None


async def search_financial_news(query: str, limit: int = 5) -> dict | None:
    """Search financial news."""
    cache_key = f"tavily:news:{query}"

    async def _fetch():
        return await search(query, domains=FINANCIAL_DOMAINS, max_results=limit)

    return await cache_get_or_fetch(cache_key, _fetch, "news")


async def search_capitol_trades(query: str, limit: int = 5) -> dict | None:
    """Search for congressional trading activity."""
    cache_key = f"tavily:capitol:{query}"

    async def _fetch():
        return await search(query, domains=CAPITOL_DOMAINS, max_results=limit)

    return await cache_get_or_fetch(cache_key, _fetch, "news")


async def get_political_trades(symbol: str | None = None) -> dict | None:
    """Get recent congressional trading activity."""
    if symbol:
        query = f"congress trading {symbol} stock 2024 2025"
    else:
        query = "congressional stock trading recent activity 2025"

    return await search_capitol_trades(query)


async def get_news_sentiment(symbol: str) -> dict | None:
    """Get news and derive sentiment for a stock."""
    cache_key = f"tavily:sentiment:{symbol.upper()}"

    async def _fetch():
        result = await search(
            f"{symbol} stock news analysis",
            domains=FINANCIAL_DOMAINS,
            max_results=8,
        )
        if not result:
            return None

        # Simple sentiment from news headlines
        positive_words = ["surge", "rally", "gain", "beat", "upgrade", "buy", "bullish", "growth", "strong"]
        negative_words = ["drop", "fall", "miss", "downgrade", "sell", "bearish", "decline", "weak", "crash"]

        pos_count = 0
        neg_count = 0
        for article in result.get("results", []):
            text = f"{article['title']} {article['content']}".lower()
            pos_count += sum(1 for w in positive_words if w in text)
            neg_count += sum(1 for w in negative_words if w in text)

        total = pos_count + neg_count
        score = pos_count / total if total > 0 else 0.5
        label = "bullish" if score > 0.6 else "bearish" if score < 0.4 else "neutral"

        return {
            "symbol": symbol.upper(),
            "news_sentiment": label,
            "sentiment_score": round(score, 2),
            "articles": result.get("results", [])[:5],
        }

    return await cache_get_or_fetch(cache_key, _fetch, "news")
