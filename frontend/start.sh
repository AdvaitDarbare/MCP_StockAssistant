#!/bin/bash

echo "🎨 Starting AI Stock Assistant Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Set the API URL environment variable
export REACT_APP_API_URL="http://127.0.0.1:2024"

# Start the React development server
echo "🚀 Starting React development server on http://localhost:3000"
npm start