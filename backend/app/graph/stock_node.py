# stock_node.py
import httpx
from typing import Dict

def stock_node(state: Dict) -> Dict:
    query = state["input"]

    try:
        response = httpx.post(
            "http://localhost:8020/mcp",  # MCP endpoint for stock agent
            json={"input": query},
            timeout=10.0,
        )
        output = response.json().get("output", "Stock agent did not respond.")
    except Exception as e:
        output = f"Stock agent error: {str(e)}"

    return {"output": output}
