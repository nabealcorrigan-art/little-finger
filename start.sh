#!/bin/bash
# Startup script for Little Finger Ring Monitor

echo "╔════════════════════════════════════════════════╗"
echo "║   Little Finger - Ring Neighborhood Monitor   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "❌ config.json not found"
    echo "   Please create config.json with your Ring credentials"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting Little Finger Monitor..."
echo "   Access dashboard at: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

# Start the server
python3 server.py
