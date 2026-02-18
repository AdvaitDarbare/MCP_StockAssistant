import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from apps.api.config import settings
from apps.api.services.cache import cache_get_or_fetch

BASE_URL = "https://paper-api.alpaca.markets" if settings.ALPACA_PAPER else "https://api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets/v2"

def get_alpaca_headers():
    return {
        "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY
    }

async def get_alpaca_quote(symbol: str):
    """Get latest quote from Alpaca (using IEX feed for free tier)."""
    async def _fetch():
        headers = get_alpaca_headers()
        if not settings.ALPACA_API_KEY:
            return None
            
        async with httpx.AsyncClient() as client:
            # feed=iex is required for free tier to get real-time (though limited volume)
            url = f"{DATA_URL}/stocks/{symbol.upper()}/quotes/latest?feed=iex"
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    print(f"Alpaca API Error: {resp.status_code} - {resp.text}")
                    return None
                
                data = resp.json()
                q = data.get("quote")
                if not q:
                    return None
                
                # In Alpaca quotes: ap=ask price, bp=bid price
                # We'll use the mid-price or ask for "current price"
                price = q.get("ap") or q.get("bp")
                
                # Mock a change for the UI if not available directly
                # Real apps would pull previous close to calc change
                return {
                    "symbol": symbol.upper(),
                    "price": float(price) if price else 0.0,
                    "bid": float(q.get("bp", 0)),
                    "ask": float(q.get("ap", 0)),
                    "timestamp": q.get("t"),
                    # We will supplement these in the agent tools
                    "change": 0.0,
                    "percent_change": 0.0
                }
            except Exception as e:
                print(f"Alpaca Fetch Exception: {e}")
                return None
                
    return await cache_get_or_fetch(f"alpaca:quote:{symbol.upper()}", _fetch, "quote")

async def get_alpaca_history(symbol: str, timeframe="1Day", limit=100):
    """Get historical bars from Alpaca."""
    async def _fetch():
        headers = get_alpaca_headers()
        if not settings.ALPACA_API_KEY:
            return None
            
        async with httpx.AsyncClient() as client:
            # For free tier, we need iex feed and RFC3339 start
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            url = f"{DATA_URL}/stocks/{symbol.upper()}/bars"
            params = {
                "timeframe": timeframe,
                "limit": limit,
                "feed": "iex",
                "start": start_date
            }
            try:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    print(f"Alpaca History Error {resp.status_code}: {resp.text}")
                    return None
                
                data = resp.json()
                bars = data.get("bars", [])
                
                if not bars:
                    return None
                    
                return [
                    {
                        "date": b["t"].split("T")[0],
                        "open": float(b["o"]),
                        "high": float(b["h"]),
                        "low": float(b["l"]),
                        "close": float(b["c"]),
                        "volume": int(b["v"])
                    }
                    for b in bars
                ]
            except Exception as e:
                print(f"Alpaca History Exception: {e}")
                return None
                
    cache_key = f"alpaca:history:v4:{symbol.upper()}:{timeframe}"
    return await cache_get_or_fetch(cache_key, _fetch, "price_history")

async def get_alpaca_news(symbol: Optional[str] = None, limit: int = 5):
    """Get latest news from Alpaca News API."""
    async def _fetch():
        headers = get_alpaca_headers()
        url = "https://data.alpaca.markets/v1beta1/news"
        params = {"limit": limit}
        if symbol:
            params["symbols"] = symbol.upper()
            
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                news = data.get("news", [])
                return [
                    {
                        "headline": n.get("headline"),
                        "summary": n.get("summary"),
                        "source": n.get("source"),
                        "url": n.get("url"),
                        "timestamp": n.get("created_at"),
                        "symbols": n.get("symbols")
                    }
                    for n in news
                ]
            except Exception as e:
                print(f"Alpaca News Exception: {e}")
                return None
                
    cache_key = f"alpaca:news:{symbol if symbol else 'global'}:{limit}"
    return await cache_get_or_fetch(cache_key, _fetch, "news")

async def get_alpaca_movers(top: int = 10):
    """Get top market movers from Alpaca."""
    async def _fetch():
        headers = get_alpaca_headers()
        # Note: Movers might require a paid subscription or specific feed
        url = f"{DATA_URL}/stocks/movers"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                # Alpaca returns a list of movers
                gainers = data.get("gainers", [])
                losers = data.get("losers", [])
                return {
                    "gainers": gainers[:top],
                    "losers": losers[:top]
                }
            except Exception as e:
                print(f"Alpaca Movers Exception: {e}")
                return None
                
    return await cache_get_or_fetch("alpaca:movers", _fetch, "quote")
