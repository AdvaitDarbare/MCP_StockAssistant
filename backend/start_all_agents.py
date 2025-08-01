#!/usr/bin/env python3
"""
AI Stock Assistant - Agent Startup Guide

This script shows you which agents need to be running and how to start them.
The AI Stock Assistant requires multiple specialized agents for full functionality.
"""

import os
import sys
from pathlib import Path

def main():
    print("🚀 AI Stock Assistant - Agent Services")
    print("=" * 50)
    
    print("\n📋 Required Services:")
    print("1. 📈 Stock Agent (Port 8020) - Stock prices, market data")
    print("2. 🏢 Equity Insights Agent (Port 8001) - Company info, news, analysis") 
    print("3. 🎯 Advisor Agent (Port 8003) - Investment advice")
    print("4. 📰 News Agent (Port 8030) - Market news")
    print("5. 🔄 Fallback Agent (Port 8040) - Backup responses")
    print("6. 🌐 Main API Server (Port 2024) - Frontend interface")
    
    print("\n🔧 Available Runners:")
    backend_path = Path(__file__).parent
    
    # Check for available runners
    runners = [
        ("run_stock_agent.py", "📈 Stock Agent", 8020),
        ("run_simple_advisor.py", "🎯 Advisor Agent", 8003),
        ("app/main.py", "🌐 Main API Server", 2024)
    ]
    
    print("\n✅ Ready to Start:")
    for runner, description, port in runners:
        runner_path = backend_path / runner
        if runner_path.exists():
            print(f"   python {runner} → {description} (Port {port})")
        else:
            print(f"   ❌ Missing: {runner}")
    
    print("\n⚠️  Missing Services:")
    missing_services = [
        ("🏢 Equity Insights Agent", 8001, "Need to create runner"),
        ("📰 News Agent", 8030, "Need to create runner"), 
        ("🔄 Fallback Agent", 8040, "Need to create runner")
    ]
    
    for service, port, status in missing_services:
        print(f"   {service} (Port {port}) - {status}")
    
    print("\n🚀 Quick Start (Available Services):")
    print("# Terminal 1:")
    print("cd backend && python run_stock_agent.py")
    print("\n# Terminal 2:")  
    print("cd backend && python run_simple_advisor.py")
    print("\n# Terminal 3:")
    print("cd backend && python app/main.py")
    print("\n# Terminal 4:")
    print("cd frontend && npm run start")
    
    print("\n💡 Note: The stock agent error you're seeing happens because")
    print("   the Stock Agent (port 8020) isn't running. Start it first!")
    
    print("\n📖 For full functionality, you'll need all agents running.")
    print("   Currently you can test with: Stock Agent + Advisor + Main API")

if __name__ == "__main__":
    main()