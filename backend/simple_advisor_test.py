#!/usr/bin/env python3
"""
Simple advisor agent test - works without external dependencies
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
import asyncio
from anthropic import AsyncAnthropic
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

app = FastAPI()
anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

class MCPRequest(BaseModel):
    input: str
    state: dict | None = None

@app.post("/mcp")
async def simple_advisor(request: Request):
    try:
        body = await request.json()
        mcp_input = MCPRequest(**body)
        user_query = mcp_input.input
        
        print(f"🎯 SIMPLE ADVISOR - Query: '{user_query}'")
        
        # Extract symbol from query
        query_upper = user_query.upper()
        symbol = "AAPL"  # Default
        
        if "AAPL" in query_upper or "APPLE" in query_upper:
            symbol = "AAPL"
        elif "TSLA" in query_upper or "TESLA" in query_upper:
            symbol = "TSLA"
        elif "GOOGL" in query_upper or "GOOGLE" in query_upper:
            symbol = "GOOGL"
        elif "NVDA" in query_upper or "NVIDIA" in query_upper:
            symbol = "NVDA"
        
        # Generate advice
        advice_prompt = f"""You are an investment advisor. The user asks: "{user_query}"

Provide structured investment advice for {symbol}:

🎯 **Investment Recommendation for {symbol}**

📊 **General Analysis:**
- Provide general market perspective on this stock
- Note: Current market data unavailable

⚖️ **Risk Assessment:**
- Risk Level: Low/Medium/High
- Key risk factors for this stock/sector

💡 **Recommendation:** 
- Provide BUY/HOLD/SELL guidance with reasoning

⚠️ **Important Considerations:**
- General investment considerations
- Suggest getting current market data

📈 **Suggested Actions:**
- Specific actionable advice

Be helpful but mention data limitations. Include investment disclaimer."""

        try:
            response = await anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": advice_prompt}]
            )
            
            advice = response.content[0].text.strip()
            
            # Add disclaimer
            disclaimer = "\n\n⚠️ **DISCLAIMER**: This is educational information based on general knowledge and should not be considered personalized financial advice. Always verify with current market data and consult with a qualified financial advisor."
            
            final_advice = advice + disclaimer
            
            # Add follow-ups
            follow_ups = f"""

__FOLLOW_UPS_START__
1. 🎯 What are the risks of investing in {symbol}?
2. 📈 Is now a good time to buy {symbol}?
3. 📊 Compare {symbol} with other tech stocks
4. 💡 How much should I invest in {symbol}?
__FOLLOW_UPS_END__"""
            
            final_output = final_advice + follow_ups
            
            print(f"✅ SIMPLE ADVISOR - Generated: {len(final_output)} chars")
            return {"output": final_output}
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {"output": f"❌ Unable to generate investment advice: {e}"}
            
    except Exception as e:
        print(f"❌ SIMPLE ADVISOR Error: {e}")
        return {"output": f"❌ Advisor error: {e}"}

if __name__ == "__main__":
    print("🎯 Starting Simple Advisor Agent on port 8003...")
    uvicorn.run(app, host="127.0.0.1", port=8003)