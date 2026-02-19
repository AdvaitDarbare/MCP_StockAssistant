#!/bin/bash

# AI Stock Assistant Development Startup Script

echo " Starting AI Stock Assistant in Development Mode..."

# Kill any existing processes on these ports
echo " Cleaning up existing processes..."
pkill -f "uvicorn.*8001" 2>/dev/null
pkill -f "next" 2>/dev/null
pkill -f "langgraph dev" 2>/dev/null

# Wait for processes to terminate
sleep 2

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Backend API
echo " Starting Backend API (port 8001)..."
(poetry run uvicorn apps.api.gateway.main:app --host 127.0.0.1 --port 8001 --reload > logs/api.log 2>&1) &

# Start Frontend
echo " Starting Frontend (port 3001)..."
(npm run dev > logs/frontend.log 2>&1) &

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 4

echo "✅ All services started successfully!"
echo ""
echo " Access your application at:"
echo "   -  Frontend UI: http://localhost:3001"
echo "   -  API Health: http://localhost:8001/health"
echo ""
echo " Check logs at:"
echo "   - Backend API: logs/api.log"
echo "   - Frontend: logs/frontend.log"