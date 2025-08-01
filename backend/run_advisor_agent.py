#!/usr/bin/env python3
"""
Advisor Agent Service - Investment recommendations and risk analysis
Port: 8003
"""

import uvicorn
from app.agents.advisor_agent import app

if __name__ == "__main__":
    print("🎯 Starting Investment Advisor Agent on port 8003...")
    print("📊 Features:")
    print("  - Investment buy/sell recommendations") 
    print("  - Risk analysis and assessment")
    print("  - Portfolio advice and timing")
    print("  - Multi-agent data gathering")
    print("  - LLM-powered synthesis")
    print("\n💡 Example queries:")
    print("  - 'Should I buy AAPL stock?'")
    print("  - 'What are the risks of investing in TSLA?'")
    print("  - 'Is now a good time to invest in NVDA?'")
    print("  - 'Compare AAPL vs GOOGL for investment'")
    print("\n🚀 Ready to provide investment guidance!")
    
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8003,
        log_level="info",
        access_log=False
    )