#!/usr/bin/env python3
"""
Stock Agent Server - Runs on port 8020
Handles stock prices, market data, and trading information
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Now import with proper path
from app.agents.stock_agent import app
import uvicorn

if __name__ == "__main__":
    print("📈 Starting Stock Agent on port 8020...")
    print("📋 Features:")
    print("  - Real-time stock quotes")
    print("  - Price history and charts")
    print("  - Market movers and trends")
    print("  - Market hours information")
    print("  - Multi-stock comparisons")
    print("\n🚀 Ready for stock queries!")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8020,
        log_level="info"
    )