# advisor_agent.py – Investment advisory agent with risk analysis and recommendations

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from anthropic import AsyncAnthropic
import os
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

app = FastAPI()

class MCPRequest(BaseModel):
    input: str
    state: dict | None = None

# Tool calling functions to other agents
async def call_stock_agent(query: str) -> str:
    """Call the stock agent to get market data"""
    print(f"🔍 ADVISOR DEBUG - Calling stock agent with query: '{query}'")
    try:
        async with aiohttp.ClientSession() as session:
            print(f"🔍 ADVISOR DEBUG - Making request to stock agent at localhost:8020")
            async with session.post(
                "http://localhost:8020/mcp",  # Stock agent port
                json={"input": query},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"🔍 ADVISOR DEBUG - Stock agent response status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    output = result.get("output", "No stock data available")
                    print(f"🔍 ADVISOR DEBUG - Stock agent returned {len(output)} chars")
                    return output
                else:
                    error_msg = f"Stock agent error: {response.status}"
                    print(f"🔍 ADVISOR DEBUG - {error_msg}")
                    return error_msg
    except Exception as e:
        print(f"🔍 ADVISOR DEBUG - Exception calling stock agent: {type(e).__name__}: {e}")
        return "Unable to fetch stock data"

async def call_equity_agent(query: str) -> str:
    """Call the equity insights agent to get company analysis"""
    print(f"🔍 ADVISOR DEBUG - Calling equity agent with query: '{query}'")
    try:
        async with aiohttp.ClientSession() as session:
            print(f"🔍 ADVISOR DEBUG - Making request to equity agent at localhost:8001")
            async with session.post(
                "http://localhost:8001/mcp",  # Equity agent port
                json={"input": query},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"🔍 ADVISOR DEBUG - Equity agent response status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    output = result.get("output", "No equity data available")
                    print(f"🔍 ADVISOR DEBUG - Equity agent returned {len(output)} chars")
                    return output
                else:
                    error_msg = f"Equity agent error: {response.status}"
                    print(f"🔍 ADVISOR DEBUG - {error_msg}")
                    return error_msg
    except Exception as e:
        print(f"🔍 ADVISOR DEBUG - Exception calling equity agent: {type(e).__name__}: {e}")
        return "Unable to fetch equity insights"

async def analyze_investment_query(user_query: str) -> Dict:
    """Analyze user query to determine what data is needed"""
    print(f"🔍 ADVISOR DEBUG - Analyzing query: '{user_query}'")
    analysis_prompt = f"""Analyze this investment query: "{user_query}"

Extract stock symbols and determine advice type. Look for:
- Stock symbols: AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, etc.
- Company names: Apple, Tesla, Google, Microsoft, Amazon, Nvidia, etc.

Return JSON:
{{
  "symbols": ["SYMBOL1", "SYMBOL2"],
  "advice_type": "buy_recommendation|risk_analysis|portfolio_advice|market_timing|comparison",
  "data_needed": {{
    "stock_data": true,
    "equity_insights": true
  }}
}}

SYMBOL EXTRACTION EXAMPLES:
"Should I buy AAPL?" → symbols: ["AAPL"]
"Should I buy Apple stock?" → symbols: ["AAPL"] 
"Tesla vs Google" → symbols: ["TSLA", "GOOGL"]
"Microsoft investment" → symbols: ["MSFT"]
"Should I invest in Nvidia?" → symbols: ["NVDA"]

ADVICE TYPES:
- buy_recommendation: Should I buy/sell, good investment questions
- risk_analysis: Risk, safety, volatility questions  
- portfolio_advice: Diversification, allocation questions
- market_timing: When to buy/sell, timing questions
- comparison: Compare multiple stocks"""

    try:
        print(f"🔍 ADVISOR DEBUG - Calling Claude API for query analysis")
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        print(f"🔍 ADVISOR DEBUG - Claude API response received for analysis")
        
        import json
        import re
        response_text = response.content[0].text.strip()
        
        # Extract JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            analysis_result = json.loads(json_match.group())
            print(f"🔍 ADVISOR DEBUG - Analysis result: {analysis_result}")
            return analysis_result
        
        # Fallback parsing
        query_upper = user_query.upper()
        fallback_symbols = []
        
        # Common stock symbols
        common_symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX"]
        for symbol in common_symbols:
            if symbol in query_upper:
                fallback_symbols.append(symbol)
        
        # Company name mapping
        company_mapping = {
            "APPLE": "AAPL", "TESLA": "TSLA", "GOOGLE": "GOOGL", 
            "MICROSOFT": "MSFT", "AMAZON": "AMZN", "NVIDIA": "NVDA",
            "META": "META", "NETFLIX": "NFLX"
        }
        
        for company, symbol in company_mapping.items():
            if company in query_upper and symbol not in fallback_symbols:
                fallback_symbols.append(symbol)
        
        fallback_result = {
            "symbols": fallback_symbols or ["AAPL"],  # Default to AAPL if no symbols found
            "advice_type": "buy_recommendation", 
            "data_needed": {"stock_data": True, "equity_insights": True}
        }
        print(f"🔍 ADVISOR DEBUG - Using fallback analysis: {fallback_result}")
        return fallback_result
        
    except Exception as e:
        print(f"🔍 ADVISOR DEBUG - Exception in query analysis: {type(e).__name__}: {e}")
        error_result = {
            "symbols": ["AAPL"],  # Default symbol
            "advice_type": "buy_recommendation",
            "data_needed": {"stock_data": True, "equity_insights": True}
        }
        print(f"🔍 ADVISOR DEBUG - Using error fallback: {error_result}")
        return error_result

async def generate_investment_advice(
    user_query: str, 
    analysis: Dict, 
    stock_data: str = "", 
    equity_data: str = ""
) -> str:
    """Generate comprehensive investment advice using LLM"""
    print(f"🔍 ADVISOR DEBUG - Entering advice generation with stock_data: {len(stock_data)} chars, equity_data: {len(equity_data)} chars")
    
    advice_prompt = f"""You are a professional investment advisor. Provide comprehensive, balanced investment advice.

USER QUERY: "{user_query}"
ANALYSIS TYPE: {analysis.get('advice_type', 'general')}
SYMBOLS: {analysis.get('symbols', [])}

MARKET DATA:
{stock_data}

COMPANY INSIGHTS:
{equity_data}

Provide a structured investment recommendation with:

🎯 **Investment Recommendation**
- Clear BUY/HOLD/SELL recommendation with confidence level
- Or appropriate advice for the query type

📊 **Current Analysis** 
- Key metrics and current situation
- Market position and recent performance

⚖️ **Risk Assessment**
- Identify specific risks (market, company, sector)
- Risk level: Low/Medium/High with explanation
- Volatility and risk factors

💡 **Reasoning**
- 2-3 key points supporting your recommendation
- Consider fundamentals, technicals, sentiment

⚠️ **Important Considerations**
- Potential concerns or red flags
- Market conditions and timing factors
- Risk management suggestions

📈 **Actionable Advice**
- Specific next steps if they decide to invest
- Position sizing recommendations
- Timeline and monitoring suggestions

**CRITICAL GUIDELINES:**
- Always include appropriate disclaimers about investment risk
- Be balanced - mention both positives and negatives
- If data is insufficient, provide general guidance based on known information
- Tailor advice to the specific question asked
- Use clear, accessible language
- Include risk warnings for any BUY recommendations
- If no current data available, base advice on general market knowledge

**WHEN DATA IS LIMITED:**
- Still provide helpful investment guidance
- Use general market knowledge about the company
- Focus on risk factors and general considerations
- Suggest seeking current data before making decisions

Remember: This is educational information, not personalized financial advice."""

    try:
        print(f"🔍 ADVISOR DEBUG - Calling Claude API for advice generation")
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",  # Use Haiku for consistency
            max_tokens=1500,
            temperature=0.3,
            messages=[{"role": "user", "content": advice_prompt}]
        )
        print(f"🔍 ADVISOR DEBUG - Claude API response received for advice")
        
        advice = response.content[0].text.strip()
        
        # Claude should already include disclaimers in the response
        return advice
        
    except Exception as e:
        print(f"🔍 ADVISOR DEBUG - Exception in advice generation: {type(e).__name__}: {e}")
        import traceback
        print(f"🔍 ADVISOR DEBUG - Full traceback: {traceback.format_exc()}")
        return "❌ Unable to generate investment advice at this time. Please try again later."

async def generate_follow_up_suggestions(user_query: str, symbols: List[str]) -> str:
    """Generate follow-up suggestions for investment advice"""
    if not symbols:
        symbols = ["AAPL"]  # Default symbol
    
    primary_symbol = symbols[0]
    suggestions = []
    
    # Context-aware suggestions based on query type
    query_lower = user_query.lower()
    
    if "buy" in query_lower or "invest" in query_lower:
        suggestions.extend([
            f"What are the risks of investing in {primary_symbol}?",
            f"Compare {primary_symbol} with similar stocks",
            f"When is the best time to buy {primary_symbol}?",
            f"How much should I invest in {primary_symbol}?"
        ])
    elif "risk" in query_lower:
        suggestions.extend([
            f"Should I buy {primary_symbol} now?",
            f"What's the outlook for {primary_symbol}?",
            f"Compare {primary_symbol} risk vs reward",
            f"How to manage {primary_symbol} investment risk?"
        ])
    else:
        suggestions.extend([
            f"Should I buy {primary_symbol} stock?",
            f"What are the risks of {primary_symbol}?",
            f"Compare {primary_symbol} vs GOOGL for investment",
            "What stocks should I consider for diversification?"
        ])
    
    # Format suggestions
    formatted_suggestions = []
    for i, suggestion in enumerate(suggestions[:4], 1):
        emoji = "🎯" if "should" in suggestion.lower() else "⚖️" if "risk" in suggestion.lower() else "📊" if "compare" in suggestion.lower() else "💡"
        formatted_suggestions.append(f"{i}. {emoji} {suggestion}")
    
    return f"\n\n__FOLLOW_UPS_START__\n" + "\n".join(formatted_suggestions) + "\n__FOLLOW_UPS_END__"

@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
        mcp_input = MCPRequest(**body)
        
        print(f"🎯 ADVISOR AGENT - Input received: '{mcp_input.input}'")
        
        # Analyze the query to determine data needs
        analysis = await analyze_investment_query(mcp_input.input)
        print(f"🎯 ADVISOR AGENT - Analysis: {analysis}")
        
        symbols = analysis.get("symbols", [])
        data_needed = analysis.get("data_needed", {})
        
        # Gather data from other agents in parallel
        print(f"🔍 ADVISOR DEBUG - Starting data gathering phase")
        stock_data = ""
        equity_data = ""
        
        tasks = []
        
        if data_needed.get("stock_data", False) and symbols:
            primary_symbol = symbols[0]
            stock_query = f"Get current price, performance, and key metrics for {primary_symbol}"
            print(f"🔍 ADVISOR DEBUG - Adding stock task for {primary_symbol}")
            tasks.append(("stock", call_stock_agent(stock_query)))
        
        if data_needed.get("equity_insights", False) and symbols:
            primary_symbol = symbols[0]
            equity_query = f"Get analyst ratings, recent news, and company overview for {primary_symbol}"
            print(f"🔍 ADVISOR DEBUG - Adding equity task for {primary_symbol}")
            tasks.append(("equity", call_equity_agent(equity_query)))
            
        print(f"🔍 ADVISOR DEBUG - Total tasks to execute: {len(tasks)}")
        
        # Execute data gathering in parallel with error handling
        if tasks:
            try:
                print(f"🔍 ADVISOR DEBUG - Executing {len(tasks)} tasks in parallel...")
                results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
                print(f"🔍 ADVISOR DEBUG - All tasks completed, processing results...")
                
                for i, (data_type, result) in enumerate(zip([task[0] for task in tasks], results)):
                    if isinstance(result, Exception):
                        print(f"⚠️ Error fetching {data_type} data: {result}")
                        # Add fallback data
                        if data_type == "stock":
                            stock_data = f"Unable to fetch current {symbols[0] if symbols else 'stock'} data from market APIs."
                        elif data_type == "equity":
                            equity_data = f"Unable to fetch company insights for {symbols[0] if symbols else 'stock'} from data sources."
                        continue
                        
                    if data_type == "stock":
                        stock_data = result
                        print(f"✅ Got stock data: {len(stock_data)} chars")
                    elif data_type == "equity":
                        equity_data = result
                        print(f"✅ Got equity data: {len(equity_data)} chars")
            except Exception as e:
                print(f"⚠️ Data gathering failed: {e}")
                # Provide fallback data
                if symbols:
                    stock_data = f"Market data unavailable for {symbols[0]}"
                    equity_data = f"Company insights unavailable for {symbols[0]}"
        
        # Generate investment advice
        print(f"🔍 ADVISOR DEBUG - Generating investment advice...")
        advice = await generate_investment_advice(
            mcp_input.input, 
            analysis, 
            stock_data, 
            equity_data
        )
        print(f"🔍 ADVISOR DEBUG - Investment advice generated: {len(advice)} chars")
        
        # Add follow-up suggestions
        follow_ups = await generate_follow_up_suggestions(mcp_input.input, symbols)
        final_output = advice + follow_ups
        
        print(f"🎯 ADVISOR AGENT - Generated advice: {len(final_output)} chars")
        return {"output": final_output}
        
    except Exception as e:
        print(f"❌ ADVISOR AGENT Error: {e}")
        return JSONResponse(
            status_code=500, 
            content={"output": f"❌ Investment advisor error: {e}"}
        )