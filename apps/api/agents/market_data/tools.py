from langchain_core.tools import tool

from apps.api.services.market_data_provider import (
    get_unified_company_profile,
    get_unified_history,
    get_unified_market_hours,
    get_unified_market_movers,
    get_unified_quote,
    get_unified_stock_news,
)


@tool
async def get_quote(symbol: str):
    """Get real-time stock quote for a symbol."""
    quote = await get_unified_quote(symbol)
    if quote:
        return quote
    return {"symbol": symbol.upper(), "error": "No quote data available"}


@tool
async def get_historical_prices(symbol: str, days: int = 30):
    """Get daily historical prices for a symbol."""
    return await get_unified_history(symbol=symbol, days=days)


@tool
async def get_company_profile(symbol: str):
    """Get company profile and fundamental overview."""
    return await get_unified_company_profile(symbol)


@tool
async def get_market_movers():
    """Get top market movers."""
    movers = await get_unified_market_movers()
    return movers or {"gainers": [], "losers": []}


@tool
async def get_stock_news(symbol: str = None, limit: int = 5):
    """Get latest news articles for a stock symbol or broad market."""
    return await get_unified_stock_news(symbol=symbol, limit=limit)


@tool
async def get_market_hours(markets: list[str] | None = None):
    """Get market hours by market type (equity, option, forex, etc.)."""
    hours = await get_unified_market_hours(markets=markets)
    return hours or {}
