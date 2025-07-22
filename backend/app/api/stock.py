# backend/routes/stock.py
from fastapi import APIRouter
from ..services.schwab_client import get_stock_data

router = APIRouter()

@router.get("/stock/{ticker}")
def get_stock(ticker: str):
    data = get_stock_data(ticker.upper())
    if not data:
        return {"error": f"Could not fetch data for {ticker}"}
    return data
