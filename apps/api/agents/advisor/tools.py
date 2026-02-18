from langchain_core.tools import tool
from apps.api.agents.market_data.tools import get_company_profile, get_quote, get_historical_prices, get_stock_news

# The Advisor agent will primarily use tools from other domains to gather context.
# We re-export them here for clarity and to potentially wrap them with specific logic later.

@tool
async def market_context_snapshot(symbol: str):
    """Build a quick market context snapshot from profile + quote + recent history."""
    profile = await get_company_profile.ainvoke({"symbol": symbol})
    quote = await get_quote.ainvoke({"symbol": symbol})
    history = await get_historical_prices.ainvoke({"symbol": symbol, "days": 10})
    return {
        "profile": profile,
        "quote": quote,
        "history_points": len(history or []),
    }

advisor_tools = [
    get_company_profile,
    get_quote,
    get_historical_prices,
    get_stock_news,
    market_context_snapshot,
]
