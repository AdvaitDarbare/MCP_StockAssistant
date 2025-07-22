from fastapi import FastAPI, Request
from pydantic import BaseModel
import httpx
import os
import anthropic

app = FastAPI()

# Define input and output for MCP
class MCPInput(BaseModel):
    input: str

class MCPOutput(BaseModel):
    output: str

# Claude API client setup
client = anthropic.Anthropic(
    api_key=os.environ.get("CLAUDE_API_KEY")  # Set this in your .env or shell
)

# Function to determine which agent to use
async def route_query(user_query: str) -> str:
    system_prompt = "You are a routing assistant that decides the best agent to call for a stock assistant."
    user_prompt = f"""Given the user query below, respond ONLY with one of the following:
- stock
- news
- fallback

User Query: {user_query}
Agent:"""

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=5,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    return response.content[0].text.strip().lower()

# Routes to different agents
AGENT_ENDPOINTS = {
    "stock": "http://localhost:8020/mcp",
    "news": "http://localhost:8030/mcp",      # ← you'll create this next
    "fallback": "http://localhost:8040/mcp"   # ← fallback agent
}

@app.post("/mcp", response_model=MCPOutput)
async def mcp_router(req: MCPInput):
    query = req.input

    try:
        target_agent = await route_query(query)
    except Exception as e:
        return {"output": f"Error routing request: {e}"}

    url = AGENT_ENDPOINTS.get(target_agent, AGENT_ENDPOINTS["fallback"])

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={"input": query})
            return {"output": resp.json().get("output", "No response")}
    except Exception as e:
        return {"output": f"Error contacting {target_agent} agent: {e}"}
