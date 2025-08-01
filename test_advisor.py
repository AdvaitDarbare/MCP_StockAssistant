#!/usr/bin/env python3
"""
Test script for the advisor agent
"""

import asyncio
import aiohttp
import json

async def test_advisor():
    """Test the advisor agent directly"""
    
    test_queries = [
        "Should I buy AAPL?",
        "What are the risks of investing in Tesla?",
        "Is now a good time to invest in NVDA?",
        "Compare AAPL vs GOOGL for investment"
    ]
    
    print("🎯 Testing Advisor Agent...")
    print("Make sure the advisor agent is running on port 8003")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test {i}: {query}")
            print("-" * 30)
            
            try:
                async with session.post(
                    "http://localhost:8003/mcp",
                    json={"input": query},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        output = result.get("output", "No output")
                        print(f"✅ Status: {response.status}")
                        print(f"📄 Response: {output[:200]}...")
                        if len(output) > 200:
                            print(f"📏 Full length: {len(output)} characters")
                    else:
                        print(f"❌ Status: {response.status}")
                        error_text = await response.text()
                        print(f"Error: {error_text}")
                        
            except asyncio.TimeoutError:
                print("⏰ Request timed out")
            except Exception as e:
                print(f"❌ Error: {e}")
            
            print()

if __name__ == "__main__":
    asyncio.run(test_advisor())