# fallback_node.py
from typing import Dict

def fallback_node(state: Dict) -> Dict:
    """
    Fallback node for non-financial queries or errors
    """
    print("❌ FALLBACK - Handling non-financial or error query")
    
    return {"output": "📈 I'm a Stock Assistant focused on providing financial data and stock information. Please ask me about stock prices, company performance, market data, or other finance-related questions.\n\nFor example:\n• \"What's the price of AAPL?\"\n• \"How is Tesla stock doing?\"\n• \"Show me Microsoft's current quote\"\n• \"Give me Apple's price and recent news\""}
