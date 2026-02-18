"""FRED Client for Macroeconomic Data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from apps.api.config import settings
from apps.api.services.cache import cache_get_or_fetch

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Common Series IDs
SERIES_MAP = {
    "gdp": "GDP",
    "cpi": "CPIAUCSL",
    "unemployment": "UNRATE",
    "fed_funds": "FEDFUNDS",
    "10y_treasury": "DGS10",
    "2y_treasury": "DGS2",
    "sp500": "SP500",
}

# ---------------------------------------------------------------------------
# Hardcoded metadata for the 7 well-known series — eliminates a second HTTP
# call to /fred/series per indicator (P-2).
# ---------------------------------------------------------------------------
_SERIES_METADATA: Dict[str, Dict[str, str]] = {
    "GDP":      {"title": "Gross Domestic Product",                      "units": "Billions of Dollars"},
    "CPIAUCSL": {"title": "Consumer Price Index for All Urban Consumers", "units": "Index 1982-1984=100"},
    "UNRATE":   {"title": "Unemployment Rate",                           "units": "Percent"},
    "FEDFUNDS": {"title": "Federal Funds Effective Rate",                 "units": "Percent"},
    "DGS10":    {"title": "10-Year Treasury Constant Maturity Rate",      "units": "Percent"},
    "DGS2":     {"title": "2-Year Treasury Constant Maturity Rate",       "units": "Percent"},
    "SP500":    {"title": "S&P 500",                                      "units": "Index"},
}


async def _fetch_fred(endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
    """Base fetch method for FRED API."""
    if not settings.FRED_API_KEY:
        logger.warning("FRED_API_KEY is not set.")
        return None

    params["api_key"] = settings.FRED_API_KEY
    params["file_type"] = "json"

    url = f"{FRED_BASE_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code != 200:
                logger.warning("FRED API Error: %s - %s", resp.status_code, resp.text[:200])
                return None
            return resp.json()
    except Exception as e:
        logger.warning("FRED API Request Failed: %s", e)
        return None


async def get_series_data(series_id: str, limit: int = 12) -> Optional[Dict]:
    """Get observations for a specific series.

    Uses hardcoded metadata for the 7 known series to avoid a second HTTP
    round-trip to /fred/series (P-2).  Falls back to a live API call for
    unknown series IDs.
    """
    # Normalize likely human-readable names to IDs if possible
    series_id = SERIES_MAP.get(series_id.lower(), series_id)

    cache_key = f"fred:series:{series_id}:{limit}"

    async def _fetch():
        data = await _fetch_fred("series/observations", {
            "series_id": series_id,
            "sort_order": "desc",
            "limit": limit,
        })

        if not data or "observations" not in data:
            return None

        # Use hardcoded metadata when available; otherwise fetch from API.
        if series_id in _SERIES_METADATA:
            meta = _SERIES_METADATA[series_id]
            title = meta["title"]
            units = meta["units"]
        else:
            info = await _fetch_fred("series", {"series_id": series_id})
            title = series_id
            units = ""
            if info and "seriess" in info:
                title = info["seriess"][0].get("title", series_id)
                units = info["seriess"][0].get("units", "")

        return {
            "series_id": series_id,
            "title": title,
            "units": units,
            "observations": [
                {
                    "date": obs["date"],
                    "value": float(obs["value"]) if obs["value"] != "." else None,
                }
                for obs in data["observations"]
            ],
        }

    return await cache_get_or_fetch(cache_key, _fetch, ttl_type="economic_data")


async def search_series(query: str, limit: int = 5) -> Optional[List[Dict]]:
    """Search for FRED series."""
    cache_key = f"fred:search:{query}"

    async def _fetch():
        data = await _fetch_fred("series/search", {
            "search_text": query,
            "limit": limit,
        })

        if not data or "seriess" not in data:
            return []

        return [
            {
                "id": s["id"],
                "title": s["title"],
                "frequency": s["frequency"],
                "units": s["units"],
            }
            for s in data["seriess"]
        ]

    return await cache_get_or_fetch(cache_key, _fetch, ttl_type="economic_data")


async def get_key_indicators() -> Dict[str, Any]:
    """Get a summary of key economic indicators (parallel fetch)."""
    import asyncio

    indicators = ["gdp", "cpi", "unemployment", "fed_funds", "10y_treasury"]
    tasks = [get_series_data(i, limit=1) for i in indicators]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("FRED Indicators fetch timed out.")
        results = [None] * len(indicators)

    summary: Dict[str, Any] = {}
    for i, res in enumerate(results):
        key = indicators[i]
        if res and res["observations"]:
            latest = res["observations"][0]
            summary[key] = {
                "value": latest["value"],
                "date": latest["date"],
                "title": res["title"],
                "units": res["units"],
            }

    return summary
