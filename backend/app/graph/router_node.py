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

ROUTER_SYSTEM = """You are a router agent. You decide where to route a query: 'stock' or 'fallback'.

Route to 'stock' ONLY for:
- Stock prices, quotes, financial data
- Company stock performance
- Market analysis for specific stocks
- Trading information

Route to 'fallback' for:
- General knowledge questions
- Non-financial queries
- Weather, geography, science, etc.
- Any question not about stocks/finance

Only respond with one word: 'stock' or 'fallback'"""

async def router_node(state: Dict) -> Dict:
    query = state.get("input", "")

    response = await anthropic.messages.create(
        model="claude-3-haiku-20240307",  # or Opus/Sonnet if preferred
        max_tokens=1,
        temperature=0,
        system=ROUTER_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )

    route = response.content[0].text.strip().lower()
    decided_route = "stock" if route == "stock" else "fallback"
    
    return {"route": decided_route}
