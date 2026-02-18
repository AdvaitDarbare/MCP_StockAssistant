import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.agents.memory.manager import MemoryManager

async def test_memory():
    manager = MemoryManager()
    
    print("1. Saving a new fact...")
    user_input = "My favorite stock is NVDA because I like GPUs."
    agent_output = "Noted, I'll remember that you like NVDA and GPUs."
    
    await manager.save_interaction(user_input, agent_output)
    print("   Saved.")
    
    print("\n2. Retrieving context for a related query...")
    query = "What companies should I invest in if I like chips?"
    results = await manager.get_relevant_context(query)
    
    print(f"   Found {len(results)} relevant items.")
    for i, res in enumerate(results):
        print(f"   [{i+1}] {res['content']}")
        
    # Check if our fact is there
    found = any("NVDA" in res['content'] for res in results)
    
    if found:
        print("\nSUCCESS: Memory retrieved correctly!")
    else:
        print("\nFAILURE: Did not find the stored fact.")

if __name__ == "__main__":
    asyncio.run(test_memory())
