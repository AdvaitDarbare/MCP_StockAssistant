# backend/app/graph/advisor_node.py

from typing import Dict
import aiohttp
import asyncio

async def advisor_node(state: Dict) -> Dict:
    """Investment advisor node that provides buy/sell recommendations and risk analysis"""
    user_input = state.get("input", "")
    
    print(f"🎯 ADVISOR NODE - Processing: '{user_input}'")
    
    try:
        # Call the advisor agent
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8003/mcp",  # Advisor agent port
                json={"input": user_input},
                timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for complex analysis
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    output = result.get("output", "No advice available")
                    
                    print(f"✅ ADVISOR NODE - Success: {len(output)} chars")
                    
                    # Update accumulated results
                    accumulated_results = state.get("accumulated_results", {})
                    accumulated_results["advisor"] = output
                    
                    # Remove this task from pending
                    pending_tasks = state.get("pending_tasks", [])
                    if "advisor" in pending_tasks:
                        pending_tasks.remove("advisor")
                    
                    return {
                        **state,
                        "accumulated_results": accumulated_results,
                        "pending_tasks": pending_tasks
                    }
                else:
                    error_msg = f"Advisor agent returned status {response.status}"
                    print(f"❌ ADVISOR NODE - {error_msg}")
                    
                    return {
                        **state,
                        "output": f"❌ Investment advisor error: {error_msg}"
                    }
                    
    except asyncio.TimeoutError:
        error_msg = "Investment advisor timed out"
        print(f"❌ ADVISOR NODE - {error_msg}")
        return {
            **state,
            "output": f"❌ {error_msg}. Please try again with a simpler query."
        }
        
    except Exception as e:
        error_msg = f"Investment advisor error: {str(e)}"
        print(f"❌ ADVISOR NODE - {error_msg}")
        return {
            **state,
            "output": f"❌ {error_msg}"
        }