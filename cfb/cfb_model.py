import cfbd
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime
import time

# --- CONFIGURATION ---
# Load .env from current directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

if not CFBD_API_KEY:
    raise ValueError("Please set your CFBD_API_KEY in .env file")

CURRENT_YEAR = 2025
BANKROLL = 10000  # Example Bankroll $10,000

print(f"--- INITIALIZING CFB ALPHA MODEL ({CURRENT_YEAR} Season) ---")

# --- API CONNECTION ---
configuration = cfbd.Configuration()
configuration.api_key['Authorization'] = CFBD_API_KEY
configuration.api_key_prefix['Authorization'] = 'Bearer'
# Set the host explicitly
configuration.host = 'https://api.collegefootballdata.com'

api_client = cfbd.ApiClient(configuration)
api_client.set_default_header('Authorization', f'Bearer {CFBD_API_KEY}')

stats_api = cfbd.StatsApi(api_client)
games_api = cfbd.GamesApi(api_client)
betting_api = cfbd.BettingApi(api_client)

# ==========================================
# 1. DATA INGESTION ENGINE
# ==========================================
def fetch_advanced_stats():
    """Fetch and calculate team EPA metrics and scoring stats from live CFBD data"""
    print("1. Fetching Live Advanced Stats & Scoring Data from CFBD...")

    try:
        # Fetch season-level advanced stats
        season_stats_raw = stats_api.get_advanced_season_stats(year=CURRENT_YEAR)
        # Fetch basic team stats for scoring/pace data
        team_season_stats = stats_api.get_team_stats(year=CURRENT_YEAR)
    except Exception as e:
        print(f"Error connecting to CFBD: {e}")
        return None

    team_data = []

    # First, get EPA data
    epa_dict = {}
    for team_stat in season_stats_raw:
        if not hasattr(team_stat, 'offense') or not hasattr(team_stat, 'defense'):
            continue
        if team_stat.offense is None or team_stat.defense is None:
            continue

        epa_off = 0.0
        epa_def = 0.0
        success_rate = 0.0

        if hasattr(team_stat.offense, 'ppa') and team_stat.offense.ppa is not None:
            epa_off = float(team_stat.offense.ppa)
        if hasattr(team_stat.defense, 'ppa') and team_stat.defense.ppa is not None:
            epa_def = float(team_stat.defense.ppa)
        if hasattr(team_stat.offense, 'success_rate') and team_stat.offense.success_rate is not None:
            success_rate = float(team_stat.offense.success_rate)

        epa_dict[team_stat.team] = {
            'EPA_Off': epa_off,
            'EPA_Def': epa_def,
            'Success_Rate': success_rate,
        }

    # Now get scoring and pace data
    # API returns stats in key-value format (stat_name, stat_value)
    # Group by team first
    team_stats_dict = {}
    for team_stat in team_season_stats:
        team_name = team_stat.team
        stat_name = team_stat.stat_name
        stat_value = team_stat.stat_value

        if team_name not in team_stats_dict:
            team_stats_dict[team_name] = {}

        team_stats_dict[team_name][stat_name] = stat_value

    # Debug: Print available stat names from first team
    if team_stats_dict:
        first_team = list(team_stats_dict.keys())[0]
        print(f"   DEBUG - Available stats for {first_team}: {list(team_stats_dict[first_team].keys())[:10]}")

    # Now process each team with their complete stats
    for team_name, stats in team_stats_dict.items():
        # Initialize with EPA data if available
        if team_name in epa_dict:
            row = epa_dict[team_name].copy()
            row['Team'] = team_name
        else:
            row = {
                'Team': team_name,
                'EPA_Off': 0.0,
                'EPA_Def': 0.0,
                'Success_Rate': 0.0,
            }

        # Extract scoring and pace data from stats dictionary
        # Common stat names: totalPoints, totalPointsAllowed, games, totalPlays
        games = float(stats.get('games', 1))

        if games > 0:
            total_points = float(stats.get('totalPoints', 0))
            total_points_allowed = float(stats.get('totalPointsAllowed', 0))
            total_plays = float(stats.get('totalPlays', 0))

            row['PPG'] = total_points / games
            row['PPG_Allowed'] = total_points_allowed / games
            row['Pace'] = total_plays / games
        else:
            row['PPG'] = 0.0
            row['PPG_Allowed'] = 0.0
            row['Pace'] = 0.0

        team_data.append(row)

    if not team_data:
        print("   No data available")
        return None

    df = pd.DataFrame(team_data)
    df['EPA_Net'] = df['EPA_Off'] - df['EPA_Def']

    print(f"   Loaded stats for {len(df)} teams (EPA + Scoring/Pace data)")
    return df

# ==========================================
# 2. PREDICTION ENGINE
# ==========================================
def predict_spread(team_a_stats, team_b_stats):
    """
    Predict point spread using EPA differential.
    Positive number = Team A favored by that many points
    """
    epa_diff = team_a_stats['EPA_Net'] - team_b_stats['EPA_Net']

    # Convert EPA differential to point spread (empirically tuned)
    # 1.0 EPA advantage ≈ 10-14 points
    predicted_spread = epa_diff * 12

    return predicted_spread

def calculate_spread_probability(predicted_spread, actual_spread):
    """
    Calculate probability that Team A covers the spread.
    Uses a simplified logistic model.
    """
    # Edge = Our prediction vs Market line
    edge = predicted_spread - actual_spread

    # Convert edge to probability (logistic function)
    # Larger edge = higher probability of covering
    import math
    prob = 1 / (1 + math.exp(-edge / 7))  # 7 is spread volatility factor

    return prob

def calculate_total_probability(team_a_stats, team_b_stats, market_total):
    """
    Predict game total using scoring trends and pace data.
    """
    # Method 1: Use actual PPG (Points Per Game) data
    team_a_expected = team_a_stats['PPG'] if team_a_stats['PPG'] > 0 else 24.0
    team_b_expected = team_b_stats['PPG'] if team_b_stats['PPG'] > 0 else 24.0

    # Adjust for defensive strength
    if team_a_stats['PPG_Allowed'] > 0:
        team_a_expected = (team_a_expected + team_b_stats['PPG_Allowed']) / 2
    if team_b_stats['PPG_Allowed'] > 0:
        team_b_expected = (team_b_expected + team_a_stats['PPG_Allowed']) / 2

    # Calculate expected total
    expected_total = team_a_expected + team_b_expected

    # Adjust for pace if available
    if team_a_stats['Pace'] > 0 and team_b_stats['Pace'] > 0:
        avg_pace = (team_a_stats['Pace'] + team_b_stats['Pace']) / 2
        league_avg_pace = 65.0  # Typical CFB plays per game
        pace_factor = avg_pace / league_avg_pace
        expected_total *= pace_factor

    # Calculate probability
    if market_total == 0:
        return expected_total, 0.50

    edge = expected_total - market_total
    # Convert edge to probability (sigmoid-like function)
    prob_over = 0.50 + (edge / 20)  # 20 points = ~100% confidence swing

    # Clamp between 30% and 70%
    prob_over = max(0.30, min(0.70, prob_over))

    return expected_total, prob_over

# ==========================================
# 3. KELLY CRITERION
# ==========================================
def kelly_criterion(true_prob, decimal_odds):
    """Calculate optimal bet size using Kelly Criterion"""
    b = decimal_odds - 1
    q = 1 - true_prob
    f = (b * true_prob - q) / b
    return max(0, f)

# ==========================================
# 4. HTML GENERATION
# ==========================================
def generate_html(results):
    """Generate NBA-style HTML report for CFB predictions"""

    games_html = ""
    for game in results['games']:
        pick_class = 'pick-yes' if game['has_bet'] else 'pick-none'

        games_html += f"""
                <div class="game-card">
                    <div class="matchup">{game['away_team']} @ {game['home_team']}</div>
                    <div class="game-time">🏈 {game['start_time']}</div>

                    <div class="bet-section">
                        <div class="bet-box">
                            <div class="bet-title">📊 SPREAD BET</div>
                            <div class="odds-line">
                                <span>Market Line:</span>
                                <strong>{game['market_spread']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Prediction:</span>
                                <strong>{game['predicted_spread']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{game['edge']} pts</strong>
                            </div>

                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Confidence</span>
                                    <span class="confidence-pct">{game['cover_prob']}</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {game['confidence']}%"></div>
                                </div>
                            </div>

                            <div class="pick {pick_class}">
                                <strong style="font-size: 1.3rem;">{'✅ ' + game['pick_team_spread'] if game['has_bet'] else '⏸️ PASS'}</strong><br>
                                <small>{game['recommendation']}</small><br>
                                <small style="opacity: 0.7;">Why: Our model sees {game['edge']} points of value in this matchup</small>
                            </div>
                        </div>

                        <div class="bet-box" style="border-left-color: #6366f1;">
                            <div class="bet-title" style="color: #6366f1;">💰 TOTAL (OVER/UNDER)</div>
                            <div class="odds-line">
                                <span>Market Total:</span>
                                <strong>{game['market_total']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Prediction:</span>
                                <strong>{game['expected_total']}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{game['total_edge']} pts</strong>
                            </div>

                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Over Probability</span>
                                    <span class="confidence-pct">{game['prob_over']}</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {game['total_confidence']}%; background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);"></div>
                                </div>
                            </div>

                            <div class="pick {'pick-yes' if game['has_total_bet'] else 'pick-none'}">
                                <strong style="font-size: 1.3rem;">{'✅ ' + game['total_pick'] if game['has_total_bet'] else '⏸️ PASS'}</strong><br>
                                <small>{game['total_recommendation']}</small><br>
                                <small style="opacity: 0.7;">{('Why: Model projects ' + game['expected_total'] + ' total points vs market of ' + game['market_total']) if game['total_has_line'] else ''}</small>
                            </div>
                        </div>
                    </div>
                </div>
        """

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CFB Alpha Model - {results['date']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            padding: 2rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{
            background: #1a1a1a;
            border-radius: 1rem;
            border: 1px solid #2a2a2a;
            padding: 2rem;
            margin-bottom: 1.5rem;
        }}
        .header-card {{
            text-align: center;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 2px solid #ff6b35;
        }}
        .game-card {{
            padding: 1.5rem;
            border-bottom: 1px solid #2a2a2a;
        }}
        .game-card:last-child {{ border-bottom: none; }}
        .matchup {{ font-size: 1.5rem; font-weight: 800; color: #ffffff; margin-bottom: 0.5rem; }}
        .game-time {{ color: #9ca3af; font-size: 0.875rem; margin-bottom: 1rem; }}
        .bet-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }}
        .bet-box {{
            background: #0a0a0a;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #ff6b35;
        }}
        .bet-title {{
            font-weight: 700;
            color: #ff6b35;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            font-size: 0.875rem;
            letter-spacing: 0.05em;
        }}
        .odds-line {{
            display: flex;
            justify-content: space-between;
            margin: 0.25rem 0;
            font-size: 0.95rem;
            color: #cbd5e1;
        }}
        .odds-line strong {{ color: #ffffff; }}
        .confidence-bar-container {{ margin: 0.75rem 0; }}
        .confidence-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            color: #9ca3af;
        }}
        .confidence-pct {{
            font-weight: 700;
            color: #ff6b35;
        }}
        .confidence-bar {{
            height: 8px;
            background: #1e293b;
            border-radius: 999px;
            overflow: hidden;
            border: 1px solid #2a2a2a;
        }}
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #ff6b35 0%, #f77f00 100%);
            border-radius: 999px;
            transition: width 0.3s ease;
        }}
        .pick {{
            font-weight: 700;
            padding: 0.75rem;
            margin-top: 0.5rem;
            border-radius: 0.375rem;
            font-size: 1.1rem;
            line-height: 1.6;
        }}
        .pick small {{
            display: block;
            font-size: 0.85rem;
            font-weight: 400;
            margin-top: 0.5rem;
            opacity: 0.9;
            line-height: 1.4;
        }}
        .pick-yes {{ background-color: #064e3b; color: #10b981; border: 2px solid #10b981; }}
        .pick-none {{ background-color: #1e293b; color: #94a3b8; border: 2px solid #475569; }}
        .badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 700;
            background-color: #7c2d12;
            color: #ff6b35;
            margin: 0.25rem;
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
            <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem;">🏈 CFB MODEL PICKS</h1>
            <p style="font-size: 1.25rem; opacity: 0.9;">EPA-Based Predictive Model</p>
            <div>
                <div class="badge">● EPA ANALYSIS</div>
                <div class="badge">● SPREAD PREDICTIONS</div>
                <div class="badge">● TOTAL PREDICTIONS</div>
                <div class="badge">● VALUE BETTING</div>
            </div>
            <p style="font-size: 0.875rem; opacity: 0.75; margin-top: 1rem;">Generated: {results['date']}</p>
            <p style="font-size: 1rem; margin-top: 0.5rem;">Games: {results['total_games']} | Betting Opportunities: {results['total_bets']}</p>
        </div>

        <div class="card">
{games_html}
        </div>

        <div style="text-align: center; margin-top: 2rem; padding: 1rem; color: #64748b; font-size: 0.875rem;">
            Model based on EPA (Expected Points Added) & Advanced Analytics<br>
            Always bet responsibly. Past performance doesn't guarantee future results.
        </div>
    </div>
</body>
</html>
"""
    return html

# ==========================================
# 5. EXECUTION
# ==========================================
def main():
    # Fetch team stats
    team_stats = fetch_advanced_stats()
    if team_stats is None:
        print("Failed to fetch team stats")
        return

    print("\n2. Fetching This Week's Games...")

    # Fetch this week's games from API
    try:
        from datetime import datetime as dt, timedelta
        from dateutil import parser as date_parser
        import pytz

        # Get current time in Eastern Time
        eastern = pytz.timezone('US/Eastern')
        now = dt.now(eastern)
        today = now.date()

        # Thanksgiving week - show games from the next 7 days
        print(f"   Fetching upcoming games starting {today.strftime('%B %d, %Y')} {now.strftime('%I:%M %p ET')}...")

        # Try both Week 13 and 14 to capture all games
        week_games = []
        for week in [13, 14]:
            try:
                live_games = games_api.get_games(
                    year=CURRENT_YEAR,
                    season_type='regular',
                    week=week
                )

                for game in live_games:
                    if game.home_team and game.away_team:
                        # Handle different date formats
                        if hasattr(game, 'start_date') and game.start_date:
                            if isinstance(game.start_date, str):
                                parsed_dt = date_parser.parse(game.start_date)
                                # Make timezone-aware for comparison
                                if parsed_dt.tzinfo is None:
                                    parsed_dt = eastern.localize(parsed_dt)
                                game_date = parsed_dt.date()
                                # Format: "Sat, Nov 22 - 12:00 PM ET"
                                start_time = parsed_dt.strftime('%a, %b %d - %I:%M %p ET')
                                game_datetime = parsed_dt
                            else:
                                if hasattr(game.start_date, 'date'):
                                    game_date = game.start_date.date()
                                    game_datetime = game.start_date if game.start_date.tzinfo else eastern.localize(game.start_date)
                                else:
                                    game_date = today
                                    game_datetime = now
                                start_time = game.start_date.strftime('%a, %b %d - %I:%M %p ET') if hasattr(game.start_date, 'strftime') else 'TBD'
                        else:
                            game_date = today
                            start_time = 'TBD'
                            game_datetime = now

                        # Skip games that have already started
                        if hasattr(game_datetime, 'tzinfo') and game_datetime < now:
                            continue

                        # Get betting lines for this game
                        spread = 0.0
                        total = 0.0
                        try:
                            lines = betting_api.get_lines(
                                year=CURRENT_YEAR,
                                week=week,
                                season_type='regular',
                                team=game.home_team
                            )
                            if lines:
                                for line in lines:
                                    # Look for this specific game and get consensus spread
                                    if line.home_team == game.home_team and line.away_team == game.away_team:
                                        if hasattr(line, 'lines') and line.lines:
                                            # Get the first available line (usually consensus)
                                            for book_line in line.lines:
                                                if hasattr(book_line, 'spread') and book_line.spread:
                                                    spread = float(book_line.spread)
                                                if hasattr(book_line, 'over_under') and book_line.over_under:
                                                    total = float(book_line.over_under)
                                                if spread != 0.0:
                                                    break
                                        break
                        except:
                            pass

                        week_games.append({
                            'away': game.away_team,
                            'home': game.home_team,
                            'spread': spread,
                            'total': total,
                            'start_time': start_time,
                            'game_date': game_date
                        })
            except Exception as e:
                print(f"   Error fetching week {week}: {e}")
                continue

        # Sort by game date
        week_games.sort(key=lambda x: x.get('game_date', today))
        upcoming_games = week_games

    except Exception as e:
        print(f"   Error fetching games: {e}")
        upcoming_games = []

    if upcoming_games:
        # Count games by date
        from collections import Counter
        dates = [g.get('game_date', today) for g in upcoming_games]
        date_counts = Counter(dates)
        print(f"   Found {len(upcoming_games)} games this week (Week 14):")
        for date, count in sorted(date_counts.items()):
            print(f"     - {date.strftime('%A, %B %d')}: {count} games")
    else:
        print(f"   Found 0 games this week")

    results = {
        'date': datetime.now().strftime('%B %d, %Y'),
        'week': 'Current',
        'total_games': len(upcoming_games),
        'total_bets': 0,
        'games': []
    }

    for game in upcoming_games:
        away_stats = team_stats[team_stats['Team'] == game['away']]
        home_stats = team_stats[team_stats['Team'] == game['home']]

        if away_stats.empty or home_stats.empty:
            continue

        away_stats = away_stats.iloc[0]
        home_stats = home_stats.iloc[0]

        # Predict spread (positive = home favored)
        predicted = predict_spread(home_stats, away_stats)
        # Spread from API is already from home team perspective
        # Positive spread = home team is underdog (getting points)
        # Negative spread = home team is favorite (giving points)
        market = game['spread']

        # Calculate cover probability
        cover_prob = calculate_spread_probability(predicted, market)

        # Calculate total prediction
        market_total = game['total']
        expected_total, prob_over = calculate_total_probability(away_stats, home_stats, market_total)

        # Determine spread bet
        decimal_odds = (100 / 110) + 1  # Standard -110 odds

        # Calculate kelly for the side we're actually betting (home or away)
        if cover_prob > 0.50:
            kelly = kelly_criterion(cover_prob, decimal_odds)
        else:
            kelly = kelly_criterion(1 - cover_prob, decimal_odds)  # Away team probability

        has_bet = kelly > 0.02 and (cover_prob > 0.55 or cover_prob < 0.45)

        # Determine total bet - calculate kelly for the side we're betting (over or under)
        if market_total > 0:
            if prob_over > 0.50:
                kelly_total = kelly_criterion(prob_over, decimal_odds)
            else:
                kelly_total = kelly_criterion(1 - prob_over, decimal_odds)  # UNDER probability
        else:
            kelly_total = 0

        has_total_bet = kelly_total > 0.02 and (prob_over > 0.55 or prob_over < 0.45)

        if has_bet or has_total_bet:
            results['total_bets'] += 1

        # Calculate edge
        edge = abs(predicted - market)
        total_edge = abs(expected_total - market_total) if market_total > 0 else 0

        # Format game data
        game_data = {
            'away_team': game['away'],
            'home_team': game['home'],
            'away_epa': f"{away_stats['EPA_Net']:.2f}",
            'home_epa': f"{home_stats['EPA_Net']:.2f}",
            'predicted_spread': f"{predicted:+.1f}",
            'market_spread': f"{market:+.1f}",
            'edge': f"{edge:.1f}",
            'cover_prob': f"{cover_prob:.0%}",
            'confidence': int(cover_prob * 100),
            'kelly_size': f"{kelly*0.5:.1%}",
            'has_bet': has_bet,
            'start_time': game.get('start_time', 'TBD'),
            # Total prediction data
            'market_total': f"{market_total:.1f}" if market_total > 0 else "N/A",
            'expected_total': f"{expected_total:.1f}",
            'total_edge': f"{total_edge:.1f}",
            'prob_over': f"{prob_over:.0%}",
            'total_confidence': int(prob_over * 100),
            'kelly_total': f"{kelly_total*0.5:.1%}",
            'has_total_bet': has_total_bet,
            'total_has_line': market_total > 0
        }

        if has_bet:
            # If model predicts home to cover (higher prob), bet home team
            # Otherwise bet away team
            if cover_prob > 0.55:
                pick = game['home']
                # Home team gets the market spread as-is
                spread_str = f"{market:+.1f}"
            else:
                pick = game['away']
                # Away team gets opposite of market spread
                spread_str = f"{-market:+.1f}"

            game_data['pick'] = pick
            game_data['pick_spread'] = spread_str
            game_data['pick_team_spread'] = f"{pick} {spread_str}"
            game_data['recommendation'] = f'BET {pick} to cover the spread ({spread_str})'
        else:
            game_data['pick'] = 'PASS'
            game_data['pick_team_spread'] = 'NO BET'
            game_data['recommendation'] = 'No significant edge - Skip this game'

        # Add total recommendation
        if has_total_bet and market_total > 0:
            if prob_over > 0.55:
                game_data['total_pick'] = 'OVER'
                game_data['total_recommendation'] = f'BET OVER {market_total:.1f}'
            else:
                game_data['total_pick'] = 'UNDER'
                game_data['total_recommendation'] = f'BET UNDER {market_total:.1f}'
        else:
            game_data['total_pick'] = 'PASS'
            if market_total > 0:
                game_data['total_recommendation'] = 'No significant edge on total'
            else:
                game_data['total_recommendation'] = 'Total line not available'

        results['games'].append(game_data)

    # Generate HTML
    html_output = generate_html(results)
    output_file = 'cfb_model_output.html'
    with open(output_file, 'w') as f:
        f.write(html_output)

    print(f"\n✅ Analysis Complete!")
    print(f"   Games Analyzed: {results['total_games']}")
    print(f"   Betting Opportunities: {results['total_bets']}")
    print(f"   HTML report generated: {output_file}")

if __name__ == "__main__":
    main()
