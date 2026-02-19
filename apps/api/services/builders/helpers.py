from __future__ import annotations

import asyncio
import math
import statistics
from datetime import datetime, timezone
from typing import Any

from apps.api.db import portfolio_repo
from apps.api.config import settings

from apps.api.services.finviz_client import (
    get_analyst_ratings,
    get_company_news,
    get_company_overview,
    get_insider_trades,
)
from apps.api.services.fred_client import get_key_indicators
from apps.api.services.market_data_provider import (
    get_unified_history,
    get_unified_market_movers,
    get_unified_quote,
    get_unified_quotes,
)
from apps.api.services.tavily_client import get_news_sentiment, search_financial_news
from apps.api.agents.technical_analysis.tools import analyze_technicals

DEV_PORTFOLIO_ID = settings.DEV_PORTFOLIO_ID
DEFAULT_SCREEN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "JPM", "V",
    "MA", "UNH", "XOM", "LLY", "HD", "COST", "ABBV", "PFE", "KO", "PEP", "PG",
    "MRK", "CSCO", "ORCL", "CRM", "AMD", "NFLX", "INTU", "ADBE", "TXN",
]
DEFAULT_DIVIDEND_UNIVERSE = [
    "JNJ", "PG", "KO", "PEP", "ABBV", "XOM", "CVX", "T", "VZ", "IBM",
    "MMM", "MCD", "MO", "PM", "HD", "LOW", "DUK", "SO", "NEE", "BMY",
]
SECTOR_COMPETITORS = {
    "semiconductors": ["NVDA", "AMD", "AVGO", "QCOM", "INTC", "TXN"],
    "ai infrastructure": ["NVDA", "MSFT", "AMZN", "GOOGL", "META", "AMD"],
    "big tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
    "banking": ["JPM", "BAC", "WFC", "C", "GS", "MS"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PSX"],
    "healthcare": ["LLY", "JNJ", "PFE", "MRK", "ABBV", "BMY"],
}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"N/A", "-", "--", "None", "."}:
        return None
    text = text.replace(",", "").replace("$", "")
    suffix = 1.0
    if text.endswith("%"):
        text = text[:-1]
    if text.endswith("T"):
        suffix = 1_000_000_000_000
        text = text[:-1]
    elif text.endswith("B"):
        suffix = 1_000_000_000
        text = text[:-1]
    elif text.endswith("M"):
        suffix = 1_000_000
        text = text[:-1]
    elif text.endswith("K"):
        suffix = 1_000
        text = text[:-1]
    try:
        return float(text) * suffix
    except ValueError:
        return None


def _safe_pct(value: Any) -> float | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if parsed > 1 and parsed <= 100:
        return parsed / 100
    if parsed > 100:
        return parsed / 10000
    return parsed


def _fmt_num(value: Any, ndigits: int = 2) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{ndigits}f}"
    except Exception:
        return str(value)


def _fmt_pct(value: Any, ndigits: int = 1) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.{ndigits}f}%"
    except Exception:
        return str(value)


def _to_markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "No rows."
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join([head, sep] + body)


def _daily_returns(history: list[dict[str, Any]]) -> list[float]:
    closes = [float(x["close"]) for x in history if x.get("close") is not None]
    if len(closes) < 2:
        return []
    returns = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev <= 0:
            continue
        returns.append((closes[i] / prev) - 1)
    return returns


def _correlation(a: list[float], b: list[float]) -> float | None:
    n = min(len(a), len(b))
    if n < 3:
        return None
    a2 = a[-n:]
    b2 = b[-n:]
    mean_a = statistics.mean(a2)
    mean_b = statistics.mean(b2)
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a2, b2))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a2))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in b2))
    if den_a == 0 or den_b == 0:
        return None
    return num / (den_a * den_b)


def _extract_ticker(payload: dict[str, Any]) -> str | None:
    for key in ("ticker", "symbol"):
        if payload.get(key):
            return str(payload[key]).upper()
    # Accept a list under 'tickers' — use the first entry
    tickers_list = payload.get("tickers")
    if isinstance(tickers_list, list) and tickers_list:
        return str(tickers_list[0]).upper()
    stock = payload.get("stock") or payload.get("company")
    if isinstance(stock, str):
        token = stock.strip().split()[0].upper()
        if 1 <= len(token) <= 6 and token.isalpha():
            return token
    return None


def _extract_top_headlines(fin_news: dict[str, Any] | None, web_news: dict[str, Any] | None, limit: int = 4) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in (fin_news or {}).get("news", [])[:limit]:
        out.append(
            {
                "title": str(item.get("headline", "")),
                "source": str(item.get("source", "Finviz")),
                "url": str(item.get("link", "")),
            }
        )
    if len(out) < limit:
        for item in (web_news or {}).get("results", [])[:limit]:
            if len(out) >= limit:
                break
            out.append(
                {
                    "title": str(item.get("title", "")),
                    "source": "Web",
                    "url": str(item.get("url", "")),
                }
            )
    return out


async def _run_research_subagents(symbol: str, include_macro: bool = False) -> dict[str, Any]:
    """Run lightweight specialist collectors in parallel (sub-agent pattern)."""
    tasks: dict[str, Any] = {
        "fundamentals": get_company_overview(symbol),
        "market_quote": get_unified_quote(symbol),
        "market_history": get_unified_history(symbol, days=365),
        "analyst_ratings": get_analyst_ratings(symbol),
        "company_news": get_company_news(symbol, limit=12),
        "insider_trades": get_insider_trades(symbol, limit=12),
        "web_sentiment": get_news_sentiment(symbol),
        "web_news": search_financial_news(f"{symbol} stock outlook", limit=5),
    }
    if include_macro:
        tasks["macro"] = get_key_indicators()

    names = list(tasks.keys())
    try:
        # Wrap gather in a timeout to prevent hanging on slow scrapers (Finviz, etc.)
        values = await asyncio.wait_for(asyncio.gather(*tasks.values(), return_exceptions=True), timeout=25.0)
    except asyncio.TimeoutError:
        # If the whole gather times out, return what we have (empty or errors)
        return {"subagent_trace": [{"agent": n, "status": "timeout"} for n in names]}

    out: dict[str, Any] = {}
    for name, value in zip(names, values):
        if isinstance(value, Exception):
            print(f"Subagent {name} failed: {value}")
            out[name] = None
        else:
            out[name] = value

    out["subagent_trace"] = [
        {"agent": name, "status": "ok" if out.get(name) else "empty"}
        for name in names
    ]
    return out


async def _load_stock_context(symbol: str) -> dict[str, Any]:
    subagent_outputs = await _run_research_subagents(symbol, include_macro=False)
    overview = subagent_outputs.get("fundamentals")
    quote = subagent_outputs.get("market_quote")
    history = subagent_outputs.get("market_history")
    ratings = subagent_outputs.get("analyst_ratings")
    news = subagent_outputs.get("company_news")
    insiders = subagent_outputs.get("insider_trades")
    web_sentiment = subagent_outputs.get("web_sentiment")
    web_news = subagent_outputs.get("web_news")
    return {
        "symbol": symbol.upper(),
        "overview": overview or {},
        "quote": quote or {},
        "history": history or [],
        "ratings": ratings or {},
        "news": news or {},
        "insiders": insiders or {},
        "web_sentiment": web_sentiment or {},
        "web_news": web_news or {},
        "headlines": _extract_top_headlines(news or {}, web_news or {}),
        "subagent_trace": subagent_outputs.get("subagent_trace", []),
    }


def _moat_rating(overview: dict[str, Any]) -> str:
    roe = _safe_pct(overview.get("roe")) or 0
    margin = _safe_pct(overview.get("profit_margin")) or 0
    debt = _safe_float(overview.get("debt_eq")) or 0
    score = (roe * 100) + (margin * 100) - min(debt, 200) * 0.05
    if score >= 30:
        return "strong"
    if score >= 15:
        return "moderate"
    return "weak"


def _risk_score(overview: dict[str, Any], quote: dict[str, Any]) -> tuple[int, str]:
    beta = _safe_float(overview.get("beta")) or 1.0
    debt = _safe_float(overview.get("debt_eq")) or 0
    pe = _safe_float(overview.get("pe")) or 20
    pct = abs(float(quote.get("percent_change") or 0))
    score = 3 + min(beta, 3) + min(debt / 150, 2) + min(pe / 40, 2) + min(pct / 5, 1)
    score_int = max(1, min(10, int(round(score))))
    reason = f"beta={beta:.2f}, debt/equity={debt:.2f}, P/E={pe:.1f}, daily move={pct:.2f}%"
    return score_int, reason


def _build_tool_plan(report_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = _extract_ticker(payload)
    plan: list[dict[str, Any]] = []

    if ticker:
        plan.append({"tool": "market_data_provider.get_unified_quote", "reason": f"Live price anchor for {ticker}"})
        plan.append({"tool": "market_data_provider.get_unified_history", "reason": f"Trend/volatility history for {ticker}"})
        plan.append({"tool": "finviz.get_company_overview", "reason": f"Fundamentals for {ticker}"})
        plan.append({"tool": "finviz.get_analyst_ratings", "reason": f"Street signals for {ticker}"})
        plan.append({"tool": "tavily.get_news_sentiment", "reason": f"Recent narrative/sentiment for {ticker}"})
    if report_type in {"morgan_dcf", "mckinsey_macro"}:
        plan.append({"tool": "fred.get_key_indicators", "reason": "Macro inputs for discount-rate/cycle assumptions"})
    if report_type in {"bridgewater_risk", "blackrock_builder", "mckinsey_macro"}:
        plan.append({"tool": "portfolio_repo.get_holdings", "reason": "Portfolio-aware recommendations"})
    return plan


def _default_sources(report_type: str) -> list[str]:
    mapping = {
        "goldman_screener": ["market_data_provider", "finviz", "tavily_news_sentiment"],
        "morgan_dcf": ["market_data_provider", "finviz", "fred", "tavily_financial_news"],
        "bridgewater_risk": ["portfolio_db", "market_data_provider", "finviz"],
        "jpm_earnings": ["market_data_provider", "finviz", "tavily_news_sentiment", "tavily_financial_news"],
        "blackrock_builder": ["historical_allocation_proxies"],
        "citadel_technical": ["market_data_provider", "technical_analysis"],
        "harvard_dividend": ["finviz", "market_data_provider"],
        "bain_competitive": ["market_data_provider", "finviz", "tavily_financial_news"],
        "renaissance_pattern": ["market_data_provider", "finviz", "tavily_financial_news"],
        "mckinsey_macro": ["fred", "market_data_provider", "portfolio_db"],
    }
    return mapping.get(report_type, ["market_data_provider", "finviz"])

