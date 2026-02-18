#!/bin/bash

# AI Stock Assistant - Quick Start Script
# Starts all necessary services for development

echo "🚀 Starting AI Stock Assistant..."
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p apps/api/db

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services (Postgres, Redis, Qdrant)..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker ps | grep -q "stock-assistant-db"; then
    echo "✅ Postgres ready"
else
    echo "⚠️  Postgres may not be ready yet"
fi

if docker ps | grep -q "stock-assistant-redis"; then
    echo "✅ Redis ready"
else
    echo "⚠️  Redis may not be ready yet"
fi

if docker ps | grep -q "stock-assistant-qdrant"; then
    echo "✅ Qdrant ready"
else
    echo "⚠️  Qdrant may not be ready yet"
fi

echo ""
echo "========================================="
echo "✅ Phase 1 Complete - Services Ready!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Backend (Terminal 1):"
echo "   cd backend"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "2. Start Frontend (Terminal 2):"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "3. Access Application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   Postgres: localhost:5435"
echo "   Redis: localhost:6380"
echo "   Qdrant: localhost:6333"
echo ""
echo "4. Test Streaming:"
echo "   Open http://localhost:3000 and send a query!"
echo "   You should see real-time agent status updates."
echo ""
echo "========================================="
echo ""
echo "💡 Tip: Check logs/ directory for structured logs"
echo "💡 Run 'docker-compose logs -f' to see Docker logs"
echo ""

