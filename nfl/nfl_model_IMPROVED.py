#!/usr/bin/env python3
"""
NFL Betting Model - Sharp +EV Version
- Stricter thresholds for profitability (+EV focus)
- Modern dark theme aesthetic matching NBA model
- Only logs high-confidence bets (8+ spread edge, 12+ total edge)
- Sharp, profitable, +EV leaning
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# Try root .env first (if exists), then local .env
root_env = Path(__file__).parent.parent / '.env'
if root_env.exists():
    load_dotenv(dotenv_path=root_env, override=True)
else:
    load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# File paths
SCRIPT_DIR = Path(__file__).parent
PICKS_TRACKING_FILE = SCRIPT_DIR / "nfl_picks_tracking.json"
PICKS_HTML_FILE = SCRIPT_DIR / "nfl_model_output.html"
TRACKING_HTML_FILE = SCRIPT_DIR / "nfl_tracking_dashboard.html"

# ============================================================================
# MODEL PARAMETERS - SHARP +EV THRESHOLDS
# ============================================================================

# Display thresholds (minimum to show in HTML)
SPREAD_THRESHOLD = 3.0      # Minimum edge to display
TOTAL_THRESHOLD = 4.0       # Minimum edge to display

# STRICT thresholds for LOGGING picks (only high-confidence bets tracked)
CONFIDENT_SPREAD_EDGE = 8.0   # Need 8+ point edge to log (sharp +EV focus)
CONFIDENT_TOTAL_EDGE = 12.0   # Need 12+ point edge to log (sharp +EV focus)

# Home field advantage (NFL average ~2.5-3.0 points)
HOME_ADVANTAGE = 2.75

# ============================================================================
# TRACKING SYSTEM
# ============================================================================

class BettingTracker:
    """Track bets and calculate performance metrics"""
    
    def __init__(self, storage_file=None):
        self.storage_file = Path(storage_file) if storage_file else PICKS_TRACKING_FILE
        self.bets = self._load_bets()
    
    def _load_bets(self):
        """Load previous bets from file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_bets(self):
        """Save bets to file"""
        with open(self.storage_file, 'w') as f:
            json.dump(self.bets, f, indent=2)
    
    def add_bet(self, game_id, bet_type, team, line, predicted_value, edge, confidence, recommendation):
        """Add a new bet to tracking (only high-confidence bets)"""
        bet = {
            'game_id': game_id,
            'bet_type': bet_type,
            'team': team,
            'line': line,
            'predicted_value': predicted_value,
            'edge': edge,
            'confidence': confidence,
            'recommendation': recommendation,
            'date_placed': datetime.now().isoformat(),
            'status': 'pending',
            'result': None,
            'profit': 0.0
        }
        self.bets.append(bet)
        self._save_bets()
        return bet
    
    def update_bet_result(self, game_id, bet_type, won, amount=100):
        """Update bet result after game completes"""
        for bet in self.bets:
            if bet['game_id'] == game_id and bet['bet_type'] == bet_type:
                bet['status'] = 'complete'
                bet['result'] = 'won' if won else 'lost'
                bet['profit'] = amount * 0.91 if won else -amount  # -110 odds
                self._save_bets()
                return bet
        return None
    
    def get_statistics(self):
        """Calculate performance statistics"""
        total_bets = len(self.bets)
        completed = [b for b in self.bets if b['status'] == 'complete']
        pending = [b for b in self.bets if b['status'] == 'pending']
        
        won = [b for b in completed if b['result'] == 'won']
        lost = [b for b in completed if b['result'] == 'lost']
        
        win_rate = (len(won) / len(completed) * 100) if completed else 0.0
        total_profit = sum(b['profit'] for b in completed)
        roi = (total_profit / (len(completed) * 100) * 100) if completed else 0.0
        
        return {
            'total_bets': total_bets,
            'completed': len(completed),
            'pending': len(pending),
            'won': len(won),
            'lost': len(lost),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'roi': roi
        }

# ============================================================================
# TEAM RATINGS - MARKET-BASED POWER RATINGS
# ============================================================================

TEAM_RATINGS = {
    # AFC East
    'Buffalo Bills': 72.5,
    'Miami Dolphins': 58.3,
    'New York Jets': 48.7,
    'New England Patriots': 42.3,
    
    # AFC North
    'Baltimore Ravens': 71.2,
    'Pittsburgh Steelers': 64.8,
    'Cincinnati Bengals': 56.9,
    'Cleveland Browns': 45.1,
    
    # AFC South
    'Houston Texans': 66.7,
    'Jacksonville Jaguars': 52.4,
    'Indianapolis Colts': 51.8,
    'Tennessee Titans': 31.0,
    
    # AFC West
    'Kansas City Chiefs': 68.5,
    'Los Angeles Chargers': 64.0,
    'Denver Broncos': 60.2,
    'Las Vegas Raiders': 38.6,
    
    # NFC East
    'Philadelphia Eagles': 69.8,
    'Washington Commanders': 63.5,
    'Dallas Cowboys': 62.1,
    'New York Giants': 41.9,
    
    # NFC North
    'Detroit Lions': 75.3,
    'Minnesota Vikings': 68.9,
    'Green Bay Packers': 64.5,
    'Chicago Bears': 49.2,
    
    # NFC South
    'Atlanta Falcons': 61.7,
    'Tampa Bay Buccaneers': 59.4,
    'New Orleans Saints': 47.8,
    'Carolina Panthers': 36.2,
    
    # NFC West
    'San Francisco 49ers': 67.3,
    'Arizona Cardinals': 59.1,
    'Los Angeles Rams': 55.6,
    'Seattle Seahawks': 54.3,
}

# ============================================================================
# ODDS API INTEGRATION
# ============================================================================

def get_nfl_odds(api_key):
    """Fetch current NFL odds from The Odds API"""
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    
    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': 'spreads,totals',
        'oddsFormat': 'american'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching odds: {e}")
        return []

# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def calculate_spread_prediction(home_team, away_team):
    """
    Calculate predicted point spread
    Positive = home team favored
    Negative = away team favored
    """
    home_rating = TEAM_RATINGS.get(home_team, 50.0)
    away_rating = TEAM_RATINGS.get(away_team, 50.0)
    
    # Calculate raw difference
    raw_diff = home_rating - away_rating
    
    # Add home field advantage
    predicted_spread = raw_diff + HOME_ADVANTAGE
    
    return round(predicted_spread, 1)

def calculate_total_prediction(home_team, away_team):
    """
    Calculate predicted total points
    Uses average of team ratings to determine scoring potential
    """
    home_rating = TEAM_RATINGS.get(home_team, 50.0)
    away_rating = TEAM_RATINGS.get(away_team, 50.0)
    
    # Average rating determines baseline scoring
    avg_rating = (home_rating + away_rating) / 2
    
    # Scale: rating of 50 = 42 points, each 10 points adds/subtracts 5 total points
    baseline = 42.0
    rating_impact = (avg_rating - 50) * 0.5
    
    predicted_total = baseline + rating_impact
    
    return round(predicted_total, 1)

def calculate_predicted_scores(home_team, away_team):
    """Calculate individual team scores"""
    predicted_spread = calculate_spread_prediction(home_team, away_team)
    predicted_total = calculate_total_prediction(home_team, away_team)
    
    # Solve for individual scores
    # home_score - away_score = spread
    # home_score + away_score = total
    home_score = (predicted_total + predicted_spread) / 2
    away_score = (predicted_total - predicted_spread) / 2
    
    return round(home_score, 1), round(away_score, 1)

# ============================================================================
# BETTING ANALYSIS - SHARP +EV FOCUS
# ============================================================================

def analyze_game(game, tracker):
    """Analyze a single game and identify betting opportunities"""
    home_team = game.get('home_team')
    away_team = game.get('away_team')
    commence_time = game.get('commence_time')
    game_id = game.get('id')
    
    if not home_team or not away_team:
        return None
    
    # Get market lines
    bookmakers = game.get('bookmakers', [])
    if not bookmakers:
        return None
    
    # Use first bookmaker (could be enhanced to shop for best line)
    bookmaker = bookmakers[0]
    markets = bookmaker.get('markets', [])
    
    spread_market = next((m for m in markets if m['key'] == 'spreads'), None)
    total_market = next((m for m in markets if m['key'] == 'totals'), None)
    
    if not spread_market or not total_market:
        return None
    
    # Extract lines
    home_spread_outcome = next((o for o in spread_market['outcomes'] if o['name'] == home_team), None)
    total_over = next((o for o in total_market['outcomes'] if o['name'] == 'Over'), None)
    
    if not home_spread_outcome or not total_over:
        return None
    
    market_spread = float(home_spread_outcome['point'])  # Negative if home underdog
    market_total = float(total_over['point'])
    
    # Calculate predictions
    predicted_spread = calculate_spread_prediction(home_team, away_team)
    predicted_total = calculate_total_prediction(home_team, away_team)
    home_score, away_score = calculate_predicted_scores(home_team, away_team)
    
    # Calculate edges
    spread_edge = predicted_spread - market_spread
    total_edge = predicted_total - market_total
    
    # Determine bets (only show those meeting display threshold)
    bets = []
    
    # Spread bet analysis
    if abs(spread_edge) >= SPREAD_THRESHOLD:
        if spread_edge > 0:
            bet_team = home_team
            bet_line = market_spread
            recommendation = f"{home_team} {market_spread:+.1f}"
        else:
            bet_team = away_team
            bet_line = -market_spread
            recommendation = f"{away_team} {-market_spread:+.1f}"
        
        # Confidence based on edge size (capped at 100%)
        confidence = min(abs(spread_edge) / 15.0, 1.0)
        
        # Only LOG high-confidence bets (8+ point edge)
        if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
            tracker.add_bet(
                game_id=game_id,
                bet_type='spread',
                team=bet_team,
                line=bet_line,
                predicted_value=predicted_spread,
                edge=spread_edge,
                confidence=confidence,
                recommendation=recommendation
            )
        
        bets.append({
            'type': 'SPREAD',
            'market_line': f"{home_team} {market_spread:+.1f}",
            'model_prediction': predicted_spread,
            'edge': spread_edge,
            'recommendation': recommendation,
            'confidence': confidence,
            'should_log': abs(spread_edge) >= CONFIDENT_SPREAD_EDGE
        })
    
    # Total bet analysis
    if abs(total_edge) >= TOTAL_THRESHOLD:
        if total_edge > 0:
            recommendation = f"OVER {market_total}"
            bet_team = "Over"
        else:
            recommendation = f"UNDER {market_total}"
            bet_team = "Under"
        
        # Confidence based on edge size (capped at 100%)
        confidence = min(abs(total_edge) / 18.0, 1.0)
        
        # Only LOG high-confidence bets (12+ point edge)
        if abs(total_edge) >= CONFIDENT_TOTAL_EDGE:
            tracker.add_bet(
                game_id=game_id,
                bet_type='total',
                team=bet_team,
                line=market_total,
                predicted_value=predicted_total,
                edge=total_edge,
                confidence=confidence,
                recommendation=recommendation
            )
        
        bets.append({
            'type': 'TOTAL',
            'market_line': market_total,
            'model_prediction': predicted_total,
            'edge': total_edge,
            'recommendation': recommendation,
            'confidence': confidence,
            'should_log': abs(total_edge) >= CONFIDENT_TOTAL_EDGE
        })
    
    return {
        'game_id': game_id,
        'home_team': home_team,
        'away_team': away_team,
        'commence_time': commence_time,
        'home_rating': TEAM_RATINGS.get(home_team, 50.0),
        'away_rating': TEAM_RATINGS.get(away_team, 50.0),
        'predicted_score': f"{home_team} {home_score}, {away_team} {away_score}",
        'predicted_spread': predicted_spread,
        'predicted_total': predicted_total,
        'market_spread': market_spread,
        'market_total': market_total,
        'bets': bets
    }

# ============================================================================
# HTML OUTPUT GENERATION - NBA STYLE AESTHETIC
# ============================================================================

def generate_picks_html(analyses, stats):
    """Generate HTML page with individual game cards - NBA aesthetic"""
    
    # Generate game cards
    game_cards = ""
    for analysis in analyses:
        game_time = datetime.fromisoformat(analysis['commence_time'].replace('Z', '+00:00'))
        game_time_str = game_time.strftime('%m/%d/%y %I:%M %p EDT')
        
        matchup = f"{analysis['away_team']} @ {analysis['home_team']}"
        
        # Generate bet boxes for this game
        bet_boxes = ""
        
        # Find spread and total bets
        spread_bet = None
        total_bet = None
        
        for bet in analysis['bets']:
            if bet['type'] == 'SPREAD':
                spread_bet = bet
            elif bet['type'] == 'TOTAL':
                total_bet = bet
        
        # Spread bet box
        if spread_bet:
            edge = spread_bet['edge']
            # Only show as pick if meets logging threshold (sharp +EV)
            if abs(edge) >= CONFIDENT_SPREAD_EDGE:
                pick_class = "pick-yes"
                pick_icon = "✅"
                explanation = f"SHARP +EV - Model projects {spread_bet['model_prediction']:+.1f}, edge: {edge:+.1f} pts"
            elif abs(edge) >= SPREAD_THRESHOLD:
                pick_class = "pick-none"
                pick_icon = "⚠️"
                explanation = f"Edge: {edge:+.1f} pts - Below sharp threshold ({CONFIDENT_SPREAD_EDGE}+ required)"
            else:
                pick_class = "pick-none"
                pick_icon = "❌"
                explanation = "Insufficient edge"
            
            confidence_pct = int(spread_bet['confidence'] * 100)
            
            bet_boxes += f"""
                        <div class="bet-box bet-box-spread">
                            <div class="bet-title bet-title-spread">📊 SPREAD</div>
                            <div class="odds-line">
                                <span>Vegas Line:</span>
                                <strong>{spread_bet['market_line']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Prediction:</span>
                                <strong>{spread_bet['model_prediction']:+.1f}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{edge:+.1f} pts</strong>
                            </div>
                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Confidence</span>
                                    <span class="confidence-pct">{confidence_pct}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {confidence_pct}%"></div>
                                </div>
                            </div>
                            <div class="pick {pick_class}">
                                {pick_icon} {spread_bet['recommendation'] if abs(edge) >= SPREAD_THRESHOLD else 'NO BET'}<br><small>{explanation}</small>
                            </div>
                        </div>
            """
        else:
            bet_boxes += """
                        <div class="bet-box bet-box-spread">
                            <div class="bet-title bet-title-spread">📊 SPREAD</div>
                            <div class="pick pick-none">
                                ❌ NO BET<br><small>Insufficient edge - pass on this line</small>
                            </div>
                        </div>
            """
        
        # Total bet box
        if total_bet:
            edge = total_bet['edge']
            # Only show as pick if meets logging threshold (sharp +EV)
            if abs(edge) >= CONFIDENT_TOTAL_EDGE:
                pick_class = "pick-yes" if edge > 0 else "pick-yes"
                pick_icon = "✅"
                direction = "OVER" if edge > 0 else "UNDER"
                explanation = f"SHARP +EV - Model projects {total_bet['model_prediction']:.0f} total, {direction} edge: {abs(edge):.1f} pts"
            elif abs(edge) >= TOTAL_THRESHOLD:
                pick_class = "pick-none"
                pick_icon = "⚠️"
                direction = "OVER" if edge > 0 else "UNDER"
                explanation = f"Edge: {abs(edge):.1f} pts - Below sharp threshold ({CONFIDENT_TOTAL_EDGE}+ required)"
            else:
                pick_class = "pick-none"
                pick_icon = "❌"
                explanation = "Insufficient edge"
            
            confidence_pct = int(total_bet['confidence'] * 100)
            
            bet_boxes += f"""
                        <div class="bet-box bet-box-total">
                            <div class="bet-title bet-title-total">🎯 OVER/UNDER</div>
                            <div class="odds-line">
                                <span>Vegas Total:</span>
                                <strong>{total_bet['market_line']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Projects:</span>
                                <strong>{total_bet['model_prediction']:.1f} pts</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{abs(edge):.1f} pts</strong>
                            </div>
                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Confidence</span>
                                    <span class="confidence-pct">{confidence_pct}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {confidence_pct}%"></div>
                                </div>
                            </div>
                            <div class="pick {pick_class}">
                                {pick_icon} {total_bet['recommendation'] if abs(edge) >= TOTAL_THRESHOLD else 'NO BET'}<br><small>{explanation}</small>
                            </div>
                        </div>
            """
        else:
            bet_boxes += """
                        <div class="bet-box bet-box-total">
                            <div class="bet-title bet-title-total">🎯 OVER/UNDER</div>
                            <div class="pick pick-none">
                                ❌ NO BET<br><small>Insufficient edge - pass on this total</small>
                            </div>
                        </div>
            """
        
        # Add game card
        game_cards += f"""
                <div class="game-card">
                    <div class="matchup">{matchup}</div>
                    <div class="game-time">🕐 {game_time_str}</div>
                    
                    <div class="bet-section">
{bet_boxes}
                    </div>
                    
                    <div class="prediction">
                        📈 PREDICTED: {analysis['predicted_score']}
                    </div>
                </div>
        """
    
    if not game_cards:
        game_cards = '<div class="game-card"><div class="matchup">No games available</div></div>'
    
    # NBA-style dark blue aesthetic
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CourtSide Analytics - NFL Picks</title>
        <style>
           * {{ margin: 0; padding: 0; box-sizing: border-box; }}
           body {{
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
                background: #000000;
                color: #ffffff;
                padding: 1.5rem;
                min-height: 100vh;
            }}
           .container {{ max-width: 1200px; margin: 0 auto; }}
           .card {{
                background: #1a1a1a;
                border-radius: 1.25rem;
                border: none;
                padding: 2rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            }}
           .header-card {{
                text-align: center;
                background: #1a1a1a;
                border: none;
            }}
           .game-card {{
                padding: 1.5rem;
                border-bottom: 1px solid #2a3441;
            }}
           .game-card:last-child {{ border-bottom: none; }}
           .matchup {{ font-size: 1.5rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; }}
           .game-time {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 1rem; }}
           .bet-section {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 1rem;
            }}
           .bet-box {{
                background: #262626;
                padding: 1.25rem;
                border-radius: 1rem;
                border-left: none;
            }}
           .bet-box-spread {{
                border-left: 4px solid #60a5fa;
            }}
           .bet-box-total {{
                border-left: 4px solid #f472b6;
            }}
           .bet-title {{
                font-weight: 600;
                color: #94a3b8;
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 0.05em;
            }}
           .bet-title-spread {{
                color: #60a5fa;
            }}
           .bet-title-total {{
                color: #f472b6;
            }}
           .odds-line {{
                display: flex;
                justify-content: space-between;
                margin: 0.25rem 0;
                font-size: 0.9375rem;
                color: #94a3b8;
            }}
           .odds-line strong {{
                color: #ffffff;
                font-weight: 600;
           }}
           .confidence-bar-container {{
                margin: 0.75rem 0;
           }}
           .confidence-label {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.5rem;
                font-size: 0.875rem;
                color: #94a3b8;
           }}
           .confidence-pct {{
                font-weight: 700;
                color: #4ade80;
           }}
           .confidence-bar {{
                height: 6px;
                background: #1a1a1a;
                border-radius: 999px;
                overflow: hidden;
                border: none;
           }}
           .confidence-fill {{
                height: 100%;
                background: #4ade80;
                border-radius: 999px;
                transition: width 0.3s ease;
           }}
           .pick {{
                font-weight: 600;
                padding: 0.875rem 1rem;
                margin-top: 0.75rem;
                border-radius: 0.75rem;
                font-size: 1rem;
                line-height: 1.5;
            }}
           .pick small {{
                display: block;
                font-size: 0.8125rem;
                font-weight: 400;
                margin-top: 0.5rem;
                opacity: 0.85;
                line-height: 1.4;
            }}
           .pick-yes {{ background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 2px solid #4ade80; }}
           .pick-no {{ background: rgba(248, 113, 113, 0.15); color: #f87171; border: 2px solid #f87171; }}
           .pick-none {{ background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 2px solid #475569; }}
           .prediction {{
                background: #262626;
                color: #4ade80;
                padding: 1rem;
                border-radius: 1rem;
                text-align: center;
                font-weight: 700;
                font-size: 1.125rem;
                margin-top: 1rem;
                border: 1px solid #2a3441;
            }}
           .badge {{
                display: inline-block;
                padding: 0.375rem 0.875rem;
                border-radius: 0.5rem;
                font-size: 0.8125rem;
                font-weight: 600;
                background: rgba(74, 222, 128, 0.2);
                color: #4ade80;
                margin: 0.25rem;
            }}
           @media (max-width: 1024px) {{
                .container {{ max-width: 100%; }}
                .card {{ padding: 1.5rem; }}
           }}
           @media (max-width: 768px) {{
                .bet-section {{ grid-template-columns: 1fr; }}
                body {{ padding: 1rem; }}
                .matchup {{ font-size: 1.25rem; }}
           }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card header-card">
                <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem;">🏈 NFL MODEL PICKS</h1>
                <p style="font-size: 1.25rem; opacity: 0.9; margin-bottom: 1rem;">Sharp +EV Focus • High Confidence Only</p>
                <div>
                    <div class="badge">● SHARP THRESHOLDS (8+ Spread / 12+ Total)</div>
                    <div class="badge">● +EV FOCUSED</div>
                    <div class="badge">● PROFITABILITY FIRST</div>
                </div>
                <p style="font-size: 0.875rem; opacity: 0.75; margin-top: 1rem;">Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</p>
            </div>
            
            <div class="card">
{game_cards}
            </div>
        </div>
    </body>
    </html>"""
    
    return html

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    # Get API key from environment variable
    API_KEY = os.getenv("ODDS_API_KEY")
    if not API_KEY:
        print("❌ ERROR: ODDS_API_KEY not found in environment variables")
        print("Please create a .env file with: ODDS_API_KEY=your_key_here")
        return
    
    print("🏈 NFL Betting Model - Sharp +EV Version")
    print("=" * 60)
    print(f"Spread Threshold: {SPREAD_THRESHOLD}+ pts (display)")
    print(f"Spread Logging: {CONFIDENT_SPREAD_EDGE}+ pts (sharp +EV)")
    print(f"Total Threshold: {TOTAL_THRESHOLD}+ pts (display)")
    print(f"Total Logging: {CONFIDENT_TOTAL_EDGE}+ pts (sharp +EV)")
    print("=" * 60)
    
    # Initialize tracker
    tracker = BettingTracker()
    
    # Fetch current odds
    print("\n📡 Fetching current NFL odds...")
    games = get_nfl_odds(API_KEY)
    
    if not games:
        print("❌ No games found or API error")
        return
    
    print(f"✅ Found {len(games)} games")
    
    # Analyze each game
    print("\n🔍 Analyzing games...\n")
    analyses = []
    logged_count = 0
    
    for game in games:
        analysis = analyze_game(game, tracker)
        if analysis:
            analyses.append(analysis)
            
            # Count logged bets
            for bet in analysis['bets']:
                if bet.get('should_log', False):
                    logged_count += 1
            
            # Print analysis
            print(f"{analysis['away_team']} @ {analysis['home_team']}")
            print(f"  🕐 {analysis['commence_time']}")
            print(f"  📊 Ratings: {analysis['home_team']} ({analysis['home_rating']}) vs {analysis['away_team']} ({analysis['away_rating']})")
            print(f"  📈 Predicted: {analysis['predicted_score']}")
            
            if analysis['bets']:
                for bet in analysis['bets']:
                    log_marker = "⭐ LOGGED" if bet.get('should_log', False) else "👁️ Display Only"
                    print(f"  {bet['type']} ({log_marker}):")
                    print(f"    Market: {bet['market_line']}")
                    print(f"    Model:  {bet['model_prediction']:.1f}")
                    print(f"    Edge:   {bet['edge']:+.1f}")
                    if bet.get('should_log', False):
                        print(f"    ✅ SHARP BET: {bet['recommendation']}")
                    elif abs(bet['edge']) >= (SPREAD_THRESHOLD if bet['type'] == 'SPREAD' else TOTAL_THRESHOLD):
                        print(f"    ⚠️  Below logging threshold: {bet['recommendation']}")
            else:
                print(f"  ⚠️  No bets (insufficient edge)")
            
            print()
    
    # Generate HTML output
    print("📄 Generating HTML reports...")
    
    stats = tracker.get_statistics()
    
    picks_html = generate_picks_html(analyses, stats)
    with open(PICKS_HTML_FILE, 'w') as f:
        f.write(picks_html)
    print(f"✅ Created: {PICKS_HTML_FILE}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Games Analyzed: {len(analyses)}")
    print(f"Bets Logged:    {logged_count} (high-confidence +EV only)")
    print(f"Total Tracked:  {stats['total_bets']}")
    print(f"Completed:      {stats['completed']}")
    print(f"Pending:        {stats['pending']}")
    if stats['completed'] > 0:
        print(f"Win Rate:       {stats['win_rate']:.1f}%")
        print(f"ROI:            {stats['roi']:+.1f}%")
        print(f"Total Profit:   ${stats['total_profit']:+.2f}")
    print("=" * 60)

if __name__ == "__main__":
    main()

