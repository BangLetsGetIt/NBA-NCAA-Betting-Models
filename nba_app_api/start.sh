#!/bin/bash
# Quick start script for NBA Analytics API

cd "$(dirname "$0")"

echo "🚀 Starting CourtSide Analytics API..."
echo ""
echo "📖 Interactive docs: http://localhost:8000/docs"
echo "🏀 Pending picks: http://localhost:8000/picks/pending"
echo "📊 Stats only: http://localhost:8000/stats"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn api:app --host 0.0.0.0 --port 8000 --reload
