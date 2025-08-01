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

ROUTER_SYSTEM = """You are an intelligent task detection and routing agent. You analyze queries to identify multiple tasks and route them appropriately.

TASK DETECTION RULES:

Route to 'advisor' for INVESTMENT ADVICE & RECOMMENDATIONS:
- Buy/sell recommendations ("Should I buy AAPL?", "Is TSLA a good investment?")
- Investment timing ("Is now a good time to buy?", "Should I wait?")
- Risk analysis ("What are the risks of NVDA?", "How risky is this stock?")
- Portfolio advice ("Should I diversify?", "What allocation?")
- Investment comparisons ("Which is better for investment: AAPL or GOOGL?")
- Financial outlook ("Is AMZN a good long-term investment?")

Route to 'stock' for MARKET DATA & PRICES:
- Stock PRICES, quotes, real-time data ("What's AAPL price?")
- Historical PRICE performance ("How has Tesla performed?")
- Market movers, gainers/losers ("Show me top gainers")
- Trading hours and market status ("Is the market open?")
- Multi-stock comparisons for DATA ("Compare AAPL vs MSFT prices")

Route to 'equity_insights' for COMPANY INFORMATION:
- Company PROFILES, overviews, about the company ("Tell me about Apple")
- Company SECTORS, business details ("What sector is Tesla in?")
- ANALYST ratings and recommendations ("What are analyst ratings for NVDA?")
- Company NEWS and press releases ("Show me recent news for MSFT")
- INSIDER trading activity ("Insider trading for AAPL")

Route to 'fallback' for:
- General knowledge questions
- Non-financial queries
- Weather, geography, science, etc.
- Any question not about stocks/finance

IMPORTANT DISTINCTION:
- "Should I buy AAPL?" → 'advisor' (investment recommendation)
- "What's AAPL price?" → 'stock' (market data)
- "Tell me about Apple" → 'equity_insights' (company info)
- "What are risks of AAPL?" → 'advisor' (risk analysis)
- "Analyst ratings for AAPL" → 'equity_insights' (data gathering)

PLANNING RULES:
- Analyze the FULL query and identify ALL tasks needed
- Return tasks as a comma-separated list in priority order
- Example: "Should I buy AAPL and what's its price?" → "advisor"
- Example: "Tell me about Apple's stock price" → "stock"
- Example: "Give me Tesla news and should I invest?" → "equity_insights,advisor"
- Example: "Compare AAPL vs GOOGL for investment" → "advisor"

Only respond with: 'advisor', 'stock', 'equity_insights', 'fallback', or comma-separated combinations"""

async def router_node(state: Dict) -> Dict:
    query = state.get("input", "")
    pending_tasks = state.get("pending_tasks", [])
    accumulated_results = state.get("accumulated_results", {})
    
    print(f"🔧 ROUTER - Query: '{query}', Pending: {pending_tasks}")
    
    # If no pending tasks, this is first time - plan the tasks
    if not pending_tasks:
        try:
            response = await anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                temperature=0,
                system=ROUTER_SYSTEM,
                messages=[{"role": "user", "content": f"Plan tasks for: {query}"}],
            )
            router_response = response.content[0].text.strip().lower()
            print(f"🔧 ROUTER - Planned tasks: '{router_response}'")
            
            # Parse tasks (comma-separated or single)
            if "," in router_response:
                all_tasks = [task.strip() for task in router_response.split(",")]
                first_task = all_tasks[0]
                remaining_tasks = all_tasks[1:]
            else:
                first_task = router_response
                remaining_tasks = []
            
            return {
                "route": first_task,
                "pending_tasks": remaining_tasks,
                "accumulated_results": accumulated_results
            }
            
        except Exception as e:
            print(f"❌ ROUTER - Error: {e}")
            return {"route": "fallback", "pending_tasks": [], "accumulated_results": accumulated_results}
    
    # Have pending tasks - execute next one
    else:
        next_task = pending_tasks[0]
        remaining_tasks = pending_tasks[1:]
        print(f"🔧 ROUTER - Next: {next_task}, Remaining: {remaining_tasks}")
        
        return {
            "route": next_task,
            "pending_tasks": remaining_tasks
        }
