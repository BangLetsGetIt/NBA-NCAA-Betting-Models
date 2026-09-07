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

CURRENT_YEAR = 2026
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

        val = stat_value.actual_instance if hasattr(stat_value, 'actual_instance') else stat_value
        team_stats_dict[team_name][stat_name] = val

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
def get_current_cfb_week():
    """Return estimated current CFB week based on today's date.
    CFB Week 1 starts around Aug 24 each year.
    """
    now = datetime.now()
    season_start = datetime(now.year, 8, 24)
    if now < season_start:
        return 1
    days_in = (now - season_start).days
    return max(1, min((days_in // 7) + 1, 15))


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
    """Generate CourtSide Analytics-style HTML report for CFB predictions"""

    spread_picks = sum(1 for g in results['games'] if g['has_bet'])
    total_picks  = sum(1 for g in results['games'] if g['has_total_bet'])

    picks_html = ""
    for game in results['games']:
        away = game['away_team']
        home = game['home_team']
        matchup = f"{away} @ {home}"
        game_time = game.get('start_time', 'TBD')

        if game['has_bet']:
            pick_label = game.get('pick_team_spread', 'N/A')
            picks_html += f"""
    <div class="prop-card glow-green">
        <div class="card-header">
            <div class="header-left">
                <div class="player-info">
                    <h2>{matchup}</h2>
                    <div class="matchup-info">{home} Home</div>
                </div>
            </div>
            <div class="game-meta">
                <div class="bet-type-badge">Spread</div>
                <div class="game-date-time">{game_time}</div>
            </div>
        </div>
        <div class="card-body">
            <div class="bet-main-row">
                <div class="bet-selection">
                    <span class="txt-green">{pick_label}</span>
                </div>
            </div>
            <div class="model-subtext">Cover probability: <strong>{game['cover_prob']}</strong></div>
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-title">Model Line</div>
                    <div class="stat-val">{game['predicted_spread']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-title">Market Line</div>
                    <div class="stat-val">{game['market_spread']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-title">Edge</div>
                    <div class="stat-val txt-green">{game['edge']} pts</div>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-item"><span class="metric-lbl">COVER %</span><span class="metric-val txt-green">{game['cover_prob']}</span></div>
                <div class="metric-item"><span class="metric-lbl">EDGE</span><span class="metric-val txt-green">{game['edge']} pts</span></div>
                <div class="metric-item"><span class="metric-lbl">KELLY</span><span class="metric-val">{game['kelly_size']}</span></div>
            </div>
            <div class="tags-container">
                <span class="tag tag-green">Spread Value</span>
                <span class="tag tag-blue">EPA Model</span>
            </div>
        </div>
    </div>"""

        if game['has_total_bet'] and game['total_has_line']:
            picks_html += f"""
    <div class="prop-card glow-green">
        <div class="card-header">
            <div class="header-left">
                <div class="player-info">
                    <h2>{matchup}</h2>
                    <div class="matchup-info">{home} Home</div>
                </div>
            </div>
            <div class="game-meta">
                <div class="bet-type-badge">Total</div>
                <div class="game-date-time">{game_time}</div>
            </div>
        </div>
        <div class="card-body">
            <div class="bet-main-row">
                <div class="bet-selection">
                    <span class="txt-green">{game['total_pick']}</span>
                    <span class="line">{game['market_total']}</span>
                </div>
            </div>
            <div class="model-subtext">Over probability: <strong>{game['prob_over']}</strong></div>
            <div class="stats-row">
                <div class="stat-item">
                    <div class="stat-title">Model Total</div>
                    <div class="stat-val">{game['expected_total']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-title">Market Total</div>
                    <div class="stat-val">{game['market_total']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-title">Edge</div>
                    <div class="stat-val txt-green">{game['total_edge']} pts</div>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-item"><span class="metric-lbl">OVER %</span><span class="metric-val txt-green">{game['prob_over']}</span></div>
                <div class="metric-item"><span class="metric-lbl">EDGE</span><span class="metric-val txt-green">{game['total_edge']} pts</span></div>
                <div class="metric-item"><span class="metric-lbl">KELLY</span><span class="metric-val">{game['kelly_total']}</span></div>
            </div>
            <div class="tags-container">
                <span class="tag tag-green">Total Value</span>
                <span class="tag tag-blue">EPA Model</span>
            </div>
        </div>
    </div>"""

    if not picks_html:
        picks_html = '<div class="no-bets">No qualifying picks today.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics — CFB Model</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    :root {{
        --bg-main: #0a0a0a; --bg-card: #1a1a1a; --bg-card-secondary: #222222;
        --text-primary: #ffffff; --text-secondary: #94a3b8;
        --accent-green: #4ade80; --accent-red: #f87171; --accent-blue: #60a5fa;
        --border-color: #2a2a2a;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 20px; font-family: 'Inter', system-ui, sans-serif;
           background-color: var(--bg-main); color: var(--text-primary); }}
    .container {{ max-width: 820px; margin: 0 auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center;
             margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 18px; }}
    h1 {{ margin: 0; font-size: 22px; font-weight: 800; }}
    .subheader {{ font-size: 15px; font-weight: 600; margin-top: 2px; }}
    .date-sub {{ color: var(--text-secondary); font-size: 13px; margin-top: 4px; }}
    .nav-bar {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }}
    .nav-link {{ padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
                text-decoration: none; border: 1px solid var(--border-color);
                color: var(--text-secondary); background: var(--bg-card); transition: all 0.15s; }}
    .nav-link:hover {{ color: var(--text-primary); border-color: var(--accent-blue); }}
    .nav-link.active {{ color: var(--accent-blue); border-color: var(--accent-blue);
                       background: rgba(96,165,250,0.1); }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px; }}
    .stat-box {{ background: var(--bg-card); border-radius: 12px; padding: 16px;
                text-align: center; border: 1px solid var(--border-color); }}
    .stat-label {{ font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .5px; margin-bottom: 6px; }}
    .stat-value {{ font-size: 22px; font-weight: 700; }}
    .txt-green {{ color: var(--accent-green); }}
    .txt-red   {{ color: var(--accent-red); }}
    .prop-card {{ background: var(--bg-card); border-radius: 16px; overflow: hidden;
                 margin-bottom: 18px; border: 1px solid var(--border-color);
                 box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
    .prop-card.glow-green {{ border-color: rgba(74,222,128,0.25); box-shadow: 0 0 15px rgba(74,222,128,0.1); }}
    .card-header {{ padding: 14px 18px; background: var(--bg-card-secondary);
                   display: flex; justify-content: space-between; align-items: center;
                   border-bottom: 1px solid var(--border-color); gap: 10px; }}
    .header-left {{ display: flex; align-items: center; gap: 12px; }}
    .player-info h2 {{ margin: 0; font-size: 17px; font-weight: 700; line-height: 1.2; }}
    .matchup-info {{ font-size: 13px; color: var(--text-secondary); margin-top: 2px; }}
    .game-meta {{ text-align: right; flex-shrink: 0; }}
    .bet-type-badge {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
                      color: var(--accent-blue); letter-spacing: .4px; }}
    .game-date-time {{ font-size: 12px; color: var(--text-secondary); margin-top: 3px; }}
    .card-body {{ padding: 18px; }}
    .bet-main-row {{ margin-bottom: 10px; }}
    .bet-selection {{ display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
    .bet-selection .txt-green {{ font-size: 20px; font-weight: 800; }}
    .line {{ font-size: 18px; font-weight: 600; color: var(--text-primary); }}
    .model-subtext {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; }}
    .model-subtext strong {{ color: var(--text-primary); }}
    .stats-row {{ display: flex; gap: 10px; margin-bottom: 12px; }}
    .stat-item {{ background: var(--bg-main); border-radius: 8px; padding: 10px 14px; flex: 1; }}
    .stat-title {{ font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .4px; margin-bottom: 4px; }}
    .stat-val {{ font-size: 16px; font-weight: 700; }}
    .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }}
    .metric-item {{ background: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }}
    .metric-lbl {{ display: block; font-size: 10px; color: var(--text-secondary);
                  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }}
    .metric-val {{ font-size: 15px; font-weight: 700; }}
    .tags-container {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tag {{ font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; }}
    .tag-green {{ background: rgba(74,222,128,0.12); color: var(--accent-green); }}
    .tag-blue  {{ background: rgba(96,165,250,0.12); color: var(--accent-blue); }}
    .no-bets {{ text-align: center; color: var(--text-secondary); padding: 40px; font-style: italic;
               background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border-color); }}
    footer {{ text-align: center; font-size: 12px; color: var(--text-secondary); margin-top: 40px;
             padding-top: 20px; border-top: 1px solid var(--border-color); }}
    @media (max-width: 768px) {{
        .stats-row {{ flex-wrap: wrap; }}
        .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
        body {{ padding: 12px; }}
    }}
    </style>
</head>
<body>
<div class="container">
    <div class="nav-bar">
        <a href="cfb_model_output.html" class="nav-link active">🏈 CFB Picks</a>
    </div>
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">🏈 College Football</div>
            <div class="date-sub">{results['date']} • EPA Model • Alpha V1.0</div>
        </div>
    </header>
    <div class="summary-grid">
        <div class="stat-box">
            <div class="stat-label">Games Analyzed</div>
            <div class="stat-value">{results['total_games']}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Spread Picks</div>
            <div class="stat-value txt-green">{spread_picks}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Total Picks</div>
            <div class="stat-value txt-green">{total_picks}</div>
        </div>
    </div>
    {picks_html}
    <footer>
        Model based on EPA (Expected Points Added) &amp; Advanced Analytics<br>
        Always bet responsibly. Past performance doesn't guarantee future results.
    </footer>
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

        # Fetch current week and next week to capture all upcoming games
        current_week = get_current_cfb_week()
        week_games = []
        for week in [current_week, current_week + 1]:
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
        print(f"   Found {len(upcoming_games)} games (Week {current_week}):")
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
