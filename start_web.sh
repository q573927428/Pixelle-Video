#!/bin/bash
# Start Pixelle-Video Web UI

UI_MODE="$1"

if [ -z "$UI_MODE" ]; then
  echo "🚀 Pixelle-Video UI Launcher"
  echo ""
  echo "Please choose a UI:"
  echo "  [1] Classic UI  - Streamlit full toolset"
  echo "  [2] Modern UI   - FastAPI + Vue 3 software-style UI"
  echo ""
  read -r -p "Select 1 or 2: " choice
  case "$choice" in
    2) UI_MODE="modern" ;;
    *) UI_MODE="classic" ;;
  esac
fi

case "$UI_MODE" in
  1|classic|Classic|CLASSIC)
    echo "🚀 Starting Pixelle-Video Classic Streamlit UI..."
    echo ""
    echo "Classic UI keeps all existing tools fully available."
    echo ""
    uv run streamlit run web/app.py
    ;;
  2|modern|Modern|MODERN)
    echo "🚀 Starting Pixelle-Video Modern UI..."
    echo ""
    echo "Modern UI: http://localhost:8000/modern"
    echo "API Docs:  http://localhost:8000/docs"
    echo ""
    uv run python api/app.py --host 0.0.0.0 --port 8000
    ;;
  *)
    echo "Unknown UI mode: $UI_MODE"
    echo "Usage:"
    echo "  ./start_web.sh classic"
    echo "  ./start_web.sh modern"
    exit 1
    ;;
esac