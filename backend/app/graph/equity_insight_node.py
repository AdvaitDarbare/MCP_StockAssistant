# backend/app/graph/equity_insight_node.py

from typing import Dict
import httpx
import json

EQUITY_INSIGHT_MCP_URL = "http://localhost:8001/mcp"  # EquityInsightAgent endpoint

async def equity_insight_node(state: Dict) -> Dict:
    """Equity insights node that handles company information, news, and analysis"""
    query = state.get("input", "")
    accumulated_results = state.get("accumulated_results", {})
    
    print(f"🏢 EQUITY_INSIGHTS - Processing: '{query}'")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EQUITY_INSIGHT_MCP_URL,
                json={"input": query},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                equity_output = result.get("output", "❌ No response from equity insights service")
            else:
                equity_output = f"❌ Equity insights service error (status: {response.status_code})"
                
    except Exception as e:
        equity_output = f"❌ Equity insights error: {str(e)}"
    
    # Store result
    updated_results = accumulated_results.copy()
    updated_results["equity_insights"] = equity_output
    
    return {
        "accumulated_results": updated_results
    }