"""Unified market data provider with Schwab-first fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.api.config import settings
from apps.api.services.alpaca_client import (
    get_alpaca_history,
    get_alpaca_movers,
    get_alpaca_news,
    get_alpaca_quote,
)
from apps.api.services.finviz_client import get_company_overview
from apps.api.services.schwab_client import (
    get_market_hours,
    get_market_movers,
    get_multiple_quotes,
    get_price_history,
    get_quote,
)


def _provider_order() -> list[str]:
    if settings.MARKET_DATA_PROVIDER == "schwab":
        return ["schwab", "alpaca"]
    if settings.MARKET_DATA_PROVIDER == "alpaca":
        return ["alpaca", "schwab"]
    return ["schwab", "alpaca"]


def _format_alpaca_quote(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": raw.get("symbol"),
        "price": raw.get("price"),
        "change": raw.get("change", 0.0),
        "percent_change": raw.get("percent_change", 0.0),
        "volume": raw.get("volume"),
        "bid": raw.get("bid"),
        "ask": raw.get("ask"),
        "open": raw.get("open"),
        "close": raw.get("close"),
        "high": raw.get("high"),
        "low": raw.get("low"),
        "week_52_high": raw.get("week_52_high"),
        "week_52_low": raw.get("week_52_low"),
        "pe_ratio": raw.get("pe_ratio"),
        "dividend_yield": raw.get("dividend_yield"),
        "timestamp": raw.get("timestamp"),
        "provider": "alpaca",
    }


def _format_schwab_quote(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": raw.get("symbol"),
        "price": raw.get("price"),
        "change": raw.get("change", 0.0),
        "percent_change": raw.get("percent_change", 0.0),
        "volume": raw.get("volume"),
        "bid": raw.get("bid"),
        "ask": raw.get("ask"),
        "open": raw.get("open"),
        "close": raw.get("close"),
        "high": raw.get("high"),
        "low": raw.get("low"),
        "week_52_high": raw.get("week_52_high"),
        "week_52_low": raw.get("week_52_low"),
        "pe_ratio": raw.get("pe_ratio"),
        "dividend_yield": raw.get("dividend_yield"),
        "timestamp": raw.get("trade_time"),
        "provider": "schwab",
    }


def _map_days_to_schwab_period(days: int) -> tuple[str, int]:
    # Schwab daily candles require month/year periods. `day` is for intraday minute data.
    if days <= 30:
        return ("month", 1)
    if days <= 60:
        return ("month", 2)
    if days <= 90:
        return ("month", 3)
    if days <= 180:
        return ("month", 6)
    if days <= 365:
        return ("year", 1)
    if days <= 730:
        return ("year", 2)
    if days <= 1825:
        return ("year", 5)
    return ("year", 10)


def _normalize_history(raw: dict[str, Any], symbol: str, days: int) -> list[dict[str, Any]]:
    candles = raw.get("candles", []) if raw else []
    normalized = []
    for c in candles[-days:]:
        dt = c.get("datetime")
        if isinstance(dt, (int, float)):
            date_val = datetime.fromtimestamp(dt / 1000).strftime("%Y-%m-%d")
        elif isinstance(dt, str):
            date_val = dt[:10]
        else:
            date_val = ""
        normalized.append(
            {
                "symbol": symbol.upper(),
                "date": date_val,
                "open": c.get("open"),
                "high": c.get("high"),
                "low": c.get("low"),
                "close": c.get("close"),
                "volume": c.get("volume"),
            }
        )
    return normalized


def _is_history_stale(rows: list[dict[str, Any]], max_age_days: int = 7) -> bool:
    if not rows:
        return True
    last = rows[-1]
    date_text = str(last.get("date", ""))[:10]
    if not date_text:
        return True
    try:
        dt = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return True
    now = datetime.now(timezone.utc)
    return (now - dt).days > max_age_days


async def get_unified_quote(symbol: str) -> dict[str, Any] | None:
    for provider in _provider_order():
        if provider == "schwab":
            q = await get_quote(symbol)
            if q and q.get("price") is not None:
                return _format_schwab_quote(q)
        else:
            q = await get_alpaca_quote(symbol)
            if q and q.get("price") is not None:
                return _format_alpaca_quote(q)
    return None


async def get_unified_quotes(symbols: list[str]) -> dict[str, Any]:
    # Schwab can return multi-quotes efficiently.
    if "schwab" in _provider_order():
        schwab_quotes = await get_multiple_quotes(symbols)
        if schwab_quotes:
            return {k: _format_schwab_quote(v) for k, v in schwab_quotes.items() if v.get("price") is not None}

    results: dict[str, Any] = {}
    for symbol in symbols:
        quote = await get_unified_quote(symbol)
        if quote:
            results[symbol.upper()] = quote
    return results


async def get_unified_history(symbol: str, days: int = 30) -> list[dict[str, Any]]:
    for provider in _provider_order():
        if provider == "schwab":
            period_type, period = _map_days_to_schwab_period(days)
            raw = await get_price_history(
                symbol=symbol,
                period_type=period_type,
                period=period,
                frequency_type="daily",
                frequency=1,
            )
            normalized = _normalize_history(raw or {}, symbol=symbol, days=days)
            if normalized and not _is_history_stale(normalized):
                return normalized
        else:
            raw = await get_alpaca_history(symbol, timeframe="1Day", limit=max(days, 30))
            if raw:
                rows = raw[-days:]
                if rows and not _is_history_stale(rows):
                    return rows
    return []


async def get_unified_market_movers() -> dict[str, Any] | None:
    for provider in _provider_order():
        if provider == "schwab":
            movers = await get_market_movers()
            if movers:
                return movers
        else:
            movers = await get_alpaca_movers()
            if movers:
                return movers
    return None


async def get_unified_market_hours(markets: list[str] | None = None) -> dict[str, Any] | None:
    hours = await get_market_hours(markets)
    if hours:
        return hours
    return None


async def get_unified_stock_news(symbol: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    news = await get_alpaca_news(symbol, limit)
    return news or []


async def get_unified_company_profile(symbol: str) -> dict[str, Any]:
    profile = await get_company_overview(symbol)
    if profile:
        return profile
    return {
        "symbol": symbol.upper(),
        "company": symbol.upper(),
        "sector": "",
        "industry": "",
        "country": "",
        "market_cap": "",
        "pe": "",
        "dividend_yield": "",
    }
