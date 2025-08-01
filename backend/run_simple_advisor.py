#!/usr/bin/env python3
"""
Simple Advisor Agent - Always responds, no external dependencies
Port: 8003
"""

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from anthropic import AsyncAnthropic
import os
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

app = FastAPI()
anthropic = AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

class MCPRequest(BaseModel):
    input: str
    state: dict | None = None

def extract_symbol_from_query(query: str) -> str:
    """Extract stock symbol from user query"""
    query_upper = query.upper()
    
    # Direct symbol matches
    symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "NFLX", "CRM", "ORCL"]
    for symbol in symbols:
        if symbol in query_upper:
            return symbol
    
    # Company name mapping
    company_mapping = {
        "APPLE": "AAPL", "TESLA": "TSLA", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
        "MICROSOFT": "MSFT", "AMAZON": "AMZN", "NVIDIA": "NVDA",
        "META": "META", "FACEBOOK": "META", "NETFLIX": "NFLX"
    }
    
    for company, symbol in company_mapping.items():
        if company in query_upper:
            return symbol
    
    return "AAPL"  # Default fallback

@app.post("/mcp")
async def handle_advisor_request(request: Request):
    try:
        body = await request.json()
        mcp_input = MCPRequest(**body)
        user_query = mcp_input.input
        
        print(f"🎯 SIMPLE ADVISOR - Processing: '{user_query}'")
        
        # Extract symbol
        symbol = extract_symbol_from_query(user_query)
        print(f"🎯 SIMPLE ADVISOR - Symbol detected: {symbol}")
        
        # Generate investment advice
        advice_prompt = f"""You are a professional investment advisor. Provide structured investment advice for this query: "{user_query}"

The stock symbol is: {symbol}

Provide advice in this EXACT format:

🎯 **Investment Recommendation for {symbol}**

📊 **Current Analysis:**
- Provide general analysis of {symbol} (use your knowledge of the company)
- Note any current market factors (general tech/market conditions)
- Mention data limitations if relevant

⚖️ **Risk Assessment:**
- Risk Level: Low/Medium/High (with brief explanation)
- Key Risk Factors: List 2-3 specific risks for this stock
- Sector Risks: Relevant industry/sector considerations

💡 **Recommendation: BUY/HOLD/SELL**
**Reasoning:** Provide 2-3 key points supporting your recommendation based on:
- Company fundamentals and market position
- Current market conditions 
- Risk/reward profile

⚠️ **Important Considerations:**
- Timing factors and market conditions
- Position sizing recommendations
- Risk management suggestions

📈 **Actionable Advice:**
1. Specific first step (e.g., "Start with 2-5% portfolio allocation")
2. Monitoring suggestion (e.g., "Watch for Q4 earnings on [date]")
3. Risk management (e.g., "Set stop-loss at X% below entry")

Keep the advice practical, balanced, and educational. Use your general knowledge about {symbol} and the current market environment."""

        try:
            print(f"🎯 SIMPLE ADVISOR - Calling Claude for advice...")
            response = await anthropic.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1200,
                temperature=0.3,
                messages=[{"role": "user", "content": advice_prompt}]
            )
            
            advice = response.content[0].text.strip()
            print(f"🎯 SIMPLE ADVISOR - Claude response received: {len(advice)} chars")
            
            # Add disclaimer
            disclaimer = "\n\n⚠️ **DISCLAIMER**: This is educational information based on general market knowledge and should not be considered personalized financial advice. Always verify with current market data and consult with a qualified financial advisor before making investment decisions."
            
            # Add follow-up suggestions
            follow_ups = f"""

__FOLLOW_UPS_START__
1. ⚖️ What are the main risks of investing in {symbol}?
2. ⏰ Is now a good time to buy {symbol}?
3. 📊 Compare {symbol} with similar stocks for investment
4. 💰 How much of my portfolio should be in {symbol}?
__FOLLOW_UPS_END__"""
            
            final_output = advice + disclaimer + follow_ups
            
            print(f"✅ SIMPLE ADVISOR - Final response: {len(final_output)} chars")
            return {"output": final_output}
            
        except Exception as e:
            print(f"❌ SIMPLE ADVISOR - Claude API error: {e}")
            
            # Fallback response
            fallback_advice = f"""🎯 **Investment Recommendation for {symbol}**

📊 **Current Analysis:**
- {symbol} is a well-known stock in the market
- Unable to access current market data at this time
- General market knowledge suggests this is an established company

⚖️ **Risk Assessment:**
- Risk Level: Medium (typical for most stocks)
- Market Risk: General market volatility affects all stocks
- Company Risk: Varies by company fundamentals

💡 **Recommendation: RESEARCH NEEDED**
**Reasoning:** Without current data, thorough research is essential before making investment decisions.

⚠️ **Important Considerations:**
- Obtain current financial data and analyst reports
- Check recent news and earnings reports
- Consider your risk tolerance and investment timeline

📈 **Actionable Advice:**
1. Research current {symbol} fundamentals and recent performance
2. Consult current analyst ratings and price targets
3. Consider your overall portfolio allocation before investing

⚠️ **DISCLAIMER**: This is general educational information. Always do your own research and consult with qualified financial advisors."""
            
            return {"output": fallback_advice}
            
    except Exception as e:
        print(f"❌ SIMPLE ADVISOR - Request error: {e}")
        return JSONResponse(
            status_code=500,
            content={"output": f"❌ Investment advisor temporarily unavailable: {str(e)}"}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "simple_advisor"}

if __name__ == "__main__":
    print("🎯 Starting Simple Investment Advisor on port 8003...")
    print("📋 Features:")
    print("  - Fast, reliable investment advice")
    print("  - No external dependencies")
    print("  - Structured recommendations")
    print("  - Built-in fallbacks")
    print("\n🚀 Ready for investment queries!")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8003,
        log_level="info"
    )