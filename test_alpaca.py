import asyncio
import os
from dotenv import load_dotenv

# Set PYTHONPATH to root so we can import apps
import sys
sys.path.append(os.getcwd())

load_dotenv()

from apps.api.config import settings
print(f"API Key Configured: {settings.ALPACA_API_KEY[:5]}...")

from apps.api.services.alpaca_client import get_alpaca_history, get_alpaca_quote, get_alpaca_news

async def test():
    print("Testing Alpaca API...")
    
    print("\n1. Testing Quote (AAPL):")
    quote = await get_alpaca_quote("AAPL")
    print(quote)
    
    print("\n2. Testing History (SPY):")
    history = await get_alpaca_history("SPY", limit=10)
    print(f"History Result: {history}")
    
    print("\n3. Testing News (AAPL):")
    news = await get_alpaca_news("AAPL", limit=2)
    print(news)

if __name__ == "__main__":
    asyncio.run(test())
