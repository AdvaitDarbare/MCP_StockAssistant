# backend/app/graph/router_node.py

from typing import Dict
from anthropic import AsyncAnthropic
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

ROUTER_SYSTEM = """You are a router agent. You decide where to route a query: 'stock', 'equity_insights', or 'fallback'.

Route to 'stock' for:
- Stock PRICES, quotes, real-time data ("What's AAPL price?")
- Historical PRICE performance ("How has Tesla performed?")
- Market movers, gainers/losers ("Show me top gainers")
- Trading hours and market status ("Is the market open?")
- Multi-stock comparisons ("Compare AAPL vs MSFT")

Route to 'equity_insights' for:
- Company PROFILES, overviews, about the company ("Tell me about Apple")
- Company SECTORS, business details ("What sector is Tesla in?")
- ANALYST ratings and recommendations ("What are analyst ratings for NVDA?")
- Company NEWS and press releases ("Show me recent news for MSFT")
- INSIDER trading activity ("Insider trading for AAPL")
- Comprehensive company ANALYSIS ("Full analysis of Tesla")

Route to 'fallback' for:
- General knowledge questions
- Non-financial queries
- Weather, geography, science, etc.
- Any question not about stocks/finance

Examples:
"Tell me about Apple's company profile" → equity_insights
"What's Apple's stock price?" → stock
"What's the weather?" → fallback

Only respond with one word: 'stock', 'equity_insights', or 'fallback'"""

async def router_node(state: Dict) -> Dict:
    query = state.get("input", "")
    print(f"🔧 ROUTER - Input query: '{query}'")

    try:
        response = await anthropic.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=20,
            temperature=0,
            system=ROUTER_SYSTEM,
            messages=[{"role": "user", "content": query}],
        )
        route = response.content[0].text.strip().lower()
    except Exception as e:
        print(f"❌ ROUTER - Error calling Anthropic API: {e}")
        route = "fallback"  # Default to fallback on error
    print(f"🔧 ROUTER - Raw LLM response: '{route}'")
    
    # Handle the three possible routes
    if route == "stock":
        decided_route = "stock"
    elif route == "equity_insights":
        decided_route = "equity_insights"
    else:
        decided_route = "fallback"
    
    print(f"🔧 ROUTER - Final routing decision: '{decided_route}'")
    return {"route": decided_route}
