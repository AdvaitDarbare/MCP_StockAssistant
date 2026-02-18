from fastapi import APIRouter, HTTPException
from apps.api.agents.market_data.tools import (
    get_quote, 
    get_historical_prices, 
    get_company_profile,
    get_stock_news,
    get_market_movers,
    get_market_hours,
)
from apps.api.agents.technical_analysis.tools import analyze_technicals
from typing import Any

router = APIRouter()

@router.get("/market/quote/{symbol}")
async def fetch_quote(symbol: str):
    try:
        return await get_quote.ainvoke({"symbol": symbol})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/history/{symbol}")
async def fetch_history(symbol: str, days: int = 30):
    try:
        return await get_historical_prices.ainvoke({"symbol": symbol, "days": days})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/news/{symbol}")
async def fetch_news(symbol: str, limit: int = 5):
    try:
        return await get_stock_news.ainvoke({"symbol": symbol, "limit": limit})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/movers")
async def fetch_movers():
    try:
        return await get_market_movers.ainvoke({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/profile/{symbol}")
async def fetch_profile(symbol: str):
    try:
        return await get_company_profile.ainvoke({"symbol": symbol})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/technicals/{symbol}")
async def fetch_technicals(symbol: str, days: int = 180):
    try:
        history = await get_historical_prices.ainvoke({"symbol": symbol, "days": days})
        return await analyze_technicals.ainvoke({"symbol": symbol, "price_data": history})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/hours")
async def fetch_market_hours():
    try:
        return await get_market_hours.ainvoke({})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
