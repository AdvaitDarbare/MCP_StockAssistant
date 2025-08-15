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

async def generate_stock_follow_up_suggestions(tools_used: list, symbols: list = None, user_query: str = "") -> str:
    """Generate intelligent follow-up question suggestions for stock queries with LLM validation"""
    # All available stock tools
    stock_tools = {
        'get_stock_data': 'Get current stock price and quote',
        'get_multiple_quotes': 'Compare multiple stocks side-by-side',
        'get_price_history': 'Get historical price performance',
        'get_market_movers': 'Get top gainers, losers, most active',
        'get_market_hours': 'Get trading hours and schedules'
    }
    
    # Find unused stock tools
    unused_tools = [tool for tool in stock_tools.keys() if tool not in tools_used]
    primary_symbol = symbols[0] if symbols and len(symbols) > 0 else "AAPL"
    
    # Create base suggestions
    base_suggestions = []
    
    # Add unused stock tool suggestions
    for tool in unused_tools[:2]:  # Limit to 2 stock suggestions
        if tool == 'get_stock_data' and symbols and len(symbols) > 1:
            base_suggestions.append(f"What's {primary_symbol} current stock price?")
        elif tool == 'get_multiple_quotes' and symbols and len(symbols) == 1:
            base_suggestions.append(f"Compare {primary_symbol} vs GOOGL vs MSFT")
        elif tool == 'get_price_history':
            base_suggestions.append(f"Show me 6 month price history for {primary_symbol}")
        elif tool == 'get_market_movers':
            base_suggestions.append(f"Show me today's top market gainers")
        elif tool == 'get_market_hours':
            base_suggestions.append(f"What are market hours today?")
    
    # Add cross-domain suggestions (equity insights)
    if symbols and len(symbols) > 0:
        base_suggestions.extend([
            f"Tell me about {primary_symbol} company",
            f"Recent news for {primary_symbol}",
            f"Analyst ratings for {primary_symbol}"
        ])
    
    # Use LLM to validate and refine suggestions  
    try:
        validation_prompt = f"""Given this stock market query: "{user_query}"
And the tools already used: {tools_used}
For symbols: {symbols or ['general market']}

From these potential follow-up suggestions:
{chr(10).join([f"- {s}" for s in base_suggestions])}

Select and refine the 3-4 most relevant, natural follow-up questions that:
1. Are directly answerable by our stock market and equity analysis tools
2. Provide complementary information to what was already shown  
3. Sound natural and conversational
4. Are relevant to the user's trading/investment interests

Return ONLY a numbered list with emojis, like:
1. 📊 Compare {primary_symbol} vs GOOGL vs MSFT
2. 📉 Show me 6 month history for {primary_symbol}
3. 🏢 Tell me about {primary_symbol} company"""

        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0.3,
            messages=[{"role": "user", "content": validation_prompt}]
        )
        
        llm_suggestions = response.content[0].text.strip()
        
        # Validate that LLM returned a proper numbered list
        if any(char.isdigit() and '. ' in llm_suggestions for char in llm_suggestions):
            return f"\n\n__FOLLOW_UPS_START__\n{llm_suggestions}\n__FOLLOW_UPS_END__"
            
    except Exception as e:
        print(f"⚠️ LLM validation failed, using fallback suggestions: {e}")
    
    # Fallback to hardcoded suggestions if LLM fails
    if not base_suggestions:
        return ""
    
    # Format for frontend parsing
    formatted_suggestions = []
    for i, suggestion in enumerate(base_suggestions[:4], 1):
        # Add appropriate emoji based on content
        if 'price' in suggestion.lower() and 'history' not in suggestion.lower():
            emoji = "📈"
        elif 'compare' in suggestion.lower():
            emoji = "📊"
        elif 'history' in suggestion.lower():
            emoji = "📉"
        elif 'movers' in suggestion.lower() or 'gainers' in suggestion.lower():
            emoji = "🚀"
        elif 'hours' in suggestion.lower():
            emoji = "🕐"
        elif 'company' in suggestion.lower():
            emoji = "🏢"
        elif 'news' in suggestion.lower():
            emoji = "📰"
        elif 'analyst' in suggestion.lower():
            emoji = "📊"
        else:
            emoji = "🔍"
        
        formatted_suggestions.append(f"{i}. {emoji} {suggestion}")
    
    suggestions_text = "\n".join(formatted_suggestions)
    return f"\n\n__FOLLOW_UPS_START__\n{suggestions_text}\n__FOLLOW_UPS_END__"

async def plan_and_execute_stock_tools(user_query: str) -> dict:
    """Use Claude to plan and execute stock market tools"""
    system_prompt = """You are a stock market assistant. Return ONLY ONE tool that matches the user's stock-related request.

AVAILABLE TOOLS:
1. get_stock_data(symbol) - For getting a single stock's current price/quote
2. get_multiple_quotes(symbols) - For comparing 2+ stocks side-by-side  
3. get_price_history(symbol, period_type, period, frequency_type, frequency) - For historical price data
4. get_market_movers(index, sort, frequency) - For market-wide lists (gainers/losers/volume)
5. get_market_hours(markets, date) - For trading schedule information

CRITICAL RULES:
- Return ONLY ONE tool per request
- If user asks to "compare X with Y" → get_multiple_quotes
- If user asks for "top 5 [anything about specific stocks]" → NOT market movers
- Market movers ONLY for market-wide requests like "top gainers in market"

Return JSON:
{
  "tools_to_call": [
    {"tool": "tool_name", "params": {...}}
  ]
}

CORRECT EXAMPLES:
- "Compare NVDA stock price with AMD" → get_multiple_quotes([NVDA, AMD])
- "AAPL price" → get_stock_data(AAPL)  
- "AMD stock over past 6 months" → get_price_history(symbol=AMD, periodType=month, period=6, frequencyType=daily, frequency=1)
- "Why AMD performance last year" → get_price_history(symbol=AMD, periodType=year, period=1, frequencyType=daily, frequency=1)
- "AMD past 2 weeks" → get_price_history(symbol=AMD, periodType=day, period=10, frequencyType=minute, frequency=30)
- "AMD past 1 week" → get_price_history(symbol=AMD, periodType=day, period=5, frequencyType=minute, frequency=30)
- "Top market gainers" → get_market_movers(NASDAQ, PERCENT_CHANGE_UP, 1)

WRONG - Do NOT do this:
- "Compare NVDA with AMD" → Do NOT call market_movers + multiple_quotes
- "Show top 5 insider trades and compare prices" → Do NOT call market_movers

SCHWAB API PRICE HISTORY PARAMETERS - CRITICAL CONSTRAINTS:

periodType="day": 
  - period: MUST be one of [1, 2, 3, 4, 5, 10]
  - frequencyType: MUST be "minute" (ONLY option)
  - frequency: MUST be one of [1, 5, 10, 15, 30]
  - Use for: intraday, "past 3 days", "past week", "past 10 days"

periodType="month": 
  - period: MUST be one of [1, 2, 3, 6]
  - frequencyType: MUST be "daily" or "weekly"
  - frequency: MUST be 1
  - Use for: "past month", "past 2 months", "past 3 months", "past 6 months"

periodType="year": 
  - period: MUST be one of [1, 2, 3, 5, 10, 15, 20]
  - frequencyType: MUST be "daily", "weekly", or "monthly"
  - frequency: MUST be 1
  - Use for: "past year", "past 2 years", "past 5 years"

periodType="ytd": 
  - period: MUST be 1
  - frequencyType: MUST be "daily" or "weekly"
  - frequency: MUST be 1
  - Use for: "year to date", "ytd", "this year"

TIME RANGE MAPPING - Use exact values:
"past 3 days" → periodType: "day", period: 3, frequencyType: "minute", frequency: 30
"past 5 days" → periodType: "day", period: 5, frequencyType: "minute", frequency: 30
"past week" → periodType: "day", period: 5, frequencyType: "minute", frequency: 30
"past 10 days" → periodType: "day", period: 10, frequencyType: "minute", frequency: 30
"past 1 month" → periodType: "month", period: 1, frequencyType: "daily", frequency: 1
"past 2 months" → periodType: "month", period: 2, frequencyType: "daily", frequency: 1
"past 3 months" → periodType: "month", period: 3, frequencyType: "daily", frequency: 1
"past 6 months" → periodType: "month", period: 6, frequencyType: "daily", frequency: 1
"year to date" or "ytd" → periodType: "ytd", period: 1, frequencyType: "daily", frequency: 1
"past year" or "past 1 year" → periodType: "year", period: 1, frequencyType: "daily", frequency: 1

INVALID COMBINATIONS TO AVOID:
- periodType="day" with frequencyType="daily" → INVALID
- periodType="month" with period=4, 5, or any value not in [1,2,3,6] → INVALID
- periodType="year" with frequencyType="minute" → INVALID

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
            "THE", "AND", "OR", "FOR", "WITH", "PAST", "LAST", "THIS", "THAT", 
            "WHAT", "HOW", "WHEN", "WHERE", "WHY", "SHOW", "GET", "FIND", "TELL", 
            "PRICE", "STOCK", "SHARE", "MARKET", "QUOTE", "DATA", "INFO", "CHANGE",
            "PERCENT", "TIME", "HISTORY", "TREND", "CHART", "GRAPH", "COMPARE", "VS"
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
        
        # ONLY ONE TOOL - prioritize based on most specific match
        
        # 1. Market hours (most specific)
        if any(keyword in query_lower for keyword in ["hours", "schedule", "open", "close", "trading times", "market open", "market close"]):
            return {"tools_to_call": [{"tool": "get_market_hours", "params": {"markets": ["equity", "option"]}}]}
        
        # 2. Stock comparison (has multiple symbols OR comparison words)
        if len(symbols) > 1 or any(keyword in query_lower for keyword in ["compare", "vs", "versus", "against"]):
            if symbols and len(symbols) >= 2:
                return {"tools_to_call": [{"tool": "get_multiple_quotes", "params": {"symbols": symbols[:5]}}]}
        
        # 3. Price history - Enhanced fallback with better time range detection
        if any(keyword in query_lower for keyword in ["performance", "history", "chart", "trend", "past", "month", "months", "year", "years", "week", "weeks", "over", "day", "days", "ytd", "year-to-date", "year to date"]) and symbols:
            # Try to detect specific time ranges
            if "3 day" in query_lower or "three day" in query_lower:
                params = {"symbol": symbols[0], "periodType": "day", "period": 3, "frequencyType": "minute", "frequency": 30}
            elif "5 day" in query_lower or "five day" in query_lower or "week" in query_lower:
                params = {"symbol": symbols[0], "periodType": "day", "period": 5, "frequencyType": "minute", "frequency": 30}
            elif "10 day" in query_lower or "ten day" in query_lower:
                params = {"symbol": symbols[0], "periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 30}
            elif "2 month" in query_lower or "two month" in query_lower:
                params = {"symbol": symbols[0], "periodType": "month", "period": 2, "frequencyType": "daily", "frequency": 1}
            elif "3 month" in query_lower or "three month" in query_lower:
                params = {"symbol": symbols[0], "periodType": "month", "period": 3, "frequencyType": "daily", "frequency": 1}
            elif "6 month" in query_lower or "six month" in query_lower:
                params = {"symbol": symbols[0], "periodType": "month", "period": 6, "frequencyType": "daily", "frequency": 1}
            elif "ytd" in query_lower or "year to date" in query_lower or "year-to-date" in query_lower:
                params = {"symbol": symbols[0], "periodType": "ytd", "period": 1, "frequencyType": "daily", "frequency": 1}
            elif "1 year" in query_lower or "one year" in query_lower or ("year" in query_lower and "2" not in query_lower):
                params = {"symbol": symbols[0], "periodType": "year", "period": 1, "frequencyType": "daily", "frequency": 1}
            else:
                # Default fallback to 1 month
                params = {"symbol": symbols[0], "periodType": "month", "period": 1, "frequencyType": "daily", "frequency": 1}
            
            return {"tools_to_call": [{"tool": "get_price_history", "params": params}]}
        
        # 4. Market movers (ONLY for market-wide requests WITHOUT specific symbols)
        if (not symbols or len(symbols) == 0) and any(keyword in query_lower for keyword in ["top gainers", "top losers", "market movers", "trending stocks", "market leaders", "biggest winners", "biggest losers", "volume leaders", "most active stocks"]):
            sort_type = "VOLUME" if any(word in query_lower for word in ["volume", "most active"]) else "PERCENT_CHANGE_UP"
            return {"tools_to_call": [{"tool": "get_market_movers", "params": {"index": "$SPX", "sort": sort_type, "frequency": 1}}]}
        
        # 5. Single stock quote (default if we have exactly one symbol)
        if len(symbols) == 1:
            return {"tools_to_call": [{"tool": "get_stock_data", "params": {"symbol": symbols[0]}}]}
        
        # 6. No valid stock request found
        return {"tools_to_call": []}


class MCPRequest(BaseModel):
    input: str  # Claude sends the raw user query here
    state: dict | None = None  # Optional memory / conversation state


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
    
    # Format period text based on parameters
    period_type = history_data.get('period_type', 'month')
    period = history_data.get('period', 1)
    
    if period_type == 'ytd':
        period_text = "Year-to-Date"
    elif period_type == 'day':
        period_text = f"{period} day{'s' if period > 1 else ''}"
    elif period_type == 'month':
        period_text = f"{period} month{'s' if period > 1 else ''}"
    elif period_type == 'year':
        period_text = f"{period} year{'s' if period > 1 else ''}"
    else:
        period_text = f"{period} {period_type}{'s' if period > 1 else ''}"
    
    return (
        f"📈 {symbol} - {period_text} Performance:\n"
        f"{change_emoji} Period Change: {period_change:+.2f} ({period_change_pct:+.2f}%)\n"
        f"Period High: ${period_high:.2f}\n"
        f"Period Low: ${period_low:.2f}\n"
        f"Current: ${last_candle['close']:.2f}\n"
        f"Data Points: {len(candles)} trading periods"
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
                    period_type = params.get('periodType', 'month')  # Note: API uses camelCase
                    period = params.get('period', 1)
                    frequency_type = params.get('frequencyType', 'daily')  # Note: API uses camelCase
                    frequency = params.get('frequency', 1)
                    
                    data = get_price_history(symbol, period_type, period, frequency_type, frequency)
                    if data:
                        # Add parameters to data for formatting
                        data['period_type'] = period_type
                        data['period'] = period
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

        # Extract symbols for follow-up suggestions
        symbols = []
        for tool_call in plan['tools_to_call']:
            params = tool_call.get('params', {})
            if 'symbol' in params:
                symbols.append(params['symbol'])
            elif 'symbols' in params:
                symbols.extend(params['symbols'])
        
        # Note: Follow-up suggestions are handled by the frontend separately

        print(f"🔧 STOCK AGENT - Final output length: {len(output)} chars")
        print(f"🎉 STOCK AGENT - Successfully processed query using {len(plan['tools_to_call'])} tool(s)")
        return {"output": output}

    except Exception as e:
        return JSONResponse(status_code=500, content={"output": f"❌ Error: {e}"})