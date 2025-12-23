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
import pytz

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
SPREAD_THRESHOLD = 0.1      # Minimum edge to display
TOTAL_THRESHOLD = 0.1       # Minimum edge to display

# STRICT thresholds for LOGGING picks (only high-confidence bets tracked)
CONFIDENT_SPREAD_EDGE = 8.0   # Need 8+ point edge to log (sharp +EV focus)
CONFIDENT_TOTAL_EDGE = 12.0   # Need 12+ point edge to log (sharp +EV focus)

# Home field advantage (NFL average ~2.5-3.0 points)
HOME_ADVANTAGE = 2.75

# ============================================================================
# TRACKING SYSTEM
# ============================================================================

def calculate_clv_status(opening_line, closing_line, pick_type, pick_text):
    """
    Calculate if a pick beat the closing line (positive CLV).
    
    Args:
        opening_line: The line when the pick was first logged
        closing_line: The line at game time (or latest available)
        pick_type: 'Spread' or 'Total'
        pick_text: The pick text (e.g., "New York Knicks -2.5" or "OVER 234.5")
    
    Returns:
        "positive" if beat closing line, "negative" if worse, "neutral" if same
    """
    try:
        # If lines are the same, no CLV advantage
        if abs(opening_line - closing_line) < 0.1:
            return "neutral"
        
        if pick_type.lower() == 'spread':
            # For spreads, determine if we're betting favorite or underdog
            # Extract the spread value from pick text if possible, otherwise rely on opening_line sign
            # This logic assumes "Team -Spread" format or similar
            
            # Simple heuristic: 
            # If betting a negative spread (favorite), we want the line to move closer to 0 or positive (e.g. -3.5 -> -2.5 is good).
            # Actually, standard betting:
            # Bet -3.5. Closing -4.5. You got -3.5, which is BETTER than -4.5. (You cover easier).
            # Wait. If I bet -3.5, and it closes -4.5. 
            # If score is Team A 24, Team B 20. Win by 4.
            # -3.5 wins. -4.5 loses.
            # So -3.5 is BETTER than -4.5.
            # So for favorites (negative), a higher (more positive/less negative) number is better? 
            # -3.5 > -4.5. Yes.
            
            # If bet +3.5 (underdog). Closing +2.5.
            # Score A 20, B 24. Lose by 4.
            # +3.5 covers (23.5). +2.5 loses (22.5).
            # So +3.5 is BETTER than +2.5.
            # So for underdogs (positive), a higher number is better.
            
            # So generally for spreads: Higher algebraic value is ALWAYS better for the bettor.
            # -2.5 > -3.5
            # +3.5 > +2.5
            
            if opening_line > closing_line:
                return "positive"
            else:
                return "negative"
        
        elif pick_type.lower() == 'total':
            # For totals, need to know if OVER or UNDER
            pick_upper = pick_text.upper()
            
            if 'OVER' in pick_upper:
                # Betting OVER: Lower total is better (e.g., OVER 40.5 beats OVER 41.5)
                if opening_line < closing_line:
                    return "positive"
                else:
                    return "negative"
            elif 'UNDER' in pick_upper:
                # Betting UNDER: Higher total is better (e.g., UNDER 41.5 beats UNDER 40.5)
                if opening_line > closing_line:
                    return "positive"
                else:
                    return "negative"
            else:
                return "neutral"
        
        return "neutral"
    
    except Exception as e:
        print(f"Error calculating CLV: {e}")
        return "neutral"

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
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data.get('picks', [])
                    return data
            except:
                return []
        return []
    
    def _save_bets(self):
        """Save bets to file in normalized dict format"""
        with open(self.storage_file, 'w') as f:
            json.dump({'picks': self.bets}, f, indent=2)
    
    def add_bet(self, game_id, bet_type, team, line, predicted_value, edge, confidence, recommendation, game_time=None):
        """Add a new bet to tracking (only high-confidence bets)"""
        # Check for duplicates
        for b in self.bets:
            # Match on ID, type, and team.
            if (b.get('game_id') == game_id and 
                b.get('bet_type') == bet_type and 
                b.get('team') == team):
                
                # Check for CLV update
                current_closing = b.get('closing_line', b.get('line'))
                if abs(float(current_closing) - float(line)) >= 0.1:
                    b['closing_line'] = line
                    # Calculate CLV
                    b['clv_status'] = calculate_clv_status(
                        b.get('opening_line', b.get('line')),
                        line,
                        bet_type,
                        recommendation
                    )
                    self._save_bets()
                    
                return b

        bet = {
            'game_id': game_id,
            'bet_type': bet_type,
            'team': team,
            'line': line,
            'opening_line': line,      # Track opening line
            'closing_line': line,      # Initialize closing line
            'clv_status': None,        # Initialize CLV status
            'predicted_value': predicted_value,
            'edge': edge,
            'confidence': confidence,
            'recommendation': recommendation,
            'game_time': game_time,
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
    
    def get_bet(self, game_id, bet_type, team):
        """Retrieve an existing bet"""
        for bet in self.bets:
            if (bet.get('game_id') == game_id and 
                bet.get('bet_type') == bet_type and 
                bet.get('team') == team):
                return bet
        return None

    def update_closing_line(self, game_id, bet_type, team, current_line, recommendation):
        """Update closing line and CLV status for an existing bet"""
        bet = self.get_bet(game_id, bet_type, team)
        if bet:
            current_closing = bet.get('closing_line', bet.get('line'))
            if abs(float(current_closing) - float(current_line)) >= 0.1 or bet.get('clv_status') is None:
                bet['closing_line'] = current_line
                bet['clv_status'] = calculate_clv_status(
                    bet.get('opening_line', bet.get('line')),
                    current_line,
                    bet_type,
                    recommendation
                )
                self._save_bets()
            return bet
        return None

    def get_statistics(self):
        """Calculate performance statistics"""
        total_bets = len(self.bets)
        # Count completed picks - support both old 'complete' status and new 'win'/'loss' status
        completed = [b for b in self.bets if b.get('status') in ['complete', 'win', 'loss', 'push']]
        pending = [b for b in self.bets if b.get('status') == 'pending']
        
        # Count wins - support both formats
        won = [b for b in self.bets if b.get('status') == 'win' or 
               (b.get('status') == 'complete' and b.get('result') in ['won', 'win'])]
        lost = [b for b in self.bets if b.get('status') == 'loss' or
                (b.get('status') == 'complete' and b.get('result') in ['lost', 'loss'])]
        
        win_rate = (len(won) / len(completed) * 100) if completed else 0.0
        total_profit = sum(b.get('profit', 0) or 0 for b in completed)
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
# AUTO-GRADING FUNCTIONS (Dec 20, 2024)
# ============================================================================

def fetch_completed_nfl_scores():
    """Fetch completed NFL game scores from The Odds API"""
    print("\n🏈 Fetching completed NFL scores...")
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        print("⚠️ ODDS_API_KEY not set")
        return []
    
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/scores/"
    params = {
        'apiKey': api_key,
        'daysFrom': 3  # Check last 3 days
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        all_games = response.json()
        
        # Filter to only completed games
        completed = [g for g in all_games if g.get('completed', False)]
        print(f"   Found {len(completed)} completed games")
        return completed
    except Exception as e:
        print(f"⚠️ Error fetching scores: {e}")
        return []

def grade_pending_picks():
    """Grade pending picks using completed game scores"""
    # Load tracking data (list format)
    if not PICKS_TRACKING_FILE.exists():
        return
    
    with open(PICKS_TRACKING_FILE, 'r') as f:
        data = json.load(f)
        if isinstance(data, dict):
            picks = data.get('picks', [])
        else:
            picks = data
    
    if not picks:
        return
    
    pending = [p for p in picks if p.get('status') == 'pending']
    if not pending:
        print("   No pending picks to grade")
        return
    
    print(f"   Checking {len(pending)} pending picks...")
    
    # Fetch completed scores
    completed_games = fetch_completed_nfl_scores()
    if not completed_games:
        return
    
    # Build lookup by teams
    game_scores = {}
    for game in completed_games:
        home = game.get('home_team', '')
        away = game.get('away_team', '')
        scores = game.get('scores', [])
        if scores and len(scores) >= 2:
            home_score = next((s['score'] for s in scores if s['name'] == home), None)
            away_score = next((s['score'] for s in scores if s['name'] == away), None)
            if home_score is not None and away_score is not None:
                game_scores[(home, away)] = (int(home_score), int(away_score))
    
    updated = 0
    for pick in pending:
        # Find matching game
        game_id = pick.get('game_id', '')
        bet_type = pick.get('bet_type', '')
        team = pick.get('team', '')
        line = pick.get('line', 0)
        
        # Try to match by checking all completed games
        for (home, away), (home_score, away_score) in game_scores.items():
            # Check if this pick matches this game
            if team in [home, away, 'Over', 'Under']:
                # Grade spread bets
                if bet_type == 'spread':
                    actual_spread = home_score - away_score  # Positive = home won
                    covered = False
                    
                    if team == home:
                        # Home team with spread (line is usually negative if favored)
                        covered = (actual_spread + line) > 0
                    elif team == away:
                        # Away team with spread
                        covered = (away_score - home_score + line) > 0
                    
                    pick['status'] = 'win' if covered else 'loss'
                    pick['result'] = 'win' if covered else 'loss'
                    pick['profit'] = 91 if covered else -100
                    pick['actual_home_score'] = home_score
                    pick['actual_away_score'] = away_score
                    updated += 1
                    status = "✅ WIN" if covered else "❌ LOSS"
                    print(f"   {status}: {pick.get('recommendation', team)}")
                    break
                
                # Grade total bets
                elif bet_type == 'total':
                    actual_total = home_score + away_score
                    hit = False
                    
                    if team == 'Over':
                        hit = actual_total > line
                    elif team == 'Under':
                        hit = actual_total < line
                    
                    pick['status'] = 'win' if hit else 'loss'
                    pick['result'] = 'win' if hit else 'loss'
                    pick['profit'] = 91 if hit else -100
                    pick['actual_home_score'] = home_score
                    pick['actual_away_score'] = away_score
                    updated += 1
                    status = "✅ WIN" if hit else "❌ LOSS"
                    print(f"   {status}: {pick.get('recommendation', team)}")
                    break
    
    # Save updated picks
    if updated > 0:
        with open(PICKS_TRACKING_FILE, 'w') as f:
            json.dump(picks, f, indent=2)
        print(f"\n   ✅ Graded {updated} picks!")
    else:
        print("   No picks matched completed games")

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
        'regions': 'us,us2',
        'markets': 'spreads,totals',
        'oddsFormat': 'american'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        all_games = response.json()
        
        # Filter games by date (exclude completed/started)
        filtered_games = []
        current_time_utc = datetime.now(pytz.utc)

        for game in all_games:
            try:
                commence_time_str = game.get('commence_time', '')
                commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                if commence_time > current_time_utc:
                    filtered_games.append(game)
            except:
                continue
                
        print(f"Fetched {len(all_games)} games, filtered to {len(filtered_games)} upcoming.")
        return filtered_games
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
    
    # Prioritize Hard Rock Bet, then FanDuel, then first available
    bookmaker = next((b for b in bookmakers if b['key'] == 'hardrockbet'),
                next((b for b in bookmakers if b['key'] == 'fanduel'), 
                     bookmakers[0]))
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
        
        # Check if this is a tracked bet to get CLV status
        tracked_bet = tracker.update_closing_line(game_id, 'spread', bet_team, bet_line, recommendation)
        clv_status = tracked_bet.get('clv_status') if tracked_bet else None

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
                recommendation=recommendation,
                game_time=commence_time
            )
        
        bets.append({
            'type': 'SPREAD',
            'market_line': f"{home_team} {market_spread:+.1f}",
            'model_prediction': predicted_spread,
            'edge': spread_edge,
            'recommendation': recommendation,
            'confidence': confidence,
            'should_log': abs(spread_edge) >= CONFIDENT_SPREAD_EDGE,
            'clv_status': clv_status
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
        
        # Check if this is a tracked bet to get CLV status
        tracked_bet = tracker.update_closing_line(game_id, 'total', bet_team, market_total, recommendation)
        clv_status = tracked_bet.get('clv_status') if tracked_bet else None

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
                recommendation=recommendation,
                game_time=commence_time
            )
        
        bets.append({
            'type': 'TOTAL',
            'market_line': market_total,
            'model_prediction': predicted_total,
            'edge': total_edge,
            'recommendation': recommendation,
            'confidence': confidence,
            'should_log': abs(total_edge) >= CONFIDENT_TOTAL_EDGE,
            'clv_status': clv_status
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

# Result mapping
def get_daily_stats(picks):
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    today_str = now.strftime('%Y-%m-%d')
    yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    stats = {
        'today': {'w': 0, 'l': 0, 'p': 0},
        'yesterday': {'w': 0, 'l': 0, 'p': 0}
    }
    
    for p in picks:
        status = p.get('status', '').lower()
        if status not in ['win', 'loss', 'push', 'complete']: continue
        
        # Result mapping
        res = 'p'
        if status == 'win' or (status == 'complete' and p.get('result') == 'won'): res = 'w'
        elif status == 'loss' or (status == 'complete' and p.get('result') == 'lost'): res = 'l'
        
        # Date check - use game_date if available (YYYY-MM-DD), otherwise parse game_time
        g_date = p.get('game_date')
        if not g_date and p.get('date_placed'):
            g_date = p.get('date_placed')[:10]
        
        if g_date == today_str:
            stats['today'][res] += 1
        elif g_date == yesterday_str:
            stats['yesterday'][res] += 1
            
    return stats

def generate_picks_html(analyses, stats, tracker):
    """Generate HTML page with PROPS_HTML_STYLING_GUIDE aesthetic - REVISED COPY"""
    from jinja2 import Template
    
    # Map for NFL logos (approximate ESPN codes)
    team_abbr_map = {
        'Arizona Cardinals': 'ari', 'Atlanta Falcons': 'atl', 'Baltimore Ravens': 'bal',
        'Buffalo Bills': 'buf', 'Carolina Panthers': 'car', 'Chicago Bears': 'chi',
        'Cincinnati Bengals': 'cin', 'Cleveland Browns': 'cle', 'Dallas Cowboys': 'dal',
        'Denver Broncos': 'den', 'Detroit Lions': 'det', 'Green Bay Packers': 'gb',
        'Houston Texans': 'hou', 'Indianapolis Colts': 'ind', 'Jacksonville Jaguars': 'jax',
        'Kansas City Chiefs': 'kc', 'Las Vegas Raiders': 'lv', 'Los Angeles Chargers': 'lac',
        'Los Angeles Rams': 'lar', 'Miami Dolphins': 'mia', 'Minnesota Vikings': 'min',
        'New England Patriots': 'ne', 'New Orleans Saints': 'no', 'New York Giants': 'nyg',
        'New York Jets': 'nyj', 'Philadelphia Eagles': 'phi', 'Pittsburgh Steelers': 'pit',
        'San Francisco 49ers': 'sf', 'Seattle Seahawks': 'sea', 'Tampa Bay Buccaneers': 'tb',
        'Tennessee Titans': 'ten', 'Washington Commanders': 'wsh'
    }

    timestamp_str = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    
    # Prepare tracking data
    tracking_data = load_picks_tracking()
    all_picks = tracking_data.get('picks', [])
    
    # Calculate Last N stats
    last_10 = calculate_recent_performance(all_picks, 10)
    last_20 = calculate_recent_performance(all_picks, 20)
    last_50 = calculate_recent_performance(all_picks, 50)
    
    # Sort for display lists (optional if used elsewhere)
    all_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    completed_picks = [p for p in all_picks if p.get('status') in ['win', 'loss', 'push']]
    pending_picks = [p for p in all_picks if p.get('status') == 'pending']
    
    # Sort
    pending_picks.sort(key=lambda x: x.get('date_placed', ''), reverse=True)
    completed_picks.sort(key=lambda x: x.get('date_placed', ''), reverse=True)
    
    daily_perf = get_daily_stats(all_picks)

    # CSS/HTML Template matches the new revised aesthetic
    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Model Picks • CourtSide Analytics</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1c1c1e;
            --bg-metric: #2c2c2e;
            --text-primary: #ffffff;
            --text-secondary: #8e8e93;
            --accent-green: #34c759;
            --accent-red: #ff3b30;
            --border-color: #333333;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 2rem;
        }

        .container {
            max-width: 850px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        header h1 {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .date-sub {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }

        /* Header Section */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .team-logo {
            width: 44px;
            height: 44px;
            object-fit: contain;
        }

        .matchup-info h2 {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .matchup-sub {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .game-time-badge {
            background-color: var(--bg-metric);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        /* Bet Section */
        .bet-row {
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .bet-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }

        .main-pick {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }
        
        .main-pick.green { color: var(--accent-green); }
        .main-pick.red { color: var(--accent-red); }

        .model-context {
            color: var(--text-secondary);
            font-size: 0.95rem;
            font-weight: 500;
        }

        .edge-val {
            color: var(--accent-green);
            font-weight: 600;
            margin-left: 6px;
        }

        /* Metrics Row */
        .metrics-row {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .metric-box {
            background-color: var(--bg-metric);
            border-radius: 8px;
            padding: 0.8rem 1.5rem;
            text-align: center;
            flex: 1;
        }

        .metric-title {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }

        .metric-value {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--text-primary);
        }
        
        .metric-value.good { color: var(--accent-green); }

        /* Tags */
        .tags-row {
            display: flex;
            gap: 0.75rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }

        .tag {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .tag-red { background: rgba(255, 59, 48, 0.15); color: #ff453a; }
        .tag-blue { background: rgba(10, 132, 255, 0.15); color: #5ac8fa; }
        .tag-green { background: rgba(48, 209, 88, 0.15); color: #32d74b; }

        /* Table Styles for Tracking */
        .tracking-section { margin-top: 3rem; }
        .tracking-header { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        thead { background: var(--bg-metric); }
        th { padding: 0.75rem 1rem; text-align: left; color: var(--text-secondary); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
        td { padding: 1rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary); font-size: 0.9rem; }
        tr:hover { background: rgba(255,255,255,0.03); }
        
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .badge-pending { background: rgba(255, 149, 0, 0.15); color: #ff9f0a; }
        .badge-won { background: rgba(50, 215, 75, 0.15); color: #32d74b; }
        .badge-lost { background: rgba(255, 69, 58, 0.15); color: #ff453a; }
        .badge-push { background: rgba(142, 142, 147, 0.15); color: #8e8e93; }

        .text-green { color: var(--accent-green); }
        .text-red { color: var(--accent-red); }
        .text-gray { color: var(--text-secondary); }
        .font-bold { font-weight: 700; }

        @media (max-width: 600px) {
            body { padding: 1rem; }
            .metrics-row { gap: 0.5rem; }
            .metric-box { padding: 0.8rem 0.5rem; }
            .main-pick { font-size: 1.5rem; }
            table { display: block; overflow-x: auto; white-space: nowrap; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🏈 NFL SHARP MODEL</h1>
                <div class="date-sub">Generated: {{ timestamp }}</div>
            </div>
            <div style="text-align: right;">
                <div class="metric-title">DAILY PERFORMANCE</div>
                <div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;">
                    <span style="color: var(--text-secondary);">TODAY:</span> 
                    <span style="color: {{ 'var(--accent-green)' if daily_perf.today.w > daily_perf.today.l else 'var(--text-primary)' }}">
                        {{ daily_perf.today.w }}-{{ daily_perf.today.l }}
                    </span>
                    <span style="margin-left: 10px; color: var(--text-secondary);">YESTERDAY:</span>
                    <span style="color: {{ 'var(--accent-green)' if daily_perf.yesterday.w > daily_perf.yesterday.l else ('var(--accent-red)' if daily_perf.yesterday.l > daily_perf.yesterday.w else 'var(--text-primary)') }}">
                        {{ daily_perf.yesterday.w }}-{{ daily_perf.yesterday.l }}
                    </span>
                </div>
                <div class="metric-title" style="margin-top: 8px;">SEASON RECORD</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                    {{ stats.won }}-{{ stats.lost }} ({{ "%.1f"|format(stats.win_rate) }}%)
                </div>
            </div>
        </header>

        {% for game in analyses %}
        {% set team_key = game.home_team %}
        {% set team_abbr = team_abbr_map.get(team_key, 'nfl')|lower %}
        
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <img src="https://a.espncdn.com/i/teamlogos/nfl/500/{{ team_abbr }}.png" 
                         alt="{{ game.home_team }}" 
                         class="team-logo"
                         onerror="this.src='https://a.espncdn.com/i/teamlogos/nfl/500/est.png'">
                    <div class="matchup-info">
                        <h2>{{ game.away_team }} @ {{ game.home_team }}</h2>
                        <div class="matchup-sub">{{ game.home_team }} Home Game</div>
                    </div>
                </div>
                <div class="game-time-badge">{{ game.commence_time[:16].replace('T', ' ') }}</div>
            </div>

            <div class="card-body">
                {% set ns = namespace(spread_bet=None, total_bet=None) %}
                {% for bet in game.bets %}
                    {% if bet.type == 'SPREAD' %}{% set ns.spread_bet = bet %}{% endif %}
                    {% if bet.type == 'TOTAL' %}{% set ns.total_bet = bet %}{% endif %}
                {% endfor %}
                {% set spread_bet = ns.spread_bet %}
                {% set total_bet = ns.total_bet %}

                <!-- SPREAD BET BLOCK -->
                <div class="bet-row">
                    {% if spread_bet %}
                    <div class="main-pick {{ 'green' if spread_bet.edge|abs >= 3.0 else '' }}">{{ spread_bet.recommendation.replace('✅ BET: ', '') }}</div>
                    {% else %}
                    <div class="main-pick">{{ game.market_spread if game.market_spread else '--' }}</div>
                    {% endif %}
                    
                    <div class="model-context">
                        Model: {% if spread_bet %}{{ "%.1f"|format(spread_bet.model_prediction) }}{% else %}--{% endif %}
                        <span class="edge-val" style="color: {{ 'var(--accent-green)' if spread_bet and spread_bet.edge|abs >= 3.0 else 'var(--text-secondary)' }};">Edge: {% if spread_bet %}{{ "%+.1f"|format(spread_bet.edge) }}{% else %}--{% endif %}</span>
                    </div>
                    {% if spread_bet and (spread_bet.should_log or spread_bet.clv_status) %}
                    <div class="tags-row" style="margin-top: 8px; justify-content: flex-start;">
                         {% if spread_bet.clv_status == 'positive' %}
                            <span class="tag tag-green">✅ CLV: Beat Line</span>
                         {% elif spread_bet.clv_status == 'negative' %}
                            <span class="tag tag-red">⚠️ CLV: Missed Line</span>
                         {% elif spread_bet.clv_status == 'neutral' %}
                            <span class="tag tag-blue">➖ CLV: Neutral</span>
                         {% elif spread_bet.clv_status is none %}
                            <span class="tag tag-blue">⏳ CLV: Tracking</span>
                         {% endif %}
                    </div>
                    {% endif %}
                </div>

                <!-- TOTAL BET BLOCK -->
                <div class="bet-row" style="border-bottom: none;">
                    {% if total_bet %}
                        <div class="main-pick {{ 'green' if total_bet.edge|abs >= 4.0 else '' }}">{{ total_bet.recommendation.replace('✅ BET: ', '') }}</div>
                    {% else %}
                        <div class="main-pick">O/U {{ game.market_total if game.market_total else '--' }}</div>
                    {% endif %}
                    
                    <div class="model-context">
                        Model: {% if total_bet %}{{ "%.1f"|format(total_bet.model_prediction) }}{% else %}--{% endif %}
                        <span class="edge-val" style="color: {{ 'var(--accent-green)' if total_bet and total_bet.edge|abs >= 4.0 else 'var(--text-secondary)' }};">Edge: {% if total_bet %}{{ "%+.1f"|format(total_bet.edge|abs) }}{% else %}--{% endif %}</span>
                    </div>
                    {% if total_bet and (total_bet.should_log or total_bet.clv_status) %}
                    <div class="tags-row" style="margin-top: 8px; justify-content: flex-start;">
                         {% if total_bet.clv_status == 'positive' %}
                            <span class="tag tag-green">✅ CLV: Beat Line</span>
                         {% elif total_bet.clv_status == 'negative' %}
                            <span class="tag tag-red">⚠️ CLV: Missed Line</span>
                         {% elif total_bet.clv_status == 'neutral' %}
                            <span class="tag tag-blue">➖ CLV: Neutral</span>
                         {% elif total_bet.clv_status is none %}
                            <span class="tag tag-blue">⏳ CLV: Tracking</span>
                         {% endif %}
                    </div>
                    {% endif %}
                </div>

                <!-- METRICS ROW -->
                <div class="metrics-row">
                    <div class="metric-box">
                        <div class="metric-title">PREDICTED</div>
                        <div class="metric-value">{{ game.predicted_score }}</div>
                    </div>
                    
                    {% set ai_score = 0 %}
                    {% if spread_bet %}{% set ai_score = ai_score + spread_bet.edge|abs %}{% endif %}
                    {% if total_bet %}{% set ai_score = ai_score + total_bet.edge|abs %}{% endif %}
                    
                    <div class="metric-box">
                        <div class="metric-title">TOTAL EDGE</div>
                        <div class="metric-value {{ 'good' if ai_score >= 6.0 else '' }}">{{ "%.1f"|format(ai_score) }}</div>
                    </div>
                </div>

            </div>
        </div>
        {% endfor %}

        <!-- PERFORMANCE STATS (Last 10/20/50) -->
        <div class="tracking-section">
            <div class="tracking-header">🔥 Recent Form</div>
            
            <div class="metrics-row" style="margin-bottom: 1.5rem;">
                <!-- Last 10 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 10</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{{ last_10.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_10.win_rate >= 55 else ('text-red' if last_10.win_rate < 50) }}">{{ "%.0f"|format(last_10.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_10.profit > 0 else ('text-red' if last_10.profit < 0) }}">{{ "%+.1f"|format(last_10.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_10.roi > 0 else ('text-red' if last_10.roi < 0) }}">{{ "%+.1f"|format(last_10.roi) }}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 20 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 20</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{{ last_20.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_20.win_rate >= 55 else ('text-red' if last_20.win_rate < 50) }}">{{ "%.0f"|format(last_20.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_20.profit > 0 else ('text-red' if last_20.profit < 0) }}">{{ "%+.1f"|format(last_20.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_20.roi > 0 else ('text-red' if last_20.roi < 0) }}">{{ "%+.1f"|format(last_20.roi) }}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 50 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 50</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{{ last_50.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_50.win_rate >= 55 else ('text-red' if last_50.win_rate < 50) }}">{{ "%.0f"|format(last_50.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_50.profit > 0 else ('text-red' if last_50.profit < 0) }}">{{ "%+.1f"|format(last_50.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_50.roi > 0 else ('text-red' if last_50.roi < 0) }}">{{ "%+.1f"|format(last_50.roi) }}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {% if completed_picks %}
        <div class="tracking-section">
            <div class="tracking-header">📊 Graded Picks Summary</div>
            <div class="summary-grid">
                <div class="prop-card" style="padding: 1rem; text-align: center;">
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">WINS</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-green);">{{ stats.won }}</div>
                </div>
                <div class="prop-card" style="padding: 1rem; text-align: center;">
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">LOSSES</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-red);">{{ stats.lost }}</div>
                </div>
                <div class="prop-card" style="padding: 1rem; text-align: center;">
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem;">WIN RATE</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: {{ 'var(--accent-green)' if stats.win_rate >= 52 else 'var(--accent-red)' }};">{{ "%.1f"|format(stats.win_rate) }}%</div>
                </div>
            </div>
        </div>
        {% endif %}

    </div>
</body>
</html>"""
    
    template = Template(template_str)
    html_output = template.render(
        analyses=analyses,
        timestamp=timestamp_str,
        team_abbr_map=team_abbr_map,
        stats=stats,
        last_10=last_10,
        last_20=last_20,
        last_50=last_50,
        daily_perf=daily_perf,
        completed_picks=completed_picks
    )
    
    with open(PICKS_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"\n✅ HTML saved: {PICKS_HTML_FILE}")

    return html_output



# ============================================================================
# TRACKING DASHBOARD FUNCTIONS
# ============================================================================

UNIT_SIZE = 100  # Standard bet size for ROI calculations

def normalize_nfl_tracking_data(bets_array):
    """Normalize NFL tracking data (array format) to standard dict format"""
    # NFL uses array format, need to convert to {"picks": [...]}
    normalized_picks = []
    
    for bet in bets_array:
        # Normalize field names and values
        pick = {
            'pick_id': bet.get('game_id', '') + '_' + bet.get('bet_type', ''),
            'game_date': bet.get('date_placed', ''),  # Use date_placed as game_date
            'pick_type': bet.get('bet_type', '').capitalize(),  # "spread" -> "Spread", "total" -> "Total"
            'pick_text': bet.get('recommendation', ''),
            'market_line': bet.get('line', 0),
            'edge': bet.get('edge', 0),
            'status': 'pending',  # Default
            'profit_loss': 0,  # Will be set from profit field
            'home_team': '',  # NFL structure doesn't have this, need to extract from recommendation
            'away_team': '',
            'matchup': bet.get('recommendation', ''),  # Use recommendation as matchup placeholder
        }
        
        # Map NFL status + result to standard status
        status = bet.get('status', 'pending')
        if status in ['win', 'loss', 'push']:
            # Already using standard format
            pick['status'] = status
        elif status == 'complete':
            # Old format - convert based on result
            result = bet.get('result', '').lower()
            if result in ['won', 'win']:
                pick['status'] = 'win'
            elif result in ['lost', 'loss']:
                pick['status'] = 'loss'
            else:
                pick['status'] = 'pending'
        else:
            pick['status'] = 'pending'
        
        # Convert profit from dollars (float) to cents (int)
        profit_dollars = bet.get('profit', 0.0) or 0.0
        pick['profit_loss'] = int(profit_dollars * 100)
        
        normalized_picks.append(pick)
    
    return {'picks': normalized_picks}

def load_picks_tracking():
    """Load and normalize NFL tracking data"""
    if PICKS_TRACKING_FILE.exists():
        try:
            with open(PICKS_TRACKING_FILE, 'r') as f:
                bets_array = json.load(f)
                # Normalize array format to dict format
                return normalize_nfl_tracking_data(bets_array)
        except:
            return {'picks': []}
    return {'picks': []}

def calculate_tracking_stats(tracking_data):
    """Calculate detailed tracking statistics for dashboard"""
    picks = tracking_data.get('picks', [])
    
    total_picks = len(picks)
    wins = sum(1 for p in picks if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in picks if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in picks if p.get('status', '').lower() == 'push')
    pending = sum(1 for p in picks if p.get('status', '').lower() == 'pending')
    
    # Calculate profit (profit_loss is in cents)
    total_profit_cents = sum(p.get('profit_loss', 0) for p in picks if p.get('profit_loss') is not None)
    total_profit_units = total_profit_cents / 100.0
    
    # Calculate win rate (excluding pushes and pending)
    decided_picks = wins + losses
    win_rate = (wins / decided_picks * 100) if decided_picks > 0 else 0.0
    
    # Calculate ROI
    total_risked = (wins + losses) * UNIT_SIZE
    roi = (total_profit_cents / total_risked * 100) if total_risked > 0 else 0.0
    
    # Breakdown by type
    spread_picks = [p for p in picks if p.get('pick_type', '').lower() == 'spread']
    total_picks_list = [p for p in picks if p.get('pick_type', '').lower() == 'total']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    
    total_wins = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'push')
    
    return {
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": win_rate,
        "total_profit": total_profit_cents,  # Return in cents for consistency
        "roi": roi,
        "spread_wins": spread_wins,
        "spread_losses": spread_losses,
        "spread_pushes": spread_pushes,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_pushes": total_pushes,
    }

def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks (most recent first)"""
    # Filter to only completed picks
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Take first N picks (most recent first since list is sorted reverse=True)
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
    total = wins + losses + pushes
    
    # Calculate profit (profit_loss is in cents, convert to units)
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    # Breakdown by type (NFL uses "Spread"/"Total" after normalization)
    spread_picks = [p for p in recent if p.get('pick_type', '').lower() == 'spread']
    total_picks = [p for p in recent if p.get('pick_type', '').lower() == 'total']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    spread_total = spread_wins + spread_losses + spread_pushes
    spread_profit_cents = sum(p.get('profit_loss', 0) for p in spread_picks if p.get('profit_loss') is not None)
    spread_profit_units = spread_profit_cents / 100.0
    spread_wr = (spread_wins / spread_total * 100) if spread_total > 0 else 0
    spread_roi = (spread_profit_cents / (spread_total * UNIT_SIZE) * 100) if spread_total > 0 else 0
    
    total_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
    total_total = total_wins + total_losses + total_pushes
    total_profit_cents = sum(p.get('profit_loss', 0) for p in total_picks if p.get('profit_loss') is not None)
    total_profit_units = total_profit_cents / 100.0
    total_wr = (total_wins / total_total * 100) if total_total > 0 else 0
    total_roi = (total_profit_cents / (total_total * UNIT_SIZE) * 100) if total_total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'count': len(recent),
        'spreads': {
            'record': f"{spread_wins}-{spread_losses}" + (f"-{spread_pushes}" if spread_pushes > 0 else ""),
            'win_rate': spread_wr,
            'profit': spread_profit_units,
            'roi': spread_roi,
            'count': len(spread_picks)
        },
        'totals': {
            'record': f"{total_wins}-{total_losses}" + (f"-{total_pushes}" if total_pushes > 0 else ""),
            'win_rate': total_wr,
            'profit': total_profit_units,
            'roi': total_roi,
            'count': len(total_picks)
        }
    }

def generate_tracking_html():
    """Generate HTML dashboard for tracking picks with last 100/50/20 breakdown"""
    from jinja2 import Template
    
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    # Get current time in Eastern timezone
    est_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(est_tz)
    
    # Separate pending and completed picks
    pending_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() == 'pending']
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Sort by game_date (date_placed in NFL)
    pending_picks.sort(key=lambda x: x.get('game_date', ''))
    completed_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    # Calculate Last 100, Last 50, and Last 20 picks performance
    last_100 = calculate_recent_performance(completed_picks, 100)
    last_50 = calculate_recent_performance(completed_picks, 50)
    last_20 = calculate_recent_performance(completed_picks, 20)
    
    daily_perf = get_daily_stats(tracking_data.get('picks', []))
    
    def format_game_date(date_str):
        """Format game_date to display date"""
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            dt_est = dt.astimezone(est_tz)
            return dt_est.strftime('%m/%d %I:%M %p')
        except:
            return str(date_str) if date_str else 'N/A'
    
    timestamp = datetime.now(est_tz).strftime('%Y-%m-%d %I:%M %p')
    
    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Model - Performance Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            padding: 1.5rem;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .card {
            background: #1a1a1a;
            border-radius: 1.25rem;
            border: none;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .stat-card {
            background: #262626;
            border: none;
            border-radius: 1rem;
            padding: 1.5rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #10b981;
        }
        .stat-label {
            color: #94a3b8;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
            font-weight: 500;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #ffffff;
            text-align: center;
        }
        h2 {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: #ffffff;
        }
        h3 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffffff;
        }
        h4 {
            font-size: 1.125rem;
            font-weight: 600;
            color: #94a3b8;
        }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #262626; }
        th { padding: 0.875rem 1rem; text-align: left; color: #94a3b8; font-weight: 600; font-size: 0.875rem; }
        td { padding: 0.875rem 1rem; border-bottom: 1px solid #2a3441; font-size: 0.9375rem; }
        tr:hover { background: #262626; }
        .text-center { text-align: center; }
        .text-green-400 { color: #10b981; }
        .text-blue-400 { color: #3b82f6; }
        .text-pink-400 { color: #f472b6; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #f59e0b; }
        .text-gray-400 { color: #94a3b8; }
        .font-bold { font-weight: 700; }
        .text-sm { font-size: 0.875rem; }
        .badge {
            display: inline-block;
            padding: 0.375rem 0.875rem;
            border-radius: 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-pending { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
        .badge-win { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-loss { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .badge-push { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
        .subtitle { color: #94a3b8; font-size: 1rem; font-weight: 400; }

        /* Mobile Responsiveness */
        @media (max-width: 1024px) {
            .container { max-width: 100%; }
            h1 { font-size: 2rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.25rem; }
        }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .card { padding: 1.25rem; }

            h1 { font-size: 1.75rem; }
            h2 { font-size: 1.25rem; }
            h3 { font-size: 1.125rem; }
            h4 { font-size: 1rem; }

            div[style*="grid-template-columns: repeat(5, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            div[style*="grid-template-columns: repeat(4, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            div[style*="grid-template-columns: repeat(2, 1fr)"] {
                grid-template-columns: 1fr !important;
            }

            .grid {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 0.75rem;
            }

            .stat-card {
                padding: 1rem;
            }
            .stat-value {
                font-size: 1.75rem;
            }
            .stat-label {
                font-size: 0.6875rem;
            }

            table {
                font-size: 0.8125rem;
                display: block;
                overflow-x: auto;
                white-space: nowrap;
                -webkit-overflow-scrolling: touch;
            }
            thead, tbody, tr {
                display: table;
                width: 100%;
                table-layout: fixed;
            }
            th, td {
                padding: 0.625rem 0.5rem;
                font-size: 0.8125rem;
            }
        }

        @media (max-width: 480px) {
            body { padding: 0.75rem; }
            .card { padding: 1rem; margin-bottom: 1rem; }

            h1 { font-size: 1.5rem; }
            h2 { font-size: 1.125rem; }
            h3 { font-size: 1rem; }

            .stat-value { font-size: 1.5rem; }
            .stat-label { font-size: 0.625rem; }
            .stat-card { padding: 0.75rem; }

            div[style*="grid-template-columns"] {
                grid-template-columns: 1fr !important;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            table { font-size: 0.75rem; }
            th, td { padding: 0.5rem 0.375rem; font-size: 0.75rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">🏈 NFL Model Performance</h1>
            <p class="text-center subtitle" style="margin-bottom: 1rem;">CourtSide Analytics</p>

            <!-- Daily Performance -->
            <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 2rem;">
                <div style="background: rgba(255,255,255,0.05); padding: 10px 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; font-weight: 600; text-align: center;">Today</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: {{ '#10b981' if daily_perf.today.w > daily_perf.today.l else '#ffffff' }}; text-align: center;">{{ daily_perf.today.w }}-{{ daily_perf.today.l }}</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 10px 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; font-weight: 600; text-align: center;">Yesterday</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: {{ '#10b981' if daily_perf.yesterday.w > daily_perf.yesterday.l else ('#ef4444' if daily_perf.yesterday.l > daily_perf.yesterday.w else '#ffffff') }}; text-align: center;">{{ daily_perf.yesterday.w }}-{{ daily_perf.yesterday.l }}</div>
                </div>
            </div>

            <!-- Overall Performance Card -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #3b82f6; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    📊 Overall Performance
                </h3>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.total_picks }}</div>
                        <div class="stat-label">Total Bets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.wins }}-{{ stats.losses }}{% if stats.pushes > 0 %}-{{ stats.pushes }}{% endif %}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f"|format(stats.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if stats.total_profit > 0 %}text-green-400{% elif stats.total_profit < 0 %}text-red-400{% endif %}">
                            {% if stats.total_profit > 0 %}+{% endif %}{{ "%.2f"|format(stats.total_profit/100) }}u
                        </div>
                        <div class="stat-label">Total Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if stats.roi > 0 %}text-green-400{% elif stats.roi < 0 %}text-red-400{% endif %}">
                            {% if stats.roi > 0 %}+{% endif %}{{ "%.1f"|format(stats.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ stats.spread_wins + stats.spread_losses + stats.spread_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">{{ stats.spread_wins }}-{{ stats.spread_losses }}{% if stats.spread_pushes > 0 %}-{{ stats.spread_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-blue-400 font-bold">{% if stats.spread_wins + stats.spread_losses > 0 %}{{ "%.1f"|format(stats.spread_wins / (stats.spread_wins + stats.spread_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="{% if (stats.spread_wins * 91 - stats.spread_losses * 100) > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.2f"|format((stats.spread_wins * 91 - stats.spread_losses * 100) / 100) }}u</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Totals ({{ stats.total_wins + stats.total_losses + stats.total_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #f472b6; margin-bottom: 0.5rem;">{{ stats.total_wins }}-{{ stats.total_losses }}{% if stats.total_pushes > 0 %}-{{ stats.total_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-pink-400 font-bold">{% if stats.total_wins + stats.total_losses > 0 %}{{ "%.1f"|format(stats.total_wins / (stats.total_wins + stats.total_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="{% if (stats.total_wins * 91 - stats.total_losses * 100) > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.2f"|format((stats.total_wins * 91 - stats.total_losses * 100) / 100) }}u</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {% if pending_picks %}
        <div class="card">
            <h2>🎯 Today's Projections</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Pick</th>
                            <th>Type</th>
                            <th>Line</th>
                            <th>Edge</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pick in pending_picks %}
                        <tr>
                            <td class="text-sm font-bold">{{ format_game_date(pick.game_date) }}</td>
                            <td class="font-bold text-yellow-400">{{ pick.pick_text }}</td>
                            <td>{{ pick.pick_type }}</td>
                            <td>{{ pick.market_line }}</td>
                            <td>{{ "%+.1f"|format(pick.edge) }}</td>
                            <td><span class="badge badge-pending">Pending</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <!-- PERFORMANCE BREAKDOWN - SELLING POINT -->
        <div class="card">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="font-size: 2rem; margin-bottom: 0.5rem;">🔥 Recent Performance Breakdown</h2>
                <p class="subtitle">Verified Track Record</p>
            </div>

            <!-- Last 100 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #3b82f6; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    📊 Last 100 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value">{{ last_100.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f"|format(last_100.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_100.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_100.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_100.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_100.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_100.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_100.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">{{ last_100.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-blue-400 font-bold">{{ "%.1f"|format(last_100.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_100.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_100.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_100.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #f472b6; margin-bottom: 0.5rem;">{{ last_100.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-pink-400 font-bold">{{ "%.1f"|format(last_100.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_100.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_100.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Last 50 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #3b82f6; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    🚀 Last 50 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ last_50.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ "%.1f"|format(last_50.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_50.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_50.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_50.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_50.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_50.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_50.spreads.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_50.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_50.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_50.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_50.totals.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_50.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Last 20 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem;">
                <h3 style="color: #3b82f6; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    ⚡ Last 20 Picks (Hot Streak)
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ last_20.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ "%.1f"|format(last_20.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_20.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_20.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_20.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_20.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_20.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_20.spreads.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_20.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_20.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_20.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_20.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_20.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_20.totals.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_20.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_20.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_20.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="text-center text-gray-400 text-sm" style="margin-top: 2rem;">
            <p>Last updated: {{ timestamp }}</p>
        </div>
    </div>
</body>
</html>'''
    
    template = Template(template_str)
    html_output = template.render(
        stats=stats,
        pending_picks=pending_picks,
        last_100=last_100,
        last_50=last_50,
        last_20=last_20,
        daily_perf=daily_perf,
        timestamp=timestamp,
        format_game_date=format_game_date,
    )
    
    with open(TRACKING_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"\n✅ Tracking dashboard saved: {TRACKING_HTML_FILE}")

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
    
    # STEP 1: Grade pending picks first (Dec 20, 2024)
    print("\n📊 STEP 1: Grading Pending Picks")
    grade_pending_picks()
    
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
    
    picks_html = generate_picks_html(analyses, stats, tracker)
    with open(PICKS_HTML_FILE, 'w') as f:
        f.write(picks_html)
    print(f"✅ Created: {PICKS_HTML_FILE}")
    
    # Generate overall tracking dashboard
    generate_tracking_html()
    
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

