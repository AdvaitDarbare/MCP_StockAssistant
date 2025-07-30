# equity_insight_agent.py – MCP-compliant server for equity insight queries using Finviz

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from anthropic import AsyncAnthropic
import os
from pathlib import Path
from dotenv import load_dotenv
from ..services.finviz_client import (
    get_company_overview, 
    get_analyst_ratings, 
    get_company_news, 
    get_insider_trading
)

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

app = FastAPI()

def get_tool_description(tool_name: str) -> str:
    """Get human-readable description of equity insight tools"""
    descriptions = {
        'get_company_overview': '🏢 Get basic company information, sectors, and exchange details',
        'get_analyst_ratings': '📊 Get analyst recommendations, price targets, and rating changes',
        'get_company_news': '📰 Get recent news articles and press releases for the company',
        'get_insider_trading': '👥 Get insider buy/sell activity and officer transactions'
    }
    return descriptions.get(tool_name, f'🔧 Unknown tool: {tool_name}')

async def plan_and_execute_with_tools(user_query: str) -> dict:
    """Use Claude to plan and execute using available tools"""
    system_prompt = """You are an equity research assistant. Extract the ticker and return ONLY the ONE tool that matches the specific request.

AVAILABLE TOOLS:
1. get_company_overview(ticker) - Basic company info, sectors, exchange
2. get_analyst_ratings(ticker) - Analyst recommendations and price targets  
3. get_company_news(ticker, limit=8) - Recent news articles
4. get_insider_trading(ticker, limit=8) - Insider buy/sell transactions

CRITICAL RULES:
- Return ONLY ONE tool that matches the request
- Extract numbers from requests (e.g., "top 5" → limit: 5)
- Do NOT add company overview unless specifically asked

Return JSON:
{
  "ticker": "SYMBOL",
  "tools_to_call": [
    {"tool": "tool_name", "params": {"ticker": "SYMBOL", "limit": X}}
  ]
}

CORRECT EXAMPLES:
- "Show me top 5 insider tradings for NVDA" → get_insider_trading(NVDA, limit=5)
- "Tesla news" → get_company_news(TSLA, limit=8)
- "Apple analyst ratings" → get_analyst_ratings(AAPL)
- "Tell me about Microsoft" → get_company_overview(MSFT)

WRONG - Do NOT do this:
- Do NOT add multiple tools unless explicitly requested
- Do NOT add company overview automatically"""

    try:
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_query}],
        )
        
        import json
        import re
        response_text = response.content[0].text.strip()
        print(f"🔧 Equity LLM Response: {response_text}")
        
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
        print(f"❌ Error analyzing equity query: {e}")
        # Fallback to simple extraction
        words = user_query.upper().split()
        symbols = []
        
        # Common non-stock words to exclude
        exclude_words = {
            "THE", "AND", "OR", "FOR", "WITH", "OVER", "PAST", "LAST", "THIS", "THAT", 
            "WHAT", "HOW", "WHEN", "WHERE", "WHY", "SHOW", "GET", "FIND", "TELL", 
            "COMPANY", "ANALYST", "NEWS", "INSIDER", "RATING", "OVERVIEW", "PROFILE"
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
        
        if any(keyword in query_lower for keyword in ["overview", "company", "profile", "about", "details"]):
            query_type = "company_overview"
        elif any(keyword in query_lower for keyword in ["analyst", "rating", "recommendation", "target", "upgrade", "downgrade"]):
            query_type = "analyst_ratings"
        elif any(keyword in query_lower for keyword in ["news", "article", "headline", "press", "recent"]):
            query_type = "news"
        elif any(keyword in query_lower for keyword in ["insider", "insider trading", "insider activity", "insider buys", "insider sells", "officer", "transaction", "insider transactions"]):
            query_type = "insider_trading"
        elif any(keyword in query_lower for keyword in ["analysis", "report", "everything", "all", "comprehensive"]):
            query_type = "all_insights"
        else:
            query_type = "unknown"  # Don't default to company overview
        
        # Check if query seems equity-related
        is_equity_related = (len(symbols) > 0 or 
                           any(keyword in query_lower for keyword in [
                               "stock", "share", "company", "ticker", "equity", 
                               "analyst", "rating", "news", "insider"
                           ]))
                
        return {
            "query_type": query_type,
            "symbols": symbols[:5],  # Limit to 5 symbols
            "is_equity_related": is_equity_related
        }


class MCPRequest(BaseModel):
    input: str  # Claude sends the raw user query here
    state: dict | None = None  # Optional memory / conversation state


def format_company_overview(data: dict) -> str:
    """Format company overview data"""
    if not data:
        return "❌ No company overview data available"
    
    # Format sectors nicely
    sectors = data['sectors']
    if isinstance(sectors, list):
        sector_str = " • ".join(sectors)
    else:
        sector_str = str(sectors)
        
    return (
        f"🏢 **{data['ticker']} - {data['company_name']}**\n\n"
        f"📈 **Exchange:** {data['exchange']}\n"
        f"🏭 **Sectors:** {sector_str}\n"
        f"📊 **Profile Status:** Available through Finviz\n"
        f"✅ **Data Verified:** Company exists and trading"
    )

def format_analyst_ratings(df, ticker: str = "Unknown") -> str:
    """Format analyst ratings data with improved readability"""
    if df is None or df.empty:
        return "❌ No analyst ratings data available"
    
    output = f"📊 Analyst Ratings for {ticker}\n\n"
    
    # Get recent ratings (first 10)
    recent_df = df.head(10)
    
    output += "🔍 **Recent Analyst Actions:**\n\n"
    
    for index, row in recent_df.iterrows():
        date = row.get('Date', 'N/A')
        status = row.get('Status', 'N/A')
        firm = row.get('Outer', 'N/A')
        rating = row.get('Rating', 'N/A')
        price = row.get('Price', 'N/A')
        
        # Format the status with appropriate emoji
        if 'Upgrade' in status:
            status_emoji = "⬆️"
        elif 'Downgrade' in status:
            status_emoji = "⬇️"
        elif 'Initiated' in status:
            status_emoji = "🆕"
        elif 'Reiterated' in status:
            status_emoji = "🔄"
        else:
            status_emoji = "📋"
        
        # Format rating with color indicators
        if any(word in rating.upper() for word in ['BUY', 'STRONG BUY', 'OVERWEIGHT', 'OUTPERFORM']):
            rating_emoji = "🟢"
        elif any(word in rating.upper() for word in ['SELL', 'UNDERWEIGHT', 'UNDERPERFORM']):
            rating_emoji = "🔴"
        elif 'HOLD' in rating.upper():
            rating_emoji = "🟡"
        else:
            rating_emoji = "⚪"
        
        # Clean up the firm name (truncate if too long)
        firm_display = firm[:20] + "..." if len(firm) > 20 else firm
        
        output += f"{status_emoji} **{date}** | {firm_display}\n"
        output += f"   {status} • {rating_emoji} {rating}\n"
        if price and price != 'N/A' and price.strip():
            output += f"   💰 Price Target: {price}\n"
        output += "\n"
    
    # Add summary stats if we have enough data
    if len(df) > 0:
        output += "📈 **Summary:**\n"
        
        # Count rating types
        buy_count = sum(1 for _, row in df.iterrows() 
                       if any(word in str(row.get('Rating', '')).upper() 
                             for word in ['BUY', 'OVERWEIGHT', 'OUTPERFORM']))
        hold_count = sum(1 for _, row in df.iterrows() 
                        if 'HOLD' in str(row.get('Rating', '')).upper())
        sell_count = sum(1 for _, row in df.iterrows() 
                        if any(word in str(row.get('Rating', '')).upper() 
                              for word in ['SELL', 'UNDERWEIGHT', 'UNDERPERFORM']))
        
        output += f"🟢 Buy/Outperform: {buy_count}  "
        output += f"🟡 Hold: {hold_count}  "
        output += f"🔴 Sell/Underperform: {sell_count}\n"
        output += f"📊 Total Ratings: {len(df)}"
    
    return output

def format_company_news(df, ticker: str = "Unknown", requested_count: int = 8) -> str:
    """Format company news data matching the format from your working script"""
    if df is None or df.empty:
        return "❌ No recent news available"
    
    # Print column names for debugging (remove in production)
    # print(f"🔧 DataFrame columns: {list(df.columns)}")
    
    output = f"📰 Recent News for {ticker}\n"
    if requested_count != 8:
        output += f"(Showing top {requested_count} articles)\n"
    output += "\n"
    
    # Use the actual column names from the pyfinviz DataFrame
    for index, row in df.iterrows():
        # Get data from the actual columns based on your working script
        date = row.get('Date', 'Recent')
        headline = row.get('Headline', row.get('Title', 'News Article'))
        url = row.get('URL', row.get('Link', ''))
        source_from = row.get('From', row.get('Source', 'Unknown Source'))
        
        # Clean up the headline - keep it longer since that's how your script shows it
        if isinstance(headline, str) and len(headline) > 150:
            headline = headline[:147] + "..."
        
        # Add appropriate emoji based on content
        headline_lower = str(headline).lower()
        if any(word in headline_lower for word in ['earnings', 'profit', 'revenue', 'beat', 'financial results']):
            news_emoji = "💰"
        elif any(word in headline_lower for word in ['upgrade', 'buy', 'positive', 'bull', 'rises', 'soars']):
            news_emoji = "📈"
        elif any(word in headline_lower for word in ['downgrade', 'sell', 'negative', 'bear', 'falls', 'drops', 'plunges']):
            news_emoji = "📉"
        elif any(word in headline_lower for word in ['acquisition', 'merger', 'deal']):
            news_emoji = "🤝"
        elif any(word in headline_lower for word in ['launch', 'new', 'innovation', 'unveils']):
            news_emoji = "🚀"
        elif any(word in headline_lower for word in ['misses', 'disappoints', 'concerns']):
            news_emoji = "⚠️"
        else:
            news_emoji = "📄"
        
        # Format similar to your working script output
        output += f"{news_emoji} **{date}**\n"
        output += f"   {headline}\n"
        if source_from and str(source_from) != 'nan' and source_from != 'Unknown Source':
            # Clean up source format (remove parentheses if present)
            clean_source = str(source_from).strip('()')
            output += f"   📍 Source: {clean_source}\n"
        if url and str(url) != 'nan' and len(str(url)) > 5:
            url_str = str(url)
            # Handle relative URLs from Finviz by making them absolute
            if url_str.startswith('/'):
                full_url = f"https://finviz.com{url_str}"
            else:
                full_url = url_str
            
            # Only truncate extremely long URLs (keep more of the URL visible)
            if len(full_url) > 100:
                display_url = full_url[:97] + "..."
            else:
                display_url = full_url
            output += f"   🔗 {display_url}\n"
        output += "\n"
    
    output += f"📊 Showing {len(df)} articles"
    
    return output

def format_insider_trading(df, ticker: str = "Unknown", requested_count: int = 8) -> str:
    """Format insider trading data with improved readability based on actual DataFrame structure"""
    if df is None or df.empty:
        return "❌ No insider trading data available"
    
    # Print column names for debugging (remove in production)  
    # print(f"🔧 Insider DataFrame columns: {list(df.columns)}")
    
    output = f"👥 Insider Trading Activity for {ticker}\n"
    if requested_count != 8:
        output += f"(Showing top {requested_count} transactions)\n"
    output += "\n"
    
    # Process each insider transaction
    for index, row in df.iterrows():
        # Extract data based on your script output - columns may vary but these are common
        insider_name = None
        position = None  
        date = None
        transaction_type = None
        price = None
        shares = None
        value = None
        filing_date = None
        
        # Try to get data from various possible column names
        for col in df.columns:
            col_str = str(col).strip()
            if not insider_name and any(name_word in col_str.lower() for name_word in ['name', 'insider']):
                insider_name = row[col]
            elif not position and any(pos_word in col_str.lower() for pos_word in ['title', 'position', 'officer', 'director']):
                position = row[col] 
            elif not date and any(date_word in col_str.lower() for date_word in ['date', 'transaction']):
                date_val = row[col]
                if 'filing' not in col_str.lower():  # Avoid filing date
                    date = date_val
            elif not transaction_type and any(type_word in col_str.lower() for type_word in ['transaction', 'type', 'action']):
                transaction_type = row[col]
            elif not price and any(price_word in col_str.lower() for price_word in ['price', 'cost']):
                price = row[col]
            elif not shares and any(share_word in col_str.lower() for share_word in ['shares', 'quantity', 'amount']):
                shares = row[col]
            elif not value and any(val_word in col_str.lower() for val_word in ['value', 'total']):
                value = row[col]
            elif not filing_date and 'filing' in col_str.lower():
                filing_date = row[col]
        
        # Fallback to first few columns if we couldn't identify them
        row_values = list(row.values)
        if not insider_name and len(row_values) > 0:
            insider_name = row_values[0]
        if not position and len(row_values) > 2:
            position = row_values[2]
        if not date and len(row_values) > 3:
            date = row_values[3]
        if not transaction_type and len(row_values) > 4:
            transaction_type = row_values[4]
        if not price and len(row_values) > 5:
            price = row_values[5]
        if not shares and len(row_values) > 6:
            shares = row_values[6]
        if not value and len(row_values) > 7:
            value = row_values[7]
            
        # Clean up the data - validate that insider_name is not a URL
        if insider_name and (str(insider_name).lower().startswith('http') or 'finviz.com' in str(insider_name).lower()):
            # This is a URL, not a name - try to find the actual name in the row
            actual_name = "Unknown Insider"
            for val in row_values:
                val_str = str(val).strip()
                if (not val_str.lower().startswith('http') and 
                    'finviz.com' not in val_str.lower() and 
                    len(val_str) > 2 and
                    any(char.isalpha() for char in val_str) and
                    not val_str.replace('.', '').replace('%', '').replace('$', '').replace(',', '').replace(' ', '').isdigit()):
                    # This looks like a name (contains letters, not just numbers/symbols)
                    actual_name = val_str
                    break
            clean_name = actual_name.title()
        else:
            clean_name = str(insider_name).title() if insider_name else "Unknown Insider"
        clean_position = str(position) if position else "N/A"
        clean_date = str(date) if date else "Recent"
        clean_type = str(transaction_type) if transaction_type else "Transaction"
        
        # Format transaction type with appropriate emoji
        type_lower = clean_type.lower()
        if 'buy' in type_lower or 'purchase' in type_lower:
            trans_emoji = "🟢"  # Green for buys
        elif 'sell' in type_lower or 'sale' in type_lower:
            trans_emoji = "🔴"  # Red for sells
        elif 'option' in type_lower or 'exercise' in type_lower:
            trans_emoji = "⚡"  # Lightning for option exercises
        elif 'proposed' in type_lower:
            trans_emoji = "📋"  # Clipboard for proposed
        else:
            trans_emoji = "📊"  # Default
            
        # Format position with emoji
        pos_lower = clean_position.lower()
        if 'ceo' in pos_lower or 'chief executive' in pos_lower:
            pos_emoji = "👑"
        elif 'cfo' in pos_lower or 'chief financial' in pos_lower:
            pos_emoji = "💰" 
        elif 'director' in pos_lower:
            pos_emoji = "🎯"
        elif 'officer' in pos_lower:
            pos_emoji = "👔"
        else:
            pos_emoji = "👤"
            
        output += f"{trans_emoji} **{clean_name}** {pos_emoji}\n"
        output += f"   Position: {clean_position}\n"
        output += f"   Transaction: {clean_type} on {clean_date}\n"
        
        # Add price, shares, value if available
        if price and str(price) != 'nan' and price != '':
            try:
                price_val = float(str(price).replace('$', '').replace(',', ''))
                output += f"   💵 Price: ${price_val:,.2f}\n"
            except:
                output += f"   💵 Price: {price}\n"
                
        if shares and str(shares) != 'nan' and shares != '':
            try:
                shares_val = int(float(str(shares).replace(',', '')))
                output += f"   📊 Shares: {shares_val:,}\n"
            except:
                output += f"   📊 Shares: {shares}\n"
                
        if value and str(value) != 'nan' and value != '':
            try:
                value_val = float(str(value).replace('$', '').replace(',', ''))
                output += f"   💎 Total Value: ${value_val:,.0f}\n"
            except:
                output += f"   💎 Total Value: {value}\n"
        
        # Add insider trading URL if available (usually in column 1)
        if len(row_values) > 1:
            potential_url = str(row_values[1])
            if potential_url.lower().startswith('http') and 'finviz.com' in potential_url.lower():
                output += f"   🔗 Finviz Profile: {potential_url}\n"
        
        output += "\n"
    
    # Add summary
    buy_count = sum(1 for _, row in df.iterrows() 
                   if 'buy' in str(row.iloc[4] if len(row) > 4 else '').lower() or 'purchase' in str(row.iloc[4] if len(row) > 4 else '').lower())
    sell_count = sum(1 for _, row in df.iterrows() 
                    if 'sell' in str(row.iloc[4] if len(row) > 4 else '').lower() or 'sale' in str(row.iloc[4] if len(row) > 4 else '').lower())
    other_count = len(df) - buy_count - sell_count
    
    output += f"📈 **Summary:**\n"
    output += f"🟢 Buys: {buy_count}  🔴 Sells: {sell_count}  ⚡ Other: {other_count}\n"
    output += f"📊 Total Transactions: {len(df)}"
    
    return output

async def generate_follow_up_suggestions(tools_used: list, ticker: str, user_query: str) -> str:
    """Generate intelligent follow-up question suggestions validated by LLM"""
    # All available tools and their capabilities
    available_tools = {
        'get_company_overview': f'Get basic company information for {ticker}',
        'get_analyst_ratings': f'Get analyst recommendations and price targets for {ticker}',
        'get_company_news': f'Get recent news articles about {ticker}',
        'get_insider_trading': f'Get insider trading activity for {ticker}'
    }
    
    # Cross-domain suggestions (Stock Agent tools)
    cross_domain_tools = {
        'stock_price': f'Get current stock price for {ticker}',
        'stock_comparison': f'Compare {ticker} with other stocks',
        'price_history': f'Get price history for {ticker}',
        'market_movers': 'Get top market gainers/losers today'
    }
    
    # Find unused equity tools
    unused_equity_tools = [tool for tool in available_tools.keys() if tool not in tools_used]
    
    # Create base suggestions
    base_suggestions = []
    
    # Add unused equity tool suggestions
    for tool in unused_equity_tools[:2]:  # Limit to 2 equity suggestions
        if tool == 'get_company_overview':
            base_suggestions.append(f"Company overview of {ticker}")
        elif tool == 'get_analyst_ratings':
            base_suggestions.append(f"Analyst ratings for {ticker}")
        elif tool == 'get_company_news':
            base_suggestions.append(f"Recent news for {ticker}")
        elif tool == 'get_insider_trading':
            base_suggestions.append(f"Insider trading for {ticker}")
    
    # Add cross-analysis if only one tool was used
    if len(tools_used) == 1:
        base_suggestions.append(f"Full analysis of {ticker}")
    
    # Add cross-domain suggestions
    base_suggestions.extend([
        f"What's {ticker} stock price?",
        f"Compare {ticker} vs GOOGL vs MSFT"
    ])
    
    # Use LLM to validate and refine suggestions
    try:
        validation_prompt = f"""Given this user query: "{user_query}"
And the tools already used: {tools_used}
For ticker: {ticker}

From these potential follow-up suggestions:
{chr(10).join([f"- {s}" for s in base_suggestions])}

Select and refine the 3-4 most relevant, natural follow-up questions that:
1. Are directly answerable by our tools
2. Provide complementary information to what was already shown
3. Sound natural and conversational
4. Are relevant to the user's apparent interest

Return ONLY a numbered list with emojis, like:
1. 📊 What are analyst ratings for {ticker}?
2. 📈 What's {ticker} current stock price?
3. 📰 Show me recent news for {ticker}"""

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
        if 'analyst' in suggestion.lower():
            emoji = "📊"
        elif 'news' in suggestion.lower():
            emoji = "📰"
        elif 'insider' in suggestion.lower():
            emoji = "👥"
        elif 'price' in suggestion.lower():
            emoji = "📈"
        elif 'compare' in suggestion.lower():
            emoji = "⚖️"
        elif 'overview' in suggestion.lower():
            emoji = "🏢"
        else:
            emoji = "🔍"
        
        formatted_suggestions.append(f"{i}. {emoji} {suggestion}")
    
    suggestions_text = "\n".join(formatted_suggestions)
    return f"\n\n__FOLLOW_UPS_START__\n{suggestions_text}\n__FOLLOW_UPS_END__"

def format_all_insights(overview, ratings, news, insider, ticker) -> str:
    """Format comprehensive equity insights"""
    output = f"📈 Comprehensive Analysis for {ticker}\n\n"
    
    output += "=" * 50 + "\n"
    output += format_company_overview(overview) + "\n\n"
    
    output += "=" * 50 + "\n"
    output += format_analyst_ratings(ratings, ticker) + "\n\n"
    
    output += "=" * 50 + "\n"
    output += format_company_news(news) + "\n\n"
    
    output += "=" * 50 + "\n"
    output += format_insider_trading(insider) + "\n"
    
    return output

@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
        mcp_input = MCPRequest(**body)
        
        print(f"🔧 EQUITY AGENT - Input received: '{mcp_input.input}'")  # Enhanced debug logging

        # Plan and execute using available tools
        plan = await plan_and_execute_with_tools(mcp_input.input)
        print(f"🔧 EQUITY AGENT - Plan generated: {plan}")
        
        if not plan.get('ticker'):
            return JSONResponse(content={"output": "❌ No stock symbol found in your query. Please specify a ticker symbol or company name."})
        
        if not plan.get('tools_to_call'):
            return JSONResponse(content={"output": "❌ I couldn't determine what equity information you're looking for. Try asking about company overviews, analyst ratings, news, or insider trading."})
        
        # Execute the planned tools
        results = []
        symbol = plan['ticker']
        
        for tool_call in plan['tools_to_call']:
            tool_name = tool_call['tool']
            params = tool_call['params']
            
            print(f"🔧 EQUITY AGENT - Executing TOOL: {tool_name}")
            print(f"   📋 Tool Description: {get_tool_description(tool_name)}")
            print(f"   ⚙️  Parameters: {params}")
            
            try:
                if tool_name == 'get_company_overview':
                    data = get_company_overview(params['ticker'])
                    if data:
                        results.append(format_company_overview(data))
                        print(f"   ✅ Tool completed successfully - Got overview for {params['ticker']} ({data.get('company_name', 'N/A')})")
                        
                elif tool_name == 'get_analyst_ratings':
                    data = get_analyst_ratings(params['ticker'])
                    if data is not None and not data.empty:
                        results.append(format_analyst_ratings(data, params['ticker']))
                        print(f"   ✅ Tool completed successfully - Got {len(data)} analyst ratings for {params['ticker']}")
                        
                elif tool_name == 'get_company_news':
                    limit = params.get('limit', 8)
                    data = get_company_news(params['ticker'], limit=limit)
                    if data is not None and not data.empty:
                        results.append(format_company_news(data, params['ticker'], limit))
                        print(f"   ✅ Tool completed successfully - Got {len(data)} news articles for {params['ticker']}")
                        
                elif tool_name == 'get_insider_trading':
                    limit = params.get('limit', 8)
                    data = get_insider_trading(params['ticker'], limit=limit)
                    if data is not None and not data.empty:
                        results.append(format_insider_trading(data, params['ticker'], limit))
                        print(f"   ✅ Tool completed successfully - Got {len(data)} insider transactions for {params['ticker']}")
                        
            except Exception as e:
                error_msg = f"❌ Error calling {tool_name}: {str(e)}"
                results.append(error_msg)
                print(f"   🚨 Tool failed: {error_msg}")
        
        if not results:
            return JSONResponse(content={"output": f"❌ Could not retrieve any data for '{symbol}'. Please verify the ticker symbol is correct."})
        
        # Combine all results with clean formatting
        if len(results) == 1:
            output = results[0]  # Single tool result, use as-is
        else:
            # Multiple tools, combine with separators
            output = f"📊 Equity Analysis for {symbol}\n\n"
            output += "\n\n" + "="*50 + "\n\n"
            output += f"\n\n{'='*50}\n\n".join(results)

        # Note: Follow-up suggestions are handled by the frontend separately

        print(f"🔧 EQUITY AGENT - Final output length: {len(output)} chars")
        print(f"🎉 EQUITY AGENT - Successfully processed query using {len(plan['tools_to_call'])} tool(s)")
        return {"output": output}

    except Exception as e:
        return JSONResponse(status_code=500, content={"output": f"❌ Error: {e}"})