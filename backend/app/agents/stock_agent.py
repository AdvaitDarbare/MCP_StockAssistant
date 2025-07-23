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

def get_tool_description(tool_name: str) -> str:
    """Get human-readable description of stock market tools"""
    descriptions = {
        'get_stock_data': '📈 Get real-time quote and price data for a single stock',
        'get_multiple_quotes': '📊 Compare multiple stocks side-by-side with prices and changes',
        'get_price_history': '📉 Get historical price performance over time periods',
        'get_market_movers': '🚀 Get top gainers, losers, or most active stocks by volume',
        'get_market_hours': '🕐 Get trading schedules and market open/close status'
    }
    return descriptions.get(tool_name, f'🔧 Unknown tool: {tool_name}')

async def plan_and_execute_stock_tools(user_query: str) -> dict:
    """Use Claude to plan and execute stock market tools"""
    system_prompt = """You are a stock market assistant with access to these tools:

AVAILABLE TOOLS:
1. get_stock_data(symbol) - Get real-time quote for one stock
2. get_multiple_quotes(symbols) - Compare multiple stocks side-by-side  
3. get_price_history(symbol, period_type, period, frequency_type, frequency) - Historical performance
4. get_market_movers(index, sort, frequency) - Top gainers/losers/volume leaders
5. get_market_hours(markets, date) - Trading schedules and market status

Your job is to:
1. Extract relevant parameters from the user query
2. Determine what tools to call based on the request
3. Return a plan with the tools to execute

Return JSON:
{
  "tools_to_call": [
    {"tool": "get_market_movers", "params": {"index": "NASDAQ", "sort": "VOLUME", "frequency": 1}},
    {"tool": "get_stock_data", "params": {"symbol": "AAPL"}}
  ],
  "reasoning": "User wants market movers and a specific stock quote"
}

EXAMPLES:
- "AAPL stock price" → get_stock_data(AAPL)
- "Compare AAPL vs TSLA" → get_multiple_quotes([AAPL, TSLA])
- "NVDA performance last 6 months" → get_price_history(NVDA, month, 6, daily, 1)
- "Top gainers in NASDAQ" → get_market_movers(NASDAQ, PERCENT_CHANGE_UP, 1)
- "Most active stocks by volume" → get_market_movers($SPX, VOLUME, 1)
- "Market hours today" → get_market_hours([equity, option])

Extract numbers, time periods, indices, and sort preferences intelligently."""

    try:
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,  # Increased for tool planning
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        
        response_text = response.content[0].text.strip()
        print(f"🔧 Stock LLM Response: {response_text}")
        
        import json
        import re
        
        # Try to extract JSON from the response even if there's extra text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
        
        # If no JSON found, try parsing the whole response
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            print(f"❌ Could not extract valid JSON from response")
        
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
        
        # Simple fallback - create basic tool calls based on keywords
        query_lower = user_query.lower()
        tools_to_call = []
        
        # Market hours
        if any(keyword in query_lower for keyword in ["hours", "schedule", "open", "close", "trading times", "market open", "market close"]):
            tools_to_call.append({
                "tool": "get_market_hours",
                "params": {"markets": ["equity", "option"]}
            })
        
        # Market movers
        elif any(keyword in query_lower for keyword in ["gainers", "losers", "movers", "trending", "top stocks", "leaders", "winners", "volume", "most active", "trades", "biggest", "worst"]):
            sort_type = "VOLUME" if any(word in query_lower for word in ["volume", "most active"]) else "PERCENT_CHANGE_UP"
            tools_to_call.append({
                "tool": "get_market_movers", 
                "params": {"index": "$SPX", "sort": sort_type, "frequency": 1}
            })
        
        # Stock comparison
        elif len(symbols) > 1 or any(keyword in query_lower for keyword in ["compare", "vs", "versus", "against"]):
            if symbols:
                tools_to_call.append({
                    "tool": "get_multiple_quotes",
                    "params": {"symbols": symbols[:5]}
                })
        
        # Price history
        elif any(keyword in query_lower for keyword in ["performance", "history", "chart", "trend", "past", "month", "year"]) and symbols:
            tools_to_call.append({
                "tool": "get_price_history",
                "params": {"symbol": symbols[0], "period_type": "month", "period": 1, "frequency_type": "daily", "frequency": 1}
            })
        
        # Single stock quote
        elif len(symbols) == 1:
            tools_to_call.append({
                "tool": "get_stock_data",
                "params": {"symbol": symbols[0]}
            })
        
        return {"tools_to_call": tools_to_call}


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
        
        print(f"🔧 STOCK AGENT - Input received: '{mcp_input.input}'")  # Enhanced debug logging

        # Plan and execute using available stock tools
        plan = await plan_and_execute_stock_tools(mcp_input.input)
        print(f"🔧 STOCK AGENT - Plan generated: {plan}")
        
        if not plan.get('tools_to_call'):
            return JSONResponse(content={"output": "❌ I couldn't determine what stock information you're looking for. Try asking about stock prices, market data, or trading information."})
        
        # Execute the planned tools
        results = []
        
        for tool_call in plan['tools_to_call']:
            tool_name = tool_call['tool']
            params = tool_call['params']
            
            print(f"🔧 STOCK AGENT - Executing TOOL: {tool_name}")
            print(f"   📋 Tool Description: {get_tool_description(tool_name)}")
            print(f"   ⚙️  Parameters: {params}")
            
            try:
                if tool_name == 'get_stock_data':
                    data = get_stock_data(params['symbol'])
                    if data:
                        results.append(format_single_quote(data))
                        print(f"   ✅ Tool completed successfully - Got quote for {params['symbol']}")
                        
                elif tool_name == 'get_multiple_quotes':
                    symbols = params['symbols']
                    data = get_multiple_quotes(symbols)
                    if data:
                        results.append(format_multiple_quotes(data))
                        print(f"   ✅ Tool completed successfully - Compared {len(symbols)} stocks: {symbols}")
                        
                elif tool_name == 'get_price_history':
                    symbol = params['symbol']
                    period_type = params.get('period_type', 'month')
                    period = params.get('period', 1)
                    frequency_type = params.get('frequency_type', 'daily')
                    frequency = params.get('frequency', 1)
                    
                    data = get_price_history(symbol, period_type, period, frequency_type, frequency)
                    if data:
                        results.append(format_price_history(data))
                        print(f"   ✅ Tool completed successfully - Got {period} {period_type}(s) history for {symbol}")
                        
                elif tool_name == 'get_market_movers':
                    index = params.get('index', '$SPX')
                    sort = params.get('sort', 'PERCENT_CHANGE_UP')
                    frequency = params.get('frequency', 1)
                    
                    data = get_market_movers(index=index, sort=sort, frequency=frequency)
                    if data and data.get('movers'):
                        results.append(format_market_movers(data))
                        print(f"   ✅ Tool completed successfully - Got {len(data.get('movers', []))} market movers from {index}")
                        
                elif tool_name == 'get_market_hours':
                    markets = params.get('markets', ['equity', 'option'])
                    date = params.get('date')
                    
                    data = get_market_hours(markets=markets, date=date)
                    if data:
                        results.append(format_market_hours(data))
                        print(f"   ✅ Tool completed successfully - Got market hours for {len(markets)} market types")
                        
            except Exception as e:
                error_msg = f"❌ Error calling {tool_name}: {str(e)}"
                results.append(error_msg)
                print(f"   🚨 Tool failed: {error_msg}")
        
        if not results:
            return JSONResponse(content={"output": "❌ Could not retrieve any stock data. Please verify your request and try again."})
        
        # Combine all results
        if len(results) == 1:
            output = results[0]  # Single tool result, use as-is
        else:
            # Multiple tools, combine with separators
            output = "📊 Stock Market Analysis\n\n"
            output += f"\n\n{'='*50}\n\n".join(results)

        print(f"🔧 STOCK AGENT - Final output length: {len(output)} chars")
        print(f"🎉 STOCK AGENT - Successfully processed query using {len(plan['tools_to_call'])} tool(s)")
        return {"output": output}

    except Exception as e:
        return JSONResponse(status_code=500, content={"output": f"❌ Error: {e}"})
