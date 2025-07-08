#!/bin/bash

echo "🤖 Starting Autonomous AI Agent System..."
echo "=================================="

# Activate virtual environment
source venv/bin/activate

# Set environment variables (you can update these with real API keys)
export OPENAI_API_KEY="your-openai-api-key-here"
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# Start the system
echo "🌐 Starting web interface on http://localhost:8000"
echo "📊 Access the dashboard to monitor and control the agent"
echo ""
echo "Press Ctrl+C to stop the system"
echo ""

python main.py --mode both --host 0.0.0.0 --port 8000