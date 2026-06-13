#!/bin/bash
# Start Pixelle-Video Modern UI

echo "🚀 Starting Pixelle-Video Modern UI..."
echo ""
echo "Modern UI: http://localhost:8000/modern"
echo "API Docs:  http://localhost:8000/docs"
echo ""
uv run python api/app.py --host 0.0.0.0 --port 8000
