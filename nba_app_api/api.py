#!/usr/bin/env python3
"""
NBA Model API - Phase 1: Backend Bridge
This API reads your existing NBA model's output files and serves them as JSON.
NO CHANGES to your existing model - this is a completely separate app.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import os

app = FastAPI(
    title="CourtSide Analytics API",
    description="Premium NBA Model Predictions API",
    version="1.0.0"
)

# Enable CORS for your iOS app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to your existing model's output files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Try local deployment structure first, fall back to production structure
PICKS_TRACKING_FILE = os.path.join(BASE_DIR, 'nba_picks_tracking.json')
if not os.path.exists(PICKS_TRACKING_FILE):
    # For local development with parent directory structure
    PICKS_TRACKING_FILE = os.path.join(os.path.dirname(BASE_DIR), 'nba', 'nba_picks_tracking.json')

# =====================
# DATA MODELS (Pydantic schemas for API responses)
# =====================

class GamePrediction(BaseModel):
    """Individual game prediction/pick"""
    home_team: str
    away_team: str
    matchup: str
    game_date: str
    pick_type: str  # "Spread" or "Total"
    pick_description: str  # e.g., "Lakers -4.5" or "OVER 220.5"
    market_line: float
    model_line: Optional[float] = None
    edge: float
    odds: int = -110
    confidence: Optional[str] = None  # "High", "Medium", "Low"
    status: str  # "pending", "win", "loss", "push"
    result: Optional[str] = None
    profit_loss: Optional[float] = None

class PerformanceStats(BaseModel):
    """Overall model performance statistics"""
    win_rate: float
    total_picks: int
    wins: int
    losses: int
    pushes: int
    total_profit: float  # In units
    roi: float
    spread_record: str  # e.g., "49-30-2"
    total_record: str   # e.g., "46-32-1"
    last_updated: str

class APIResponse(BaseModel):
    """Main API response structure"""
    metadata: PerformanceStats
    games: List[GamePrediction]

# =====================
# HELPER FUNCTIONS
# =====================

def load_tracking_data():
    """Load data from your existing NBA model's tracking file"""
    if not os.path.exists(PICKS_TRACKING_FILE):
        raise HTTPException(status_code=404, detail="Model data not found. Run your NBA model first.")

    try:
        with open(PICKS_TRACKING_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model data: {str(e)}")

def calculate_confidence(edge: float, pick_type: str) -> str:
    """Calculate confidence level based on edge"""
    abs_edge = abs(edge)

    if pick_type == "Spread":
        if abs_edge >= 8:
            return "High"
        elif abs_edge >= 5:
            return "Medium"
        else:
            return "Low"
    else:  # Total
        if abs_edge >= 12:
            return "High"
        elif abs_edge >= 7:
            return "Medium"
        else:
            return "Low"

def transform_pick_to_game_prediction(pick: dict) -> GamePrediction:
    """Transform your model's pick format to API format"""
    # Determine confidence based on edge
    confidence = calculate_confidence(pick.get('edge', 0), pick.get('pick_type', 'Spread'))

    # Extract pick description (remove emojis)
    pick_desc = pick.get('pick', pick.get('pick_text', ''))
    pick_desc = pick_desc.replace('✅', '').replace('BET:', '').strip()

    return GamePrediction(
        home_team=pick.get('home_team', ''),
        away_team=pick.get('away_team', ''),
        matchup=pick.get('matchup', ''),
        game_date=pick.get('game_date', ''),
        pick_type=pick.get('pick_type', 'Unknown'),
        pick_description=pick_desc,
        market_line=pick.get('market_line', 0),
        model_line=pick.get('model_line'),
        edge=pick.get('edge', 0),
        odds=pick.get('odds', -110),
        confidence=confidence,
        status=pick.get('status', 'pending'),
        result=pick.get('result'),
        profit_loss=pick.get('profit_loss', 0) / 100 if pick.get('profit_loss') else None  # Convert cents to units
    )

def calculate_performance_stats(picks: list) -> PerformanceStats:
    """Calculate overall performance statistics"""
    completed = [p for p in picks if p['status'] in ['win', 'loss', 'push']]
    wins = [p for p in picks if p['status'] == 'win']
    losses = [p for p in picks if p['status'] == 'loss']
    pushes = [p for p in picks if p['status'] == 'push']

    # Calculate win rate (excluding pushes)
    decisive_picks = [p for p in completed if p['status'] != 'push']
    win_rate = (len(wins) / len(decisive_picks) * 100) if decisive_picks else 0

    # Calculate profit
    total_profit = sum(p.get('profit_loss', 0) for p in picks) / 100  # Convert cents to units

    # Calculate ROI
    total_risk = len(completed) * 100  # Assuming 1 unit per bet
    roi = (total_profit / (total_risk / 100) * 100) if total_risk > 0 else 0

    # Spread/Total breakdowns
    spread_picks = [p for p in picks if p.get('pick_type') == 'Spread']
    spread_wins = len([p for p in spread_picks if p['status'] == 'win'])
    spread_losses = len([p for p in spread_picks if p['status'] == 'loss'])
    spread_pushes = len([p for p in spread_picks if p['status'] == 'push'])

    total_picks = [p for p in picks if p.get('pick_type') == 'Total']
    total_wins = len([p for p in total_picks if p['status'] == 'win'])
    total_losses = len([p for p in total_picks if p['status'] == 'loss'])
    total_pushes = len([p for p in total_picks if p['status'] == 'push'])

    return PerformanceStats(
        win_rate=round(win_rate, 1),
        total_picks=len(picks),
        wins=len(wins),
        losses=len(losses),
        pushes=len(pushes),
        total_profit=round(total_profit, 2),
        roi=round(roi, 1),
        spread_record=f"{spread_wins}-{spread_losses}-{spread_pushes}",
        total_record=f"{total_wins}-{total_losses}-{total_pushes}",
        last_updated=datetime.now().strftime('%Y-%m-%d %I:%M %p ET')
    )

# =====================
# API ENDPOINTS
# =====================

@app.get("/", tags=["Info"])
async def root():
    """API info and health check"""
    return {
        "name": "CourtSide Analytics API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "/picks": "Get all model picks with performance stats",
            "/picks/pending": "Get only pending (upcoming) picks",
            "/picks/completed": "Get only completed picks with results",
            "/stats": "Get performance statistics only"
        }
    }

@app.get("/picks", response_model=APIResponse, tags=["Picks"])
async def get_all_picks():
    """
    Get all NBA model picks with performance statistics.
    This endpoint returns both pending and completed picks.
    """
    data = load_tracking_data()
    picks = data.get('picks', [])

    # Transform picks to API format
    game_predictions = [transform_pick_to_game_prediction(p) for p in picks]

    # Calculate stats
    stats = calculate_performance_stats(picks)

    return APIResponse(
        metadata=stats,
        games=game_predictions
    )

@app.get("/picks/pending", response_model=APIResponse, tags=["Picks"])
async def get_pending_picks():
    """
    Get only pending (upcoming) NBA picks.
    Perfect for showing users what to bet on today.
    """
    data = load_tracking_data()
    picks = data.get('picks', [])

    # Filter for pending picks only
    pending_picks = [p for p in picks if p.get('status') == 'pending']

    # Transform to API format
    game_predictions = [transform_pick_to_game_prediction(p) for p in pending_picks]

    # Calculate stats from ALL picks (not just pending)
    stats = calculate_performance_stats(picks)

    return APIResponse(
        metadata=stats,
        games=game_predictions
    )

@app.get("/picks/completed", response_model=APIResponse, tags=["Picks"])
async def get_completed_picks():
    """
    Get only completed picks with results.
    Use this for showing historical performance.
    """
    data = load_tracking_data()
    picks = data.get('picks', [])

    # Filter for completed picks
    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss', 'push']]

    # Transform to API format
    game_predictions = [transform_pick_to_game_prediction(p) for p in completed_picks]

    # Calculate stats
    stats = calculate_performance_stats(picks)

    return APIResponse(
        metadata=stats,
        games=game_predictions
    )

@app.get("/stats", response_model=PerformanceStats, tags=["Stats"])
async def get_stats_only():
    """
    Get performance statistics only (no game data).
    Lightweight endpoint for dashboard widgets.
    """
    data = load_tracking_data()
    picks = data.get('picks', [])

    return calculate_performance_stats(picks)

# =====================
# RUN SERVER
# =====================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CourtSide Analytics API...")
    print("📖 Docs available at: http://localhost:8000/docs")
    print("🏀 NBA Picks endpoint: http://localhost:8000/picks")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
