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

def get_market_movers(index: str = "$SPX", sort: str = "PERCENT_CHANGE_UP", frequency: int = 0) -> dict | None:
    """Get top 10 market movers for a specific index
    
    Supported indices: $SPX, $DJI, $COMPX, NYSE, NASDAQ, OTCBB, 
                      INDEX_ALL, EQUITY_ALL, OPTION_ALL, OPTION_PUT, OPTION_CALL
    Supported sorts: VOLUME, TRADES, PERCENT_CHANGE_UP, PERCENT_CHANGE_DOWN  
    Supported frequencies: 0, 1, 5, 10, 30, 60 (minutes)
    """
    try:
        # Build parameters exactly as shown in the API documentation
        # The API expects 'sort' and 'frequency' as URL parameters
        
        # API call with proper parameters matching Schwab documentation
        
        # Try calling with explicit parameters matching the API docs
        if sort == "VOLUME" and frequency > 0:
            # This matches your working curl example
            resp = client.get_movers(index, sort_order=sort, frequency=frequency)
        elif sort != "PERCENT_CHANGE_UP":
            resp = client.get_movers(index, sort_order=sort)
        elif frequency > 0:
            resp = client.get_movers(index, frequency=frequency) 
        else:
            resp = client.get_movers(index)
        
        if resp.status_code != httpx.codes.OK:
            return get_fallback_market_movers(index)
            
        data = resp.json()
        
        if not data.get("screeners"):
            return get_fallback_market_movers(index)
            
        # The API already returns data sorted by the requested sort parameter
        # No need to re-sort, just use the order provided by Schwab API
        sorted_movers = data["screeners"]
            
        return {
            "index": index,
            "sort": sort,
            "frequency": frequency,
            "movers": [
                {
                    "symbol": mover["symbol"],
                    "description": mover["description"], 
                    "last_price": mover["lastPrice"],
                    "change": mover["netChange"],
                    "direction": "up" if mover["netChange"] > 0 else "down",
                    "volume": mover["volume"],  # Individual stock volume
                    "trades": mover.get("trades", 0),  # Number of trades
                    "total_volume": mover["totalVolume"]  # Total market volume
                }
                for mover in sorted_movers[:10]  # Top 10
            ]
        }
        
    except Exception as e:
        print(f"❌ Error fetching market movers for {index}: {e}")
        return get_fallback_market_movers(index)

def get_market_hours(markets: list[str] = None, date: str = None, single_market: str = None) -> dict | None:
    """Get market hours for specified markets
    
    Supports both bulk endpoint (multiple markets) and single market endpoint
    Valid markets: equity, option, bond, future, forex
    """
    try:
        # If single_market is specified, use the existing method with single market
        if single_market:
            if single_market not in ["equity", "option", "bond", "future", "forex"]:
                print(f"❌ Invalid market: {single_market}. Valid markets: equity, option, bond, future, forex")
                return get_fallback_market_hours()
                
            # Use existing method with single market as list
            params = {"markets": [single_market]}
            if date:
                params["date"] = date
                
            print(f"🔧 Calling get_market_hours (single) with params: {params}")
            resp = client.get_market_hours(**params)
            print(f"🔧 Response status: {resp.status_code}")
            
        else:
            # Use bulk endpoint for multiple markets
            if markets is None:
                markets = ["equity", "option"]
                
            # Validate markets
            valid_markets = {"equity", "option", "bond", "future", "forex"}
            invalid_markets = [m for m in markets if m not in valid_markets]
            if invalid_markets:
                print(f"❌ Invalid markets: {invalid_markets}. Valid markets: {valid_markets}")
                return get_fallback_market_hours()
            
            # The schwab-py library expects markets as a list, not a comma-separated string
            params = {"markets": markets}
            if date:
                params["date"] = date
                
            print(f"🔧 Calling get_market_hours with params: {params}")
            resp = client.get_market_hours(**params)
            print(f"🔧 Response status: {resp.status_code}")
        
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Market hours API call failed with status {resp.status_code}")
            return get_fallback_market_hours()
            
        data = resp.json()
        print(f"🔧 Market hours response data: {data}")
        
        # Format the response for easier consumption
        formatted_hours = {}
        for market_type, market_data in data.items():
            formatted_hours[market_type] = {}
            for product, details in market_data.items():
                formatted_hours[market_type][product] = {
                    "date": details["date"],
                    "product_name": details["productName"],
                    "is_open": details["isOpen"],
                    "session_hours": details.get("sessionHours", {})
                }
                
        print(f"🔧 Formatted market hours: {formatted_hours}")
        return formatted_hours
        
    except Exception as e:
        print(f"❌ Error fetching market hours: {e}")
        return get_fallback_market_hours()

def get_fallback_market_movers(index: str) -> dict | None:
    """Fallback for market movers - simplified version"""
    try:
        # This is a basic fallback - in a real implementation you might use another API
        return {
            "index": index,
            "sort": "PERCENT_CHANGE_UP", 
            "frequency": 0,
            "movers": [],
            "note": "Market movers data unavailable - using fallback"
        }
    except Exception as e:
        print(f"❌ Fallback market movers error: {e}")
        return None

def get_fallback_market_hours() -> dict | None:
    """Fallback for market hours - basic trading schedule"""
    try:
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "equity": {
                "EQ": {
                    "date": current_date,
                    "product_name": "equity",
                    "is_open": True,  # Simplified - would need real market calendar
                    "session_hours": {
                        "regularMarket": [
                            {
                                "start": f"{current_date}T09:30:00-05:00",
                                "end": f"{current_date}T16:00:00-05:00"
                            }
                        ]
                    }
                }
            },
            "note": "Market hours data unavailable - using fallback"
        }
    except Exception as e:
        print(f"❌ Fallback market hours error: {e}")
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
