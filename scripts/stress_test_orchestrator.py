import asyncio
import json
import httpx
import time
from typing import List, Dict, Any

BASE_URL = "http://127.0.0.1:8001/api/chat"

class StressTestResult:
    def __init__(self, name: str):
        self.name = name
        self.success = False
        self.agents_involved = set()
        self.tools_used = set()
        self.duration = 0
        self.final_content = ""
        self.error = None

    def __repr__(self):
        status = "✅ PASS" if self.success else "❌ FAIL"
        return (f"{status} | {self.name} | {self.duration:.2f}s\n"
                f"   Agents: {', '.join(self.agents_involved)}\n"
                f"   Tools: {', '.join(self.tools_used)}\n"
                f"   Error: {self.error}")

async def run_scenario(name: str, messages: List[Dict[str, str]], conversation_id: str = None) -> StressTestResult:
    result = StressTestResult(name)
    start_time = time.time()
    
    payload = {
        "messages": messages,
        "conversation_id": conversation_id or f"stress-{int(time.time())}",
        "user_id": "stress-tester"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", BASE_URL, json=payload) as response:
                if response.status_code != 200:
                    result.error = f"HTTP {response.status_code}: {await response.aread()}"
                    return result

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    try:
                        data = json.loads(line[6:])
                        msg_type = data.get("type")
                        
                        if msg_type == "agent_start":
                            result.agents_involved.add(data.get("agent"))
                        elif msg_type == "report_metadata":
                            report_type = data.get("report_type")
                            if report_type:
                                result.agents_involved.add(f"report:{report_type}")
                        elif msg_type == "tool_start":
                            result.tools_used.add(data.get("tool"))
                        elif msg_type == "final":
                            result.final_content = data.get("content")
                        elif msg_type == "error":
                            result.error = data.get("message")
                        
                    except json.JSONDecodeError:
                        continue

    except Exception as e:
        result.error = str(e)

    result.duration = time.time() - start_time
    # Success if we got final content and no fatal error
    if result.final_content and not result.error:
        result.success = True
    
    return result

async def main():
    print("🚀 Starting Comprehensive Agentic Stress Test Suite\n")
    
    scenarios = [
        {
            "name": "Single Ticker Deep Dive (Multi-Agent)",
            "messages": [{"role": "user", "content": "Analyze $NVDA. Check its current RSI, its latest earnings headlines, and its P/E vs industry average."}]
        },
        {
            "name": "Macro-Driven Correlation",
            "messages": [{"role": "user", "content": "How is the 10-year treasury yield trending according to FRED, and what does that mean for $AAPL's valuation?"}]
        },
        {
            "name": "Cross-Agent Sentiment Alignment",
            "messages": [{"role": "user", "content": "Compare the technical setup of $TSLA with the current sentiment on Reddit and the web. Are they aligned?"}]
        },
        {
            "name": "Intent-Based Report Routing",
            "messages": [{"role": "user", "content": "I need a Citadel-style technical report for PLTR."}]
        }
    ]

    # Portfolio Scenario (Complex Payload)
    scenarios.append({
        "name": "Complex Multi-Step Intent",
        "messages": [{"role": "user", "content": "I want to build a portfolio for a 40-year old with moderate risk, but first tell me if semiconductors are in a bubble based on technicals of AMD."}]
    })

    results = []
    for scenario in scenarios:
        print(f"Running scenario: {scenario['name']}...")
        res = await run_scenario(scenario["name"], scenario["messages"])
        results.append(res)
        print(res)
        print("-" * 50)
        await asyncio.sleep(2) # Ease up on APIs

    # Multi-Turn Sequence
    print("Running Multi-Turn Sequence...")
    conv_id = f"multi-turn-{int(time.time())}"
    turn1 = await run_scenario(
        "Multi-Turn Step 1: Citadel Report", 
        [{"role": "user", "content": "Get me a Citadel report for AMD."}],
        conversation_id=conv_id
    )
    results.append(turn1)
    print(turn1)
    
    await asyncio.sleep(2)
    
    turn2 = await run_scenario(
        "Multi-Turn Step 2: Competitive Follow-up",
        [
            {"role": "user", "content": "Get me a Citadel report for AMD."},
            {"role": "assistant", "content": turn1.final_content},
            {"role": "user", "content": "Now compare that technical outlook with its competitive position in AI chips using a Bain style report."}
        ],
        conversation_id=conv_id
    )
    results.append(turn2)
    print(turn2)

    print("\n📊 FINAL SUMMARY")
    passed = len([r for r in results if r.success])
    print(f"Passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("✅ ALL SYSTEMS GO")
    else:
        print("⚠️ SOME FAILURES DETECTED")

if __name__ == "__main__":
    asyncio.run(main())
