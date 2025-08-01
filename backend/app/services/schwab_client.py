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

# Initialize Schwab client with proper error handling
client = None
try:
    # Only attempt Schwab client if credentials are available and token exists
    token_path = "/tmp/token.json"
    if (os.getenv("SCHWAB_CLIENT_ID") and 
        os.getenv("SCHWAB_CLIENT_SECRET") and 
        os.path.exists(token_path)):
        
        client = easy_client(
            api_key=os.getenv("SCHWAB_CLIENT_ID"),
            app_secret=os.getenv("SCHWAB_CLIENT_SECRET"),
            callback_url=os.getenv("SCHWAB_REDIRECT_URI"),
            token_path=token_path,
            enforce_enums=False
        )
        print("✅ Schwab client initialized successfully")
    else:
        print("⚠️ Schwab credentials not available or token missing - using fallback APIs only")
        
except Exception as e:
    print(f"⚠️ Failed to initialize Schwab client: {e}")
    print("🔄 Falling back to free APIs for stock data")
    client = None

def get_stock_data(symbol: str) -> dict | None:
    try:
        # Try Schwab API first if client is available
        if client:
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
        else:
            # Schwab client not available, use fallback directly
            return get_fallback_stock_data(symbol)
    except Exception as e:
        print(f"❌ Error fetching quote for {symbol}: {e}")
        return get_fallback_stock_data(symbol)

def get_multiple_quotes(symbols: list[str]) -> dict:
    """Get quotes for multiple symbols at once"""
    try:
        # Try Schwab API first if client is available
        if client:
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
        else:
            # Schwab client not available, use fallback directly
            return get_fallback_multiple_quotes(symbols)
        
    except Exception as e:
        print(f"❌ Error fetching multiple quotes: {e}")
        return get_fallback_multiple_quotes(symbols)

def get_price_history(symbol: str, period_type: str = "month", period: int = 1, 
                     frequency_type: str = "daily", frequency: int = 1) -> dict | None:
    """Get historical price data for a symbol"""
    try:
        # Try Schwab API first if client is available
        if client:
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
        else:
            # Schwab client not available, use fallback directly
            return get_fallback_price_history(symbol, period_type, period)
        
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
        # Try Schwab API first if client is available
        if client:
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
        else:
            # Schwab client not available, use fallback directly
            return get_fallback_market_movers(index)
        
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
            if client:
                resp = client.get_market_hours(**params)
                print(f"🔧 Response status: {resp.status_code}")
            else:
                return get_fallback_market_hours()
            
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
            if client:
                resp = client.get_market_hours(**params)
                print(f"🔧 Response status: {resp.status_code}")
            else:
                return get_fallback_market_hours()
        
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
    """Fallback providing sample data for testing when real APIs are unavailable"""
    try:
        print(f"📊 Using fallback data for {symbol}")
        
        # Sample stock prices for common symbols
        sample_data = {
            "AAPL": {"price": 230.85, "change": 2.15, "percent_change": 0.94, "volume": 45000000, "open": 228.70, "high": 232.10, "low": 227.50, "52w_high": 237.23, "52w_low": 164.08},
            "GOOGL": {"price": 175.42, "change": -1.23, "percent_change": -0.70, "volume": 28000000, "open": 176.65, "high": 177.89, "low": 174.10, "52w_high": 193.31, "52w_low": 121.46},
            "MSFT": {"price": 423.89, "change": 3.47, "percent_change": 0.83, "volume": 22000000, "open": 420.42, "high": 425.78, "low": 419.33, "52w_high": 468.35, "52w_low": 362.90},
            "TSLA": {"price": 248.98, "change": -5.67, "percent_change": -2.23, "volume": 95000000, "open": 254.65, "high": 256.44, "low": 247.22, "52w_high": 414.50, "52w_low": 138.80},
            "NVDA": {"price": 138.07, "change": 1.89, "percent_change": 1.39, "volume": 55000000, "open": 136.18, "high": 139.75, "low": 135.44, "52w_high": 152.89, "52w_low": 39.23},
            "AMZN": {"price": 207.09, "change": 0.84, "percent_change": 0.41, "volume": 31000000, "open": 206.25, "high": 208.77, "low": 205.10, "52w_high": 215.90, "52w_low": 118.35}
        }
        
        # Use sample data if available, otherwise generate mock data
        if symbol.upper() in sample_data:
            data = sample_data[symbol.upper()]
        else:
            # Generate mock data for unknown symbols
            import random
            base_price = random.uniform(50, 400)
            change = random.uniform(-10, 10)
            data = {
                "price": round(base_price, 2),
                "change": round(change, 2),
                "percent_change": round((change / base_price) * 100, 2),
                "volume": random.randint(1000000, 50000000),
                "open": round(base_price - random.uniform(-5, 5), 2),
                "high": round(base_price + random.uniform(0, 8), 2),
                "low": round(base_price - random.uniform(0, 8), 2),
                "52w_high": round(base_price * random.uniform(1.2, 1.8), 2),
                "52w_low": round(base_price * random.uniform(0.5, 0.8), 2)
            }
        
        return {
            "symbol": symbol.upper(),
            "price": data["price"],
            "change": data["change"],
            "percent_change": data["percent_change"],
            "volume": data["volume"],
            "bid": data["price"] - 0.01,
            "ask": data["price"] + 0.01,
            "open": data["open"],
            "close": data["price"] - data["change"],  # Previous close
            "high": data["high"],
            "low": data["low"],
            "week_52_high": data["52w_high"],
            "week_52_low": data["52w_low"],
            "trade_time": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Fallback data error for {symbol}: {e}")
        return None
