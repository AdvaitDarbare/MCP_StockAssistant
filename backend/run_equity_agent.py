#!/usr/bin/env python3
"""
Equity Insights Agent Server - Runs on port 8001
Handles company information, news, analyst ratings, and insider trading
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path so we can import the equity agent
sys.path.append(str(Path(__file__).parent / 'app'))

from agents.equity_insight_agent import app
import uvicorn

if __name__ == "__main__":
    print("🏢 Starting Equity Insights Agent on port 8001...")
    print("📋 Features:")
    print("  - Company information and profiles")
    print("  - Latest company news and articles")
    print("  - Analyst ratings and recommendations")
    print("  - Insider trading activity")
    print("  - SEC filings and financial data")
    print("\n🚀 Ready for equity analysis queries!")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8001,
        log_level="info"
    )