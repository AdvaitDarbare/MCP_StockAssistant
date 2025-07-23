# backend/app/graph/equity_insight_node.py

from typing import Dict
import httpx
import json

EQUITY_INSIGHT_MCP_URL = "http://localhost:8001/mcp"  # EquityInsightAgent endpoint

async def equity_insight_node(state: Dict) -> Dict:
    """Node to handle equity insights queries by calling the EquityInsightAgent MCP endpoint"""
    
    query = state.get("input", "")
    
    try:
        # Call the EquityInsightAgent MCP endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EQUITY_INSIGHT_MCP_URL,
                json={"input": query},
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                output = result.get("output", "❌ No response from equity insights service")
            else:
                output = f"❌ Equity insights service error (status: {response.status_code})"
                
    except httpx.RequestError as e:
        output = f"❌ Failed to connect to equity insights service: {str(e)}"
    except json.JSONDecodeError:
        output = "❌ Invalid response from equity insights service"
    except Exception as e:
        output = f"❌ Unexpected error calling equity insights service: {str(e)}"
    
    return {"output": output}