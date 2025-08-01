import os
from datetime import datetime
from schwab.auth import easy_client
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Initialize Schwab client with proper error handling
client = None
token_path = "/tmp/token.json"

try:
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
        print("⚠️ Schwab credentials not available or token missing")
        print("⚠️ Run setup_schwab_auth.py to authenticate first")
        
except Exception as e:
    print(f"⚠️ Failed to initialize Schwab client: {e}")
    client = None

def get_stock_data(symbol: str) -> dict | None:
    """Get real-time stock quote data from Schwab API"""
    if not client:
        print("❌ Schwab client not initialized. Run setup_schwab_auth.py first.")
        return None
        
    try:
        resp = client.get_quotes(symbol)
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Schwab API error for {symbol}: HTTP {resp.status_code}")
            return None

        data = resp.json()
        if symbol not in data or "quote" not in data[symbol]:
            print(f"❌ No quote data found for {symbol}")
            return None

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
        return None

def get_multiple_quotes(symbols: list[str]) -> dict:
    """Get quotes for multiple symbols at once from Schwab API"""
    if not client:
        print("❌ Schwab client not initialized. Run setup_schwab_auth.py first.")
        return {}
        
    try:
        symbols_str = ",".join(symbols)
        resp = client.get_quotes(symbols_str)
        
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Schwab API error for multiple quotes: HTTP {resp.status_code}")
            return {}
            
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
                print(f"❌ No quote data found for {symbol}")
                
        return result
        
    except Exception as e:
        print(f"❌ Error fetching multiple quotes: {e}")
        return {}

def get_price_history(symbol: str, period_type: str = "month", period: int = 1, 
                     frequency_type: str = "daily", frequency: int = 1) -> dict | None:
    """Get historical price data for a symbol from Schwab API"""
    if not client:
        print("❌ Schwab client not initialized. Run setup_schwab_auth.py first.")
        return None
        
    try:
        resp = client.get_price_history(
            symbol=symbol,
            period_type=period_type,
            period=period,
            frequency_type=frequency_type,
            frequency=frequency
        )
        
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Schwab API error for price history {symbol}: HTTP {resp.status_code}")
            return None
            
        data = resp.json()
        
        if not data.get("candles"):
            print(f"❌ No price history data found for {symbol}")
            return None
            
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
        return None

def get_market_movers(index: str = "$SPX", sort: str = "PERCENT_CHANGE_UP", frequency: int = 0) -> dict | None:
    """Get top 10 market movers for a specific index from Schwab API
    
    Supported indices: $SPX, $DJI, $COMPX, NYSE, NASDAQ, OTCBB, 
                      INDEX_ALL, EQUITY_ALL, OPTION_ALL, OPTION_PUT, OPTION_CALL
    Supported sorts: VOLUME, TRADES, PERCENT_CHANGE_UP, PERCENT_CHANGE_DOWN  
    Supported frequencies: 0, 1, 5, 10, 30, 60 (minutes)
    """
    if not client:
        print("❌ Schwab client not initialized. Run setup_schwab_auth.py first.")
        return None
        
    try:
        if sort == "VOLUME" and frequency > 0:
            resp = client.get_movers(index, sort_order=sort, frequency=frequency)
        elif sort != "PERCENT_CHANGE_UP":
            resp = client.get_movers(index, sort_order=sort)
        elif frequency > 0:
            resp = client.get_movers(index, frequency=frequency) 
        else:
            resp = client.get_movers(index)
        
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Schwab API error for market movers {index}: HTTP {resp.status_code}")
            return None
            
        data = resp.json()
        
        if not data.get("screeners"):
            print(f"❌ No market movers data found for {index}")
            return None
            
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
                    "volume": mover["volume"],
                    "trades": mover.get("trades", 0),
                    "total_volume": mover["totalVolume"]
                }
                for mover in sorted_movers[:10]
            ]
        }
        
    except Exception as e:
        print(f"❌ Error fetching market movers for {index}: {e}")
        return None

def get_market_hours(markets: list[str] = None, date: str = None, single_market: str = None) -> dict | None:
    """Get market hours for specified markets from Schwab API
    
    Supports both bulk endpoint (multiple markets) and single market endpoint
    Valid markets: equity, option, bond, future, forex
    """
    if not client:
        print("❌ Schwab client not initialized. Run setup_schwab_auth.py first.")
        return None
        
    try:
        if single_market:
            if single_market not in ["equity", "option", "bond", "future", "forex"]:
                print(f"❌ Invalid market: {single_market}. Valid markets: equity, option, bond, future, forex")
                return None
                
            params = {"markets": [single_market]}
            if date:
                params["date"] = date
                
            resp = client.get_market_hours(**params)
            
        else:
            if markets is None:
                markets = ["equity", "option"]
                
            valid_markets = {"equity", "option", "bond", "future", "forex"}
            invalid_markets = [m for m in markets if m not in valid_markets]
            if invalid_markets:
                print(f"❌ Invalid markets: {invalid_markets}. Valid markets: {valid_markets}")
                return None
            
            params = {"markets": markets}
            if date:
                params["date"] = date
                
            resp = client.get_market_hours(**params)
        
        if resp.status_code != httpx.codes.OK:
            print(f"❌ Schwab API error for market hours: HTTP {resp.status_code}")
            return None
            
        data = resp.json()
        
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
                
        return formatted_hours
        
    except Exception as e:
        print(f"❌ Error fetching market hours: {e}")
        return None