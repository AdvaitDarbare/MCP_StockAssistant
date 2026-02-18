import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.agents.advisor.agent import advisor_node
from apps.api.agents.portfolio.tools import add_transaction
from apps.api.db.database import init_db, close_db

async def test_advisor():
    print("----- Testing Advisor Agent -----")
    
    # 0. Initialize DB
    await init_db()
    
    try:
        # 1. Setup Data (Optional)
        # 2. Test the agent
        state = {
            "messages": [
                {"role": "user", "content": "I have some Apple stock. Is my portfolio diversified?"}
            ]
        }
        
        print(f"Input: {state['messages'][0]['content']}")
        
        response = await advisor_node(state)
        print("\nResponse:")
        print(response["messages"][-1].content)
        print("\n[SUCCESS] Advisor agent executed.")
    except Exception as e:
        print(f"\n[ERROR] Advisor execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(test_advisor())
