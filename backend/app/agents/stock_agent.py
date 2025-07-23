# stock_agent.py – MCP-compliant server for stock price queries

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from anthropic import AsyncAnthropic
import os
from pathlib import Path
from dotenv import load_dotenv
from ..services.schwab_client import get_stock_data, get_multiple_quotes, get_price_history, get_market_movers, get_market_hours

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

app = FastAPI()

async def analyze_query_with_llm(user_query: str) -> dict:
    """Use Claude to analyze the query and determine what type of stock data is needed"""
    system_prompt = """Analyze stock queries and return JSON:
{
  "query_type": "single_quote" | "multiple_quotes" | "price_history" | "market_movers" | "market_hours" | "unknown",
  "symbols": ["TICKER"], 
  "period": "1 month" | "3 months" | "6 months" | "1 year" | "YTD" | null,
  "index": "$SPX" | "$DJI" | "$COMPX" | "NASDAQ" | "NYSE" | null,
  "is_stock_related": true | false
}

Types:
- single_quote: One stock price
- multiple_quotes: Compare multiple stocks  
- price_history: Historical data, trends, performance over time
- market_movers: Top gainers/losers, trending stocks, market leaders
- market_hours: Trading schedules, market open/close times
- unknown: Not stock related

For market_movers: look for "gainers", "losers", "movers", "trending", "top stocks", "leaders", "volume", "most active"
- Detect index: "S&P 500"->$SPX, "Dow Jones"->$DJI, "NASDAQ"->$COMPX, "NYSE"->NYSE, "NASDAQ"->NASDAQ
- Detect sort: "volume"->VOLUME, "most active"->VOLUME, "gainers"->PERCENT_CHANGE_UP, "losers"->PERCENT_CHANGE_DOWN
For market_hours: look for "hours", "schedule", "open", "close", "trading times" """

    try:
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        
        import json
        result = json.loads(response.content[0].text.strip())
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing query: {e}")
        # Fallback to simple extraction - be more inclusive
        words = user_query.upper().split()
        symbols = []
        
        # Common non-stock words to exclude
        exclude_words = {
            "THE", "AND", "OR", "FOR", "WITH", "OVER", "PAST", "LAST", "THIS", "THAT", 
            "WHAT", "HOW", "WHEN", "WHERE", "WHY", "SHOW", "GET", "FIND", "TELL", 
            "PRICE", "STOCK", "SHARE", "MARKET", "QUOTE", "DATA", "INFO", "CHANGE",
            "PERCENT", "MONTH", "YEAR", "DAY", "WEEK", "TIME", "HISTORY",
            "TREND", "CHART", "GRAPH", "COMPARE", "VS"
        }
        
        for word in words:
            # Include anything that looks like a ticker (1-5 chars, all letters)
            if (1 <= len(word) <= 5 and 
                word.isalpha() and 
                word not in exclude_words and
                not word.lower() in ["a", "i", "to", "is", "of", "in", "on", "at", "up", "it", "my", "me", "we", "be", "do", "go", "so", "no"]):
                symbols.append(word)
        
        # Determine query type based on keywords
        query_lower = user_query.lower()
        has_history_keywords = any(keyword in query_lower for keyword in [
            "change", "performance", "history", "chart", "trend", "past", "last", 
            "over the", "since", "during", "period", "month", "year", "ytd"
        ])
        
        has_comparison_keywords = any(keyword in query_lower for keyword in [
            "compare", "vs", "versus", "against", "and", ",", "portfolio"
        ])
        
        has_movers_keywords = any(keyword in query_lower for keyword in [
            "gainers", "losers", "movers", "trending", "top stocks", "leaders", "winners",
            "volume", "most active", "trades", "most traded", "biggest", "worst"
        ])
        
        has_hours_keywords = any(keyword in query_lower for keyword in [
            "hours", "schedule", "open", "close", "trading times", "market open", "market close"
        ])
        
        query_type = "unknown"
        if has_movers_keywords:
            query_type = "market_movers"
        elif has_hours_keywords:
            query_type = "market_hours"
        elif symbols:
            if has_history_keywords:
                query_type = "price_history"
            elif len(symbols) > 1 or has_comparison_keywords:
                query_type = "multiple_quotes"
            elif len(symbols) == 1:
                query_type = "single_quote"
            else:
                query_type = "single_quote"  # Default to single quote if we have symbols
        
        # Check if query seems stock-related even without clear symbols
        is_stock_related = (len(symbols) > 0 or 
                           any(keyword in query_lower for keyword in [
                               "stock", "share", "ticker", "quote", "market", "trading", 
                               "equity", "investment", "portfolio", "dividend"
                           ]))
                
        return {
            "query_type": query_type,
            "symbols": symbols[:10],
            "period": "1 month" if has_history_keywords else None,
            "is_stock_related": is_stock_related
        }


class MCPRequest(BaseModel):
    input: str  # Claude sends the raw user query here
    state: dict | None = None  # Optional memory / conversation state


def convert_period_to_api_params(period_str: str) -> dict:
    """Convert user-friendly period to API parameters"""
    if not period_str:
        return {"period_type": "month", "period": 1, "frequency_type": "daily", "frequency": 1}
    
    period_lower = period_str.lower()
    if "ytd" in period_lower or "year to date" in period_lower:
        return {"period_type": "ytd", "period": 1, "frequency_type": "daily", "frequency": 1}
    elif "year" in period_lower or "12 month" in period_lower:
        return {"period_type": "year", "period": 1, "frequency_type": "daily", "frequency": 1}
    elif "6 month" in period_lower:
        return {"period_type": "month", "period": 6, "frequency_type": "daily", "frequency": 1}
    elif "3 month" in period_lower:
        return {"period_type": "month", "period": 3, "frequency_type": "daily", "frequency": 1}
    else:  # Default to 1 month
        return {"period_type": "month", "period": 1, "frequency_type": "daily", "frequency": 1}

def format_single_quote(data: dict) -> str:
    """Format a single stock quote"""
    return (
        f"📈 {data['symbol']} Quote:\n"
        f"Price: ${data['price']:.2f} ({data['change']:+.2f}, {data['percent_change']:+.2f}%)\n"
        f"High: ${data['high']:.2f}, Low: ${data['low']:.2f}, Open: ${data['open']:.2f}\n"
        f"52W Range: ${data['week_52_low']:.2f} - ${data['week_52_high']:.2f}\n"
        f"Trade Time: {data['trade_time']}"
    )

def format_multiple_quotes(quotes_data: dict) -> str:
    """Format multiple stock quotes for comparison"""
    if not quotes_data:
        return "❌ No quote data available"
        
    output = "📊 Stock Comparison:\n\n"
    for symbol, data in quotes_data.items():
        change_emoji = "🔴" if data['change'] < 0 else "🟢"
        output += (
            f"{change_emoji} {symbol}: ${data['price']:.2f} "
            f"({data['change']:+.2f}, {data['percent_change']:+.2f}%) "
            f"Vol: {data['volume']:,}\n"
        )
    return output.strip()

def format_price_history(history_data: dict) -> str:
    """Format price history data"""
    if not history_data or not history_data.get('candles'):
        return "❌ No historical data available"
        
    symbol = history_data['symbol']
    candles = history_data['candles']
    
    if len(candles) < 2:
        return f"❌ Insufficient historical data for {symbol}"
    
    # Get first and last candle for period performance
    first_candle = candles[0]
    last_candle = candles[-1]
    
    period_change = last_candle['close'] - first_candle['close']
    period_change_pct = (period_change / first_candle['close']) * 100
    
    # Calculate high/low for period
    period_high = max(candle['high'] for candle in candles)
    period_low = min(candle['low'] for candle in candles)
    
    change_emoji = "🔴" if period_change < 0 else "🟢"
    period_text = f"{history_data.get('period', 1)} {history_data.get('period_type', 'month')}(s)"
    
    return (
        f"📈 {symbol} - {period_text} Performance:\n"
        f"{change_emoji} Period Change: {period_change:+.2f} ({period_change_pct:+.2f}%)\n"
        f"Period High: ${period_high:.2f}\n"
        f"Period Low: ${period_low:.2f}\n"
        f"Current: ${last_candle['close']:.2f}\n"
        f"Data Points: {len(candles)} trading days"
    )

def format_market_movers(movers_data: dict) -> str:
    """Format market movers data"""
    if not movers_data or not movers_data.get('movers'):
        return "❌ No market movers data available"
        
    index = movers_data['index']
    sort_type = movers_data['sort']
    movers = movers_data['movers']
    
    if not movers:
        return f"❌ No movers data found for {index}"
        
    # Determine header based on sort type
    if "UP" in sort_type or "GAIN" in sort_type:
        header = f"🚀 Top Gainers ({index}):\n\n"
    elif "DOWN" in sort_type or "LOSS" in sort_type:
        header = f"📉 Top Losers ({index}):\n\n"
    elif "VOLUME" in sort_type:
        header = f"📈 Most Active by Volume ({index}):\n\n"
    elif "TRADES" in sort_type:
        header = f"⚡ Most Active by Trades ({index}):\n\n"
    else:
        header = f"📊 Market Movers ({index}):\n\n"
    
    output = header
    for i, mover in enumerate(movers[:10], 1):  # Top 10
        direction_emoji = "🟢" if mover['direction'] == "up" else "🔴"
        
        # Show different metrics based on sort type
        if "TRADES" in sort_type:
            metric = f"Trades: {mover.get('trades', 0):,}"
        elif "VOLUME" in sort_type:
            metric = f"Vol: {mover.get('volume', 0):,}"
        else:
            # For percent change, show percentage
            pct_change = (mover['change'] / (mover['last_price'] - mover['change'])) * 100 if mover['last_price'] != mover['change'] else 0
            metric = f"Vol: {mover.get('volume', 0):,}"
            
        output += (
            f"{i}. {direction_emoji} {mover['symbol']}: ${mover['last_price']:.2f} "
            f"({mover['change']:+.2f}) {metric}\n"
        )
        
    return output.strip()

def format_market_hours(hours_data: dict) -> str:
    """Format market hours data"""
    if not hours_data:
        return "❌ No market hours data available"
        
    output = "🕐 Market Hours:\n\n"
    
    for market_type, market_info in hours_data.items():
        if market_type == "note":
            continue
            
        market_name = market_type.title()
        output += f"**{market_name} Market:**\n"
        
        for product, details in market_info.items():
            product_name = details.get('product_name', product).title()
            is_open = details.get('is_open', False)
            status = "🟢 OPEN" if is_open else "🔴 CLOSED"
            
            output += f"  {product_name}: {status}\n"
            
            session_hours = details.get('session_hours', {})
            for session_name, times in session_hours.items():
                if times:
                    session_display = session_name.replace('Market', ' Market').title()
                    for time_slot in times:
                        start = time_slot.get('start', '').split('T')[1][:5] if 'T' in time_slot.get('start', '') else ''
                        end = time_slot.get('end', '').split('T')[1][:5] if 'T' in time_slot.get('end', '') else ''
                        if start and end:
                            output += f"    {session_display}: {start} - {end}\n"
            output += "\n"
    
    if "note" in hours_data:
        output += f"ℹ️  {hours_data['note']}"
        
    return output.strip()

@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
        mcp_input = MCPRequest(**body)

        # Analyze the query to determine what type of data is needed
        analysis = await analyze_query_with_llm(mcp_input.input)
        
        if not analysis['is_stock_related']:
            return JSONResponse(content={"output": "❌ This doesn't appear to be a stock-related query. Try asking about stock prices, comparisons, or historical performance."})
        
        # Only require symbols for certain query types
        if not analysis['symbols'] and analysis['query_type'] in ['single_quote', 'multiple_quotes', 'price_history']:
            return JSONResponse(content={"output": "❌ No stock symbols found in your query. Please specify stock tickers or company names."})
        
        # Handle different query types
        if analysis['query_type'] == 'single_quote':
            symbol = analysis['symbols'][0]
            data = get_stock_data(symbol)
            if not data:
                return JSONResponse(content={"output": f"❌ Could not find data for symbol '{symbol}'. Please check if it's a valid stock ticker. Try searching for the company's official ticker symbol."})
            output = format_single_quote(data)
            
        elif analysis['query_type'] == 'multiple_quotes':
            symbols = analysis['symbols']
            data = get_multiple_quotes(symbols)
            if not data:
                return JSONResponse(content={"output": f"❌ Could not find data for any of these symbols: {', '.join(symbols)}. Please verify the ticker symbols are correct."})
            
            # Show partial results if some symbols failed
            failed_symbols = [s for s in symbols if s not in data]
            if failed_symbols:
                output = format_multiple_quotes(data)
                output += f"\n\n⚠️  Could not find data for: {', '.join(failed_symbols)}"
            else:
                output = format_multiple_quotes(data)
            
        elif analysis['query_type'] == 'price_history':
            symbol = analysis['symbols'][0]  # Use first symbol for history
            api_params = convert_period_to_api_params(analysis['period'])
            data = get_price_history(symbol, **api_params)
            if not data:
                return JSONResponse(content={"output": f"❌ Could not find historical data for symbol '{symbol}'. Please verify the ticker symbol is correct, or try a different time period."})
            output = format_price_history(data)
            
        elif analysis['query_type'] == 'market_movers':
            # Determine index and sort type from query
            index = analysis.get('index') or '$SPX'
            
            # Enhanced keyword detection for sort type
            query_lower = mcp_input.input.lower()
            
            # Determine sort type based on keywords
            if any(word in query_lower for word in ['volume', 'most active', 'highest volume', 'trading volume']):
                sort_type = "VOLUME"
            elif any(word in query_lower for word in ['trades', 'most traded', 'trading activity']):
                sort_type = "TRADES"
            elif any(word in query_lower for word in ['loser', 'down', 'decline', 'drop', 'worst', 'falling']):
                sort_type = "PERCENT_CHANGE_DOWN"
            else:
                sort_type = "PERCENT_CHANGE_UP"  # Default to gainers
            
            # Detect frequency hints in query (supports 0, 1, 5, 10, 30, 60)
            frequency = 1  # Default
            
            # Check for explicit frequency values
            import re
            freq_match = re.search(r'\b(0|1|5|10|30|60)%?\b', query_lower)
            if freq_match:
                frequency = int(freq_match.group(1))
            # Check for descriptive frequency hints
            elif any(word in query_lower for word in ['major moves', 'big moves', 'significant moves']):
                frequency = 10  # Major moves >= 10%
            elif any(word in query_lower for word in ['moderate moves', 'medium moves']):
                frequency = 5   # Moderate moves >= 5%
            elif any(word in query_lower for word in ['all moves', 'any moves', 'small moves', 'minor moves']):
                frequency = 0   # Show all moves
            elif any(word in query_lower for word in ['substantial moves', 'huge moves']):
                frequency = 30  # Substantial moves >= 30%
            elif any(word in query_lower for word in ['extreme moves', 'massive moves']):
                frequency = 60  # Extreme moves >= 60%
            
            # Debug output showing what parameters were detected/defaulted
            debug_info = f"🔧 Parameters: Index='{index}' (detected: {analysis.get('index', 'None, defaulted to $SPX')}), Sort='{sort_type}', Frequency={frequency}"
                
            data = get_market_movers(index=index, sort=sort_type, frequency=frequency)
            if not data or not data.get('movers'):
                return JSONResponse(content={"output": f"❌ Could not find market movers data for {index}. Please try again later."})
            
            # Add debug info to output
            output = format_market_movers(data) + f"\n\n{debug_info}"
            
        elif analysis['query_type'] == 'market_hours':
            query_lower = mcp_input.input.lower()
            
            # Detect specific market types from query
            detected_markets = []
            single_market = None
            
            # Check for specific market mentions
            if any(word in query_lower for word in ['equity', 'stock', 'stocks']):
                detected_markets.append('equity')
                single_market = 'equity' if len([w for w in query_lower.split() if w in ['equity', 'stock', 'stocks']]) == 1 else None
                
            if any(word in query_lower for word in ['option', 'options']):
                detected_markets.append('option')
                single_market = 'option' if 'option' in query_lower and len(detected_markets) == 0 else None
                
            if any(word in query_lower for word in ['bond', 'bonds']):
                detected_markets.append('bond')
                single_market = 'bond' if 'bond' in query_lower and len(detected_markets) == 0 else None
                
            if any(word in query_lower for word in ['future', 'futures']):
                detected_markets.append('future')
                single_market = 'future' if 'future' in query_lower and len(detected_markets) == 0 else None
                
            if any(word in query_lower for word in ['forex', 'fx', 'currency']):
                detected_markets.append('forex')
                single_market = 'forex' if any(w in query_lower for w in ['forex', 'fx']) and len(detected_markets) == 0 else None
            
            # Extract date if provided (format: YYYY-MM-DD)
            import re
            date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', mcp_input.input)
            date = date_match.group(1) if date_match else None
            
            # Default to equity and options if no specific markets detected
            if not detected_markets:
                detected_markets = ['equity', 'option']
            
            # Use single market endpoint if only one market requested
            if single_market:
                data = get_market_hours(single_market=single_market, date=date)
            else:
                data = get_market_hours(markets=detected_markets, date=date)
                
            if not data:
                return JSONResponse(content={"output": "❌ Could not find market hours data. Please try again later."})
            output = format_market_hours(data)
            
        else:
            return JSONResponse(content={"output": "❌ Unable to determine what stock information you're looking for. Try asking for specific stock prices, comparisons, historical data, market movers, or trading hours."})

        return {"output": output}

    except Exception as e:
        return JSONResponse(status_code=500, content={"output": f"❌ Error: {e}"})
