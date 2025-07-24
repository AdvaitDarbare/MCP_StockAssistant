#!/bin/bash

# AI Stock Assistant Development Startup Script

echo " Starting AI Stock Assistant in Development Mode..."

# Kill any existing processes on these ports
echo " Cleaning up existing processes..."
pkill -f "uvicorn.*8000" 2>/dev/null
pkill -f "uvicorn.*stock_agent.*8020" 2>/dev/null
pkill -f "uvicorn.*equity_insight_agent.*8001" 2>/dev/null
pkill -f "langgraph dev" 2>/dev/null
pkill -f "react-scripts start" 2>/dev/null

# Wait for processes to terminate
sleep 2

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Main App
echo " Starting Main App (port 8000)..."
(cd backend && uvicorn app.main:app --reload --port 8000 > ../logs/main.log 2>&1) &

# Start Stock Agent
echo " Starting Stock Agent (port 8020)..."
(cd backend && uvicorn app.agents.stock_agent:app --reload --port 8020 > ../logs/stock_agent.log 2>&1) &

# Start Equity Insight Agent  
echo " Starting Equity Insight Agent (port 8001)..."
(cd backend && uvicorn app.agents.equity_insight_agent:app --reload --port 8001 > ../logs/equity_agent.log 2>&1) &

# Start Frontend
echo " Starting Frontend (port 3000)..."
(cd frontend && ./start.sh > ../logs/frontend.log 2>&1) &

# Wait for agents to start
echo "⏳ Waiting for services to initialize..."
sleep 8

# Start LangGraph Dev Server
echo " Starting LangGraph Development Server..."
langgraph dev

echo "✅ All services started successfully!"
echo ""
echo " Access your application at:"
echo "   -  Frontend UI: http://localhost:3000"
echo "   -  LangGraph Studio: http://localhost:8123"
echo "   -  Main App: http://localhost:8000"
echo "   -  Stock Agent: http://localhost:8020"  
echo "   -  Equity Agent: http://localhost:8001"
echo ""
echo " Check logs at:"
echo "   - Main App: logs/main.log"
echo "   - Frontend: logs/frontend.log"
echo "   - Stock Agent: logs/stock_agent.log"
echo "   - Equity Agent: logs/equity_agent.log"