#!/usr/bin/env bash
# Quick start script for the Streamlit web app

echo "🛡️  =========================================="
echo "   Shieldient Stack Rationalization"
echo "   Web Interface (Streamlit)"
echo "=========================================="
echo ""
echo "📦 Installing dependencies..."
pip install -q streamlit plotly pandas 2>/dev/null

echo ""
echo "🚀 Launching Streamlit app..."
echo ""
echo "   🌐 App will open at: http://localhost:8501"
echo "   📊 Use Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

streamlit run streamlit_app.py
