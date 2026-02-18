from langchain_core.tools import tool
from apps.api.services.fred_client import get_key_indicators, get_series_data, search_series

@tool
async def get_macro_summary():
    """Get a summary of key macroeconomic indicators (GDP, CPI, Unemployment, Fed Funds, 10Y Treasury)."""
    return await get_key_indicators()

@tool
async def get_economic_series(series_id: str, limit: int = 12):
    """
    Get detailed data for a specific economic series from FRED.
    
    Args:
        series_id: The FRED Series ID (e.g., 'GDP', 'CPIAUCSL', 'UNRATE', 'DGS10').
        limit: Number of recent data points to retrieve (default: 12).
    """
    return await get_series_data(series_id, limit)

@tool
async def search_economic_data(query: str):
    """
    Search for economic data series in the FRED database.
    
    Args:
        query: Search term (e.g., 'inflation', 'housing starts', 'yield curve').
    """
    return await search_series(query)

macro_tools = [
    get_macro_summary,
    get_economic_series,
    search_economic_data
]
