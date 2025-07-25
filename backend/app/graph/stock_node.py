# stock_node.py
import httpx
from typing import Dict

async def stock_node(state: Dict) -> Dict:
    """Stock node that handles price, market data, and trading information"""
    query = state.get("input", "")
    accumulated_results = state.get("accumulated_results", {})
    
    print(f"📈 STOCK - Processing: '{query}'")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8020/mcp", 
                json={"input": query},
                timeout=15.0,
            )
            if response.status_code == 200:
                stock_output = response.json().get("output", "Stock agent did not respond.")
            else:
                stock_output = f"❌ Stock service error (status: {response.status_code})"
    except Exception as e:
        stock_output = f"❌ Stock agent error: {str(e)}"
    
    # Store result
    updated_results = accumulated_results.copy()
    updated_results["stock"] = stock_output

    return {
        "accumulated_results": updated_results
    }
