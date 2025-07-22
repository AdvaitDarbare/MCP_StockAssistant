# backend/schwab_client.py
import os
from datetime import datetime
from schwab.auth import easy_client
# BaseClient import removed since we're using enforce_enums=False
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

client = easy_client(
    api_key=os.getenv("SCHWAB_CLIENT_ID"),
    app_secret=os.getenv("SCHWAB_CLIENT_SECRET"),
    callback_url=os.getenv("SCHWAB_REDIRECT_URI"),
    token_path="/tmp/token.json",
    enforce_enums=False
)

def get_stock_data(symbol: str) -> dict | None:
    try:
        # Try Schwab API first
        resp = client.get_quotes(symbol)
        if resp.status_code != httpx.codes.OK:
            return get_fallback_stock_data(symbol)

        data = resp.json()
        if symbol not in data or "quote" not in data[symbol]:
            return get_fallback_stock_data(symbol)

        q = data[symbol]["quote"]
        return {
            "symbol": symbol,
            "price": q["lastPrice"],
            "change": q["netChange"],
            "percent_change": q["netPercentChange"],
            "volume": q["totalVolume"],
            "bid": q["bidPrice"],
            "ask": q["askPrice"],
            "open": q["openPrice"],
            "close": q["closePrice"],
            "high": q["highPrice"],
            "low": q["lowPrice"],
            "week_52_high": q["52WeekHigh"],
            "week_52_low": q["52WeekLow"],
            "trade_time": datetime.fromtimestamp(q["tradeTime"] / 1000).isoformat()
        }
    except Exception as e:
        print(f"❌ Error fetching quote for {symbol}: {e}")
        return get_fallback_stock_data(symbol)

def get_multiple_quotes(symbols: list[str]) -> dict:
    """Get quotes for multiple symbols at once"""
    try:
        symbols_str = ",".join(symbols)
        resp = client.get_quotes(symbols_str)
        
        if resp.status_code != httpx.codes.OK:
            return get_fallback_multiple_quotes(symbols)
            
        data = resp.json()
        result = {}
        
        for symbol in symbols:
            if symbol in data and "quote" in data[symbol]:
                q = data[symbol]["quote"]
                result[symbol] = {
                    "symbol": symbol,
                    "price": q["lastPrice"],
                    "change": q["netChange"],
                    "percent_change": q["netPercentChange"],
                    "volume": q["totalVolume"],
                    "bid": q["bidPrice"],
                    "ask": q["askPrice"],
                    "open": q["openPrice"],
                    "close": q["closePrice"],
                    "high": q["highPrice"],
                    "low": q["lowPrice"],
                    "week_52_high": q["52WeekHigh"],
                    "week_52_low": q["52WeekLow"],
                    "trade_time": datetime.fromtimestamp(q["tradeTime"] / 1000).isoformat()
                }
            else:
                fallback = get_fallback_stock_data(symbol)
                if fallback:
                    result[symbol] = fallback
                    
        return result
        
    except Exception as e:
        print(f"❌ Error fetching multiple quotes: {e}")
        return get_fallback_multiple_quotes(symbols)

def get_price_history(symbol: str, period_type: str = "month", period: int = 1, 
                     frequency_type: str = "daily", frequency: int = 1) -> dict | None:
    """Get historical price data for a symbol"""
    try:
        # With enforce_enums=False, we can use strings directly
        resp = client.get_price_history(
            symbol=symbol,
            period_type=period_type,
            period=period,
            frequency_type=frequency_type,
            frequency=frequency
        )
        
        if resp.status_code != httpx.codes.OK:
            return get_fallback_price_history(symbol, period_type, period)
            
        data = resp.json()
        
        if not data.get("candles"):
            return get_fallback_price_history(symbol, period_type, period)
            
        return {
            "symbol": symbol,
            "candles": [
                {
                    "datetime": datetime.fromtimestamp(candle["datetime"] / 1000).isoformat(),
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"]
                }
                for candle in data["candles"]
            ],
            "period_type": period_type,
            "period": period,
            "frequency_type": frequency_type,
            "frequency": frequency
        }
        
    except Exception as e:
        print(f"❌ Error fetching price history for {symbol}: {e}")
        return get_fallback_price_history(symbol, period_type, period)

def get_fallback_multiple_quotes(symbols: list[str]) -> dict:
    """Fallback for multiple quotes using individual API calls"""
    result = {}
    for symbol in symbols:
        data = get_fallback_stock_data(symbol)
        if data:
            result[symbol] = data
    return result

def get_fallback_price_history(symbol: str, period_type: str, period: int) -> dict | None:
    """Fallback price history using free API"""
    try:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey=demo"
        
        with httpx.Client() as http_client:
            response = http_client.get(url)
            if response.status_code != 200:
                return None
                
            data = response.json()
            if not data.get("historical"):
                return None
                
            # Limit to requested period (approximate)
            limit = 30 if period_type == "month" else 252 if period_type == "year" else 10
            historical = data["historical"][:limit * period]
            
            return {
                "symbol": symbol,
                "candles": [
                    {
                        "datetime": h["date"] + "T16:00:00",
                        "open": h["open"],
                        "high": h["high"], 
                        "low": h["low"],
                        "close": h["close"],
                        "volume": h["volume"]
                    }
                    for h in historical
                ],
                "period_type": period_type,
                "period": period,
                "frequency_type": "daily",
                "frequency": 1
            }
            
    except Exception as e:
        print(f"❌ Fallback price history error for {symbol}: {e}")
        return None

def get_fallback_stock_data(symbol: str) -> dict | None:
    """Fallback using free financial data API for development"""
    try:
        # Using Yahoo Finance alternative - financialmodelingprep free tier
        url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=demo"
        
        with httpx.Client() as http_client:
            response = http_client.get(url)
            if response.status_code != 200:
                return None
                
            data = response.json()
            if not data or len(data) == 0:
                return None
                
            q = data[0]
            return {
                "symbol": symbol,
                "price": q.get("price", 0),
                "change": q.get("change", 0),
                "percent_change": q.get("changesPercentage", 0),
                "volume": q.get("volume", 0),
                "bid": q.get("price", 0),
                "ask": q.get("price", 0),
                "open": q.get("open", 0),
                "close": q.get("previousClose", 0),
                "high": q.get("dayHigh", 0),
                "low": q.get("dayLow", 0),
                "week_52_high": q.get("yearHigh", 0),
                "week_52_low": q.get("yearLow", 0),
                "trade_time": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"❌ Fallback API error for {symbol}: {e}")
        return None
