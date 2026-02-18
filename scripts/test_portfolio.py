import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.agents.portfolio.tools import add_transaction, get_holdings, manage_watchlist
from apps.api.config import settings
from apps.api.db.database import init_db, close_db

async def test_portfolio():
    await init_db()
    try:
        print(f"Testing Portfolio Tools for User: {settings.DEV_USER_ID}")
        
        # 1. Add a transaction
        print("\n1. Adding Transaction (Buy 10 AAPL @ 150)...")
        tx = await add_transaction.ainvoke({
            "symbol": "AAPL",
            "action": "buy",
            "shares": 10.0,
            "price": 150.0,
            "notes": "Test buy"
        })
        print(f"   Transaction recorded: {tx.get('id')}")
        
        # 2. Add another transaction (Buy 5 NVDA @ 400)
        print("\n2. Adding Transaction (Buy 5 NVDA @ 400)...")
        await add_transaction.ainvoke({
            "symbol": "NVDA",
            "action": "buy",
            "shares": 5.0,
            "price": 400.0,
            "notes": "Test buy 2"
        })
        
        # 3. Get Holdings
        print("\n3. Retrieving Holdings...")
        holdings = await get_holdings.ainvoke({})
        for h in holdings:
            print(f"   - {h['symbol']}: {h['shares']} shares @ ${h['avg_cost']}")
            
        # Validation
        aapl = next((h for h in holdings if h['symbol'] == 'AAPL'), None)
        if aapl and float(aapl['shares']) == 10.0:
            print("   -> AAPL verified.")
        else:
            print("   -> ARRH! AAPL verification failed.")
            
        # 4. Watchlist
        print("\n4. Managing Watchlist (Adding TSLA)...")
        await manage_watchlist.ainvoke({"action": "add", "symbol": "TSLA", "target_low": 180.0})
        wl = await manage_watchlist.ainvoke({"action": "view", "symbol": "irrelevent"})
        print(f"   Watchlist items: {[w['symbol'] for w in wl]}")
        
        if any(w['symbol'] == 'TSLA' for w in wl):
            print("   -> TSLA verified in watchlist.")
    
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(test_portfolio())
