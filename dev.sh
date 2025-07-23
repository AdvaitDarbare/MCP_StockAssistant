#!/bin/bash

# AI Stock Assistant Development Startup Script

echo "🚀 Starting AI Stock Assistant in Development Mode..."

# Kill any existing processes on these ports
echo "🧹 Cleaning up existing processes..."
pkill -f "uvicorn.*stock_agent.*8020" 2>/dev/null
pkill -f "uvicorn.*equity_insight_agent.*8001" 2>/dev/null
pkill -f "langgraph dev" 2>/dev/null

# Wait for processes to terminate
sleep 2

# Start Stock Agent
echo "📈 Starting Stock Agent (port 8020)..."
(cd backend && uvicorn app.agents.stock_agent:app --reload --port 8020 > ../logs/stock_agent.log 2>&1) &

# Start Equity Insight Agent  
echo "🏢 Starting Equity Insight Agent (port 8001)..."
(cd backend && uvicorn app.agents.equity_insight_agent:app --reload --port 8001 > ../logs/equity_agent.log 2>&1) &

# Wait for agents to start
echo "⏳ Waiting for agents to initialize..."
sleep 5

# Start LangGraph Dev Server
echo "🔗 Starting LangGraph Development Server..."
langgraph dev

echo "✅ All services started successfully!"
echo ""
echo "🌐 Access your application at:"
echo "   - LangGraph Studio: http://localhost:8123"
echo "   - Stock Agent: http://localhost:8020"  
echo "   - Equity Agent: http://localhost:8001"
echo ""
echo "📊 Check logs at:"
echo "   - Stock Agent: logs/stock_agent.log"
echo "   - Equity Agent: logs/equity_agent.log"