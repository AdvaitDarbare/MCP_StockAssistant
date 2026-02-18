import asyncio
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.agents.market_data.tools import get_quote
from apps.api.services.cache import CacheService

async def test_cache():
    print("Testing Redis Cache logic...")
    symbol = "TSLA"
    
    # Clear cache first to ensure clean state
    cache = CacheService()
    await cache.delete(f"market_data:{symbol}:price")
    
    # 1. First Call (Miss)
    print("\n1. First Call (Cache Miss)...")
    start = time.time()
    res1 = await get_quote.ainvoke({"symbol": symbol})
    end = time.time()
    print(f"   Time: {end - start:.4f}s")
    print(f"   Price: {res1['price']}")
    print(f"   Timestamp: {res1['timestamp']}")
    
    # 2. Second Call (Hit)
    print("\n2. Second Call (Cache Hit)...")
    start = time.time()
    res2 = await get_quote.ainvoke({"symbol": symbol})
    end = time.time()
    print(f"   Time: {end - start:.4f}s")
    print(f"   Price: {res2['price']}")
    print(f"   Timestamp: {res2['timestamp']}")
    
    # Verification
    if res1['timestamp'] == res2['timestamp']:
        print("\nSUCCESS: Timestamps match! Data was retrieved from cache.")
    else:
        print("\nFAILURE: Timestamps differ! Cache was not used.")
        
    await cache.close()

if __name__ == "__main__":
    asyncio.run(test_cache())
