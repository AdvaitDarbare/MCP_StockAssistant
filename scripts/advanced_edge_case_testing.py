import asyncio
import json
import httpx
import time

BASE_URL = "http://127.0.0.1:8001/api/chat"

async def run_complex_query(query: str):
    print(f"--- QUERY: {query} ---")
    payload = {
        "messages": [{"role": "user", "content": query}],
        "conversation_id": f"complex-{int(time.time())}",
        "user_id": "comprehensive-tester"
    }
    
    agents = set()
    tools = set()
    final_text = ""
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", BASE_URL, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        t = data.get("type")
                        if t == "agent_start":
                            agents.add(data.get("agent"))
                        elif t == "tool_start":
                            tools.add(data.get("tool"))
                        elif t == "final":
                            final_text = data.get("content")
                        elif t == "error":
                            print(f"   [ERROR] {data.get('message')}")
    except Exception as e:
        print(f"   [EXCEPTION] {e}")

    print(f"   Agents involved: {agents}")
    print(f"   Tools used: {tools}")
    print(f"   Response Length: {len(final_text)} chars")
    if final_text:
        print(f"   Preview: {final_text[:200]}...")
    print("-" * 50)

async def main():
    # 1. Multi-Question Single-Turn
    await run_complex_query("What is the current 10-Year Treasury yield, what is MSFT's current price, and what is the top news for Bitcoin?")
    
    # 2. Reasoning/Analysis (Requires multiple agents interacting)
    await run_complex_query("Analyze the impact of a rising unemployment rate on the technology sector, specifically comparing the technical setups of $GOOGL and $AMZN.")
    
    # 3. Edge Case: Non-existent Ticker
    await run_complex_query("Give me a deep dive analysis on $NONEXISTENT_TKR.")

    # 4. Large response/Complex formatting
    await run_complex_query("Build a detailed comparison table between AAPL, MSFT, and GOOGL covering P/E ratio, market cap, and latest RSI reading.")

if __name__ == "__main__":
    asyncio.run(main())
