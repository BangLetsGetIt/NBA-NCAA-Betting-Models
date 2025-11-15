import requests
import json
from datetime import datetime
import pytz

# API Configuration
ODDS_API_KEY = '671958bc1621170701241a09d5ecc627'
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'

def get_player_props():
    """Fetch NBA player props from The Odds API"""
    url = f"{ODDS_API_BASE}/sports/basketball_nba/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists',
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []

def get_event_odds(event_id):
    """Fetch player prop odds for a specific event"""
    url = f"{ODDS_API_BASE}/sports/basketball_nba/events/{event_id}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists',
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching odds for event {event_id}: {e}")
        return None

def process_props(events_data):
    """Process all player props and organize by player and market"""
    all_props = []
    
    for event in events_data:
        event_id = event.get('id')
        home_team = event.get('home_team')
        away_team = event.get('away_team')
        commence_time = event.get('commence_time')
        
        # Get odds for this event
        odds_data = get_event_odds(event_id)
        if not odds_data:
            continue
        
        # Process bookmakers
        for bookmaker in odds_data.get('bookmakers', []):
            book_name = bookmaker.get('title')
            
            for market in bookmaker.get('markets', []):
                market_key = market.get('key')
                market_name = get_market_display_name(market_key)
                
                for outcome in market.get('outcomes', []):
                    player_name = outcome.get('description')
                    line = outcome.get('point')
                    over_price = outcome.get('price') if outcome.get('name') == 'Over' else None
                    under_price = None
                    
                    # Find the corresponding under
                    for under_outcome in market.get('outcomes', []):
                        if (under_outcome.get('description') == player_name and 
                            under_outcome.get('name') == 'Under' and 
                            under_outcome.get('point') == line):
                            under_price = under_outcome.get('price')
                            break
                    
                    if outcome.get('name') == 'Over' and over_price and under_price:
                        all_props.append({
                            'player': player_name,
                            'market': market_name,
                            'market_key': market_key,
                            'line': line,
                            'over_odds': over_price,
                            'under_odds': under_price,
                            'bookmaker': book_name,
                            'game': f"{away_team} @ {home_team}",
                            'commence_time': commence_time
                        })
    
    return all_props

def get_market_display_name(market_key):
    """Convert market key to display name"""
    market_names = {
        'player_points': 'Points',
        'player_rebounds': 'Rebounds',
        'player_assists': 'Assists',
        'player_threes': '3-Pointers Made',
        'player_points_rebounds_assists': 'Pts + Rebs + Asts',
        'player_points_rebounds': 'Pts + Rebs',
        'player_points_assists': 'Pts + Asts',
        'player_rebounds_assists': 'Rebs + Asts'
    }
    return market_names.get(market_key, market_key)

def american_to_decimal(odds):
    """Convert American odds to decimal"""
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1

def decimal_to_american(decimal):
    """Convert decimal odds to American"""
    if decimal >= 2:
        return int((decimal - 1) * 100)
    else:
        return int(-100 / (decimal - 1))

def calculate_ev(offered_odds, fair_probability):
    """Calculate expected value as a percentage"""
    decimal_odds = american_to_decimal(offered_odds)
    ev = (decimal_odds * fair_probability) - 1
    return ev * 100

def remove_vig_power(over_odds, under_odds, power=2.0):
    """Remove vig using power method - more accurate for finding true probabilities"""
    over_decimal = american_to_decimal(over_odds)
    under_decimal = american_to_decimal(under_odds)
    
    over_implied = 1 / over_decimal
    under_implied = 1 / under_decimal
    
    # Calculate fair probabilities using power method
    total = (over_implied ** power + under_implied ** power) ** (1/power)
    
    fair_over_prob = (over_implied ** power) / (over_implied ** power + under_implied ** power)
    fair_under_prob = (under_implied ** power) / (over_implied ** power + under_implied ** power)
    
    return fair_over_prob, fair_under_prob

def calculate_consensus_fair_odds(bookmakers):
    """Calculate consensus fair odds by averaging across all books"""
    if not bookmakers:
        return None, None
    
    all_over_probs = []
    all_under_probs = []
    
    for book in bookmakers:
        fair_over, fair_under = remove_vig_power(book['over_odds'], book['under_odds'])
        all_over_probs.append(fair_over)
        all_under_probs.append(fair_under)
    
    # Average the fair probabilities
    avg_over_prob = sum(all_over_probs) / len(all_over_probs)
    avg_under_prob = sum(all_under_probs) / len(all_under_probs)
    
    # Normalize to ensure they sum to 1
    total = avg_over_prob + avg_under_prob
    avg_over_prob = avg_over_prob / total
    avg_under_prob = avg_under_prob / total
    
    return avg_over_prob, avg_under_prob

def group_props_by_player_and_market(props, min_ev=0.5):
    """Group props by player and market, calculate edges, show plays above min_ev threshold"""
    grouped = {}
    
    for prop in props:
        key = (prop['player'], prop['market'], prop['line'])
        if key not in grouped:
            grouped[key] = {
                'player': prop['player'],
                'market': prop['market'],
                'line': prop['line'],
                'game': prop['game'],
                'commence_time': prop['commence_time'],
                'bookmakers': []
            }
        
        grouped[key]['bookmakers'].append({
            'name': prop['bookmaker'],
            'over_odds': prop['over_odds'],
            'under_odds': prop['under_odds']
        })
    
    # Now calculate edges for each prop
    edge_plays = []
    
    for key, prop_data in grouped.items():
        # Calculate consensus fair odds from all books
        fair_over_prob, fair_under_prob = calculate_consensus_fair_odds(prop_data['bookmakers'])
        
        if fair_over_prob is None:
            continue
        
        # Find the lowest vig market for reference
        best_vig = float('inf')
        for book in prop_data['bookmakers']:
            over_decimal = american_to_decimal(book['over_odds'])
            under_decimal = american_to_decimal(book['under_odds'])
            total_implied = (1/over_decimal) + (1/under_decimal)
            vig = (total_implied - 1) * 100
            if vig < best_vig:
                best_vig = vig
        
        # Check each bookmaker for edges
        for book in prop_data['bookmakers']:
            over_ev = calculate_ev(book['over_odds'], fair_over_prob)
            under_ev = calculate_ev(book['under_odds'], fair_under_prob)
            
            # If either side meets the minimum EV threshold, add it
            if over_ev >= min_ev:
                edge_plays.append({
                    'player': prop_data['player'],
                    'market': prop_data['market'],
                    'line': prop_data['line'],
                    'game': prop_data['game'],
                    'commence_time': prop_data['commence_time'],
                    'bookmaker': book['name'],
                    'side': 'OVER',
                    'odds': book['over_odds'],
                    'fair_odds': decimal_to_american(1 / fair_over_prob),
                    'ev': over_ev,
                    'fair_prob': fair_over_prob * 100,
                    'implied_prob': calculate_implied_probability(book['over_odds']),
                    'market_vig': best_vig
                })
            
            if under_ev >= min_ev:
                edge_plays.append({
                    'player': prop_data['player'],
                    'market': prop_data['market'],
                    'line': prop_data['line'],
                    'game': prop_data['game'],
                    'commence_time': prop_data['commence_time'],
                    'bookmaker': book['name'],
                    'side': 'UNDER',
                    'odds': book['under_odds'],
                    'fair_odds': decimal_to_american(1 / fair_under_prob),
                    'ev': under_ev,
                    'fair_prob': fair_under_prob * 100,
                    'implied_prob': calculate_implied_probability(book['under_odds']),
                    'market_vig': best_vig
                })
    
    # Sort by EV% (highest first)
    edge_plays.sort(key=lambda x: x['ev'], reverse=True)
    
    return edge_plays

def calculate_implied_probability(odds):
    """Calculate implied probability from American odds"""
    if odds > 0:
        return 100 / (odds + 100) * 100
    else:
        return abs(odds) / (abs(odds) + 100) * 100

def find_best_odds(bookmakers, side='over'):
    """Find the best odds for a given side"""
    odds_key = 'over_odds' if side == 'over' else 'under_odds'
    best_book = None
    best_odds = -10000  # Start with worst possible
    
    for book in bookmakers:
        odds = book[odds_key]
        if odds > best_odds:
            best_odds = odds
            best_book = book['name']
    
    return best_book, best_odds

def format_odds(odds):
    """Format odds with + for positive odds"""
    return f"+{odds}" if odds > 0 else str(odds)

def generate_html(edge_plays):
    """Generate HTML dashboard showing only +EV plays"""
    
    # Get current time
    et = pytz.timezone('US/Eastern')
    current_time = datetime.now(et).strftime('%B %d, %Y at %I:%M %p ET')
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Player Props - Plus EV Plays</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(212, 175, 55, 0.3);
        }}
        
        .header h1 {{
            color: #d4af37;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
        }}
        
        .header .subtitle {{
            color: #4caf50;
            font-size: 1.2em;
            margin-top: 10px;
            font-weight: bold;
        }}
        
        .header .timestamp {{
            color: #888;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        
        .header .explanation {{
            color: #b8b8b8;
            font-size: 0.95em;
            margin-top: 15px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
            line-height: 1.5;
        }}
        
        .props-container {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
            gap: 20px;
        }}
        
        .prop-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            border: 2px solid rgba(76, 175, 80, 0.3);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        
        .prop-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(76, 175, 80, 0.6);
            box-shadow: 0 8px 25px rgba(76, 175, 80, 0.3);
        }}
        
        .prop-card.hardrock {{
            border: 2px solid #d4af37;
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.1) 0%, rgba(212, 175, 55, 0.05) 100%);
        }}
        
        .prop-card.hardrock:hover {{
            border-color: #d4af37;
            box-shadow: 0 8px 25px rgba(212, 175, 55, 0.4);
        }}
        
        .ev-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
        }}
        
        .hardrock .ev-badge {{
            background: linear-gradient(135deg, #d4af37 0%, #c5a028 100%);
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
        }}
        
        .bookmaker-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.9em;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .hardrock .bookmaker-badge {{
            background: rgba(212, 175, 55, 0.2);
            color: #d4af37;
        }}
        
        .hardrock .bookmaker-badge::after {{
            content: " ⭐ MUST PLAY";
            font-weight: bold;
        }}
        
        .player-name {{
            color: #d4af37;
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .market-info {{
            color: #b8b8b8;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        
        .play-info {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 15px 0;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            border-left: 4px solid #4caf50;
        }}
        
        .hardrock .play-info {{
            border-left-color: #d4af37;
        }}
        
        .side-badge {{
            background: #4caf50;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .side-badge.under {{
            background: #2196f3;
        }}
        
        .line-display {{
            font-size: 1.3em;
            font-weight: bold;
            color: #fff;
        }}
        
        .odds-display {{
            font-size: 1.4em;
            font-weight: bold;
            color: #4caf50;
        }}
        
        .hardrock .odds-display {{
            color: #d4af37;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }}
        
        .stat-box {{
            background: rgba(255, 255, 255, 0.03);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat-label {{
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
            text-transform: uppercase;
        }}
        
        .stat-value {{
            color: #fff;
            font-size: 1.1em;
            font-weight: bold;
        }}
        
        .stat-value.positive {{
            color: #4caf50;
        }}
        
        .game-info {{
            color: #888;
            font-size: 0.9em;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stats-summary {{
            text-align: center;
            margin: 30px auto;
            padding: 25px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            max-width: 800px;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }}
        
        .stats-row {{
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
        }}
        
        .summary-stat {{
            flex: 1;
            padding: 15px;
        }}
        
        .summary-label {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .summary-value {{
            color: #4caf50;
            font-size: 2em;
            font-weight: bold;
        }}
        
        .no-plays {{
            text-align: center;
            padding: 60px 20px;
            color: #888;
            font-size: 1.2em;
        }}
        
        @media (max-width: 768px) {{
            .props-container {{
                grid-template-columns: 1fr;
            }}
            
            .comparison-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏀 NBA PLAYER PROPS</h1>
        <div class="subtitle">✅ PLUS EV PLAYS ONLY</div>
        <div class="timestamp">Last Updated: {current_time}</div>
        <div class="explanation">
            Showing plays with positive expected value (minimum 0.5% EV). 
            Fair odds calculated using consensus devigging across all available bookmakers.
            EV% represents your expected profit per dollar wagered over the long term.
        </div>
    </div>
"""
    
    if not edge_plays:
        html += """
    <div class="no-plays">
        <h2>No +EV plays found at this time</h2>
        <p style="margin-top: 10px;">Check back later or adjust your parameters</p>
    </div>
"""
    else:
        # Calculate stats
        total_plays = len(edge_plays)
        avg_ev = sum(play['ev'] for play in edge_plays) / total_plays
        max_ev = max(play['ev'] for play in edge_plays)
        hardrock_plays = len([p for p in edge_plays if 'Hard Rock' in p['bookmaker']])
        
        html += f"""
    <div class="stats-summary">
        <div class="stats-row">
            <div class="summary-stat">
                <div class="summary-label">Total +EV Plays</div>
                <div class="summary-value">{total_plays}</div>
            </div>
            <div class="summary-stat">
                <div class="summary-label">Avg EV</div>
                <div class="summary-value">{avg_ev:.2f}%</div>
            </div>
            <div class="summary-stat">
                <div class="summary-label">Best EV</div>
                <div class="summary-value">{max_ev:.2f}%</div>
            </div>
            <div class="summary-stat">
                <div class="summary-label">Hard Rock Plays</div>
                <div class="summary-value">{hardrock_plays}</div>
            </div>
        </div>
    </div>
    
    <div class="props-container">
"""
        
        for play in edge_plays:
            is_hardrock = 'Hard Rock' in play['bookmaker']
            hardrock_class = 'hardrock' if is_hardrock else ''
            side_class = 'under' if play['side'] == 'UNDER' else ''
            
            odds_sign = '+' if play['odds'] > 0 else ''
            fair_odds_sign = '+' if play['fair_odds'] > 0 else ''
            
            html += f"""
        <div class="prop-card {hardrock_class}">
            <div class="ev-badge">+{play['ev']:.2f}% EV</div>
            <div class="bookmaker-badge">{play['bookmaker']}</div>
            
            <div class="player-name">{play['player']}</div>
            <div class="market-info">{play['market']}</div>
            
            <div class="play-info">
                <div class="side-badge {side_class}">{play['side']}</div>
                <div class="line-display">{play['line']}</div>
                <div class="odds-display">{odds_sign}{play['odds']}</div>
            </div>
            
            <div class="comparison-grid">
                <div class="stat-box">
                    <div class="stat-label">Your Odds</div>
                    <div class="stat-value positive">{odds_sign}{play['odds']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Fair Odds</div>
                    <div class="stat-value">{fair_odds_sign}{play['fair_odds']}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Implied Prob</div>
                    <div class="stat-value">{play['implied_prob']:.1f}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Fair Prob</div>
                    <div class="stat-value">{play['fair_prob']:.1f}%</div>
                </div>
            </div>
            
            <div class="game-info">
                {play['game']} • Market Vig: {play['market_vig']:.2f}%
            </div>
        </div>
"""
        
        html += """
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    return html
    """Generate HTML dashboard showing all bookmakers"""
    
    # Get current time
    et = pytz.timezone('US/Eastern')
    current_time = datetime.now(et).strftime('%B %d, %Y at %I:%M %p ET')
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Player Props - All Bookmakers</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(212, 175, 55, 0.3);
        }}
        
        .header h1 {{
            color: #d4af37;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
        }}
        
        .header .subtitle {{
            color: #b8b8b8;
            font-size: 1.1em;
            margin-top: 10px;
        }}
        
        .header .timestamp {{
            color: #888;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        
        .props-container {{
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 20px;
        }}
        
        .prop-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(212, 175, 55, 0.2);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        
        .prop-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(212, 175, 55, 0.5);
            box-shadow: 0 8px 25px rgba(212, 175, 55, 0.2);
        }}
        
        .prop-header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
        }}
        
        .player-name {{
            color: #d4af37;
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .market-info {{
            color: #b8b8b8;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        
        .line {{
            color: #fff;
            font-size: 1.3em;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .game-info {{
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .bookmakers-section {{
            margin-top: 15px;
        }}
        
        .bookmaker-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            margin-bottom: 10px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .bookmaker-row.hardrock {{
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(212, 175, 55, 0.05) 100%);
            border: 2px solid #d4af37;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
        }}
        
        .bookmaker-name {{
            color: #fff;
            font-weight: 600;
            font-size: 1em;
            flex: 1;
        }}
        
        .hardrock .bookmaker-name {{
            color: #d4af37;
            font-size: 1.1em;
        }}
        
        .hardrock .bookmaker-name::after {{
            content: " ⭐ MUST PLAY";
            font-size: 0.75em;
            color: #d4af37;
            margin-left: 8px;
            font-weight: bold;
        }}
        
        .odds-container {{
            display: flex;
            gap: 15px;
        }}
        
        .odds-box {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 8px 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            min-width: 80px;
        }}
        
        .odds-label {{
            color: #888;
            font-size: 0.75em;
            margin-bottom: 3px;
            text-transform: uppercase;
        }}
        
        .odds-value {{
            color: #fff;
            font-size: 1.1em;
            font-weight: bold;
        }}
        
        .odds-value.positive {{
            color: #4caf50;
        }}
        
        .odds-value.negative {{
            color: #ff6b6b;
        }}
        
        .hardrock .odds-value {{
            color: #d4af37;
            font-size: 1.2em;
        }}
        
        .best-odds {{
            border: 2px solid #4caf50;
            background: rgba(76, 175, 80, 0.1);
        }}
        
        .implied-prob {{
            color: #888;
            font-size: 0.8em;
            margin-top: 3px;
        }}
        
        .stats-summary {{
            text-align: center;
            margin: 30px auto;
            padding: 25px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            max-width: 800px;
            border: 1px solid rgba(212, 175, 55, 0.3);
        }}
        
        .stats-row {{
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
        }}
        
        .stat-box {{
            flex: 1;
            padding: 15px;
        }}
        
        .stat-label {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            color: #d4af37;
            font-size: 2em;
            font-weight: bold;
        }}
        
        @media (max-width: 768px) {{
            .props-container {{
                grid-template-columns: 1fr;
            }}
            
            .bookmaker-row {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .odds-container {{
                width: 100%;
                justify-content: space-around;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏀 NBA PLAYER PROPS</h1>
        <div class="subtitle">All Bookmakers - Shop for the Best Price</div>
        <div class="timestamp">Last Updated: {current_time}</div>
    </div>
"""
    
    # Calculate stats
    total_props = len(grouped_props)
    total_bookmakers = len(set(book['name'] for prop in grouped_props for book in prop['bookmakers']))
    total_players = len(set(prop['player'] for prop in grouped_props))
    
    html += f"""
    <div class="stats-summary">
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-label">Total Props</div>
                <div class="stat-value">{total_props}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Players</div>
                <div class="stat-value">{total_players}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Bookmakers</div>
                <div class="stat-value">{total_bookmakers}</div>
            </div>
        </div>
    </div>
    
    <div class="props-container">
"""
    
    for prop in grouped_props:
        # Find best odds for highlighting
        best_over_book, best_over_odds = find_best_odds(prop['bookmakers'], 'over')
        best_under_book, best_under_odds = find_best_odds(prop['bookmakers'], 'under')
        
        # Sort bookmakers - Hard Rock first, then alphabetically
        sorted_books = sorted(prop['bookmakers'], key=lambda x: (
            0 if 'Hard Rock' in x['name'] else 1,
            x['name']
        ))
        
        html += f"""
        <div class="prop-card">
            <div class="prop-header">
                <div class="player-name">{prop['player']}</div>
                <div class="market-info">{prop['market']}</div>
                <div class="line">Line: {prop['line']}</div>
                <div class="game-info">{prop['game']}</div>
            </div>
            
            <div class="bookmakers-section">
"""
        
        for book in sorted_books:
            is_hardrock = 'Hard Rock' in book['name']
            hardrock_class = 'hardrock' if is_hardrock else ''
            
            over_is_best = book['name'] == best_over_book
            under_is_best = book['name'] == best_under_book
            
            over_class = 'best-odds' if over_is_best and not is_hardrock else ''
            under_class = 'best-odds' if under_is_best and not is_hardrock else ''
            
            over_sign = '+' if book['over_odds'] > 0 else ''
            under_sign = '+' if book['under_odds'] > 0 else ''
            
            over_color = 'positive' if book['over_odds'] > 0 else 'negative'
            under_color = 'positive' if book['under_odds'] > 0 else 'negative'
            
            over_prob = calculate_implied_probability(book['over_odds'])
            under_prob = calculate_implied_probability(book['under_odds'])
            
            html += f"""
                <div class="bookmaker-row {hardrock_class}">
                    <div class="bookmaker-name">{book['name']}</div>
                    <div class="odds-container">
                        <div class="odds-box {over_class}">
                            <div class="odds-label">Over</div>
                            <div class="odds-value {over_color}">{over_sign}{book['over_odds']}</div>
                            <div class="implied-prob">{over_prob:.1f}%</div>
                        </div>
                        <div class="odds-box {under_class}">
                            <div class="odds-label">Under</div>
                            <div class="odds-value {under_color}">{under_sign}{book['under_odds']}</div>
                            <div class="implied-prob">{under_prob:.1f}%</div>
                        </div>
                    </div>
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html

def main():
    print("Fetching NBA Player Props from The Odds API...")
    print("=" * 60)
    
    # Configurable minimum EV threshold (in percentage points)
    MIN_EV_THRESHOLD = 0.5  # Show plays with at least 0.5% edge
    
    # Fetch events
    events = get_player_props()
    if not events:
        print("No events found")
        return
    
    print(f"Found {len(events)} NBA games")
    
    # Process props
    print("Processing player props...")
    all_props = process_props(events)
    
    if not all_props:
        print("No player props found")
        return
    
    print(f"Found {len(all_props)} total prop offerings")
    
    # Count unique props
    unique_props = set((p['player'], p['market'], p['line']) for p in all_props)
    print(f"Analyzing {len(unique_props)} unique props across all books")
    
    # Find edge plays
    print(f"Calculating edges (minimum EV threshold: {MIN_EV_THRESHOLD}%)...")
    edge_plays = group_props_by_player_and_market(all_props, min_ev=MIN_EV_THRESHOLD)
    
    if edge_plays:
        print(f"\n✅ Found {len(edge_plays)} +EV plays!")
        avg_ev = sum(play['ev'] for play in edge_plays) / len(edge_plays)
        max_ev = max(play['ev'] for play in edge_plays)
        hardrock_plays = len([p for p in edge_plays if 'Hard Rock' in p['bookmaker']])
        print(f"📊 Average EV: +{avg_ev:.2f}%")
        print(f"🎯 Best EV: +{max_ev:.2f}%")
        print(f"⭐ Hard Rock plays: {hardrock_plays}")
        
        # Show top 5 plays
        print(f"\n🔥 Top 5 Plays:")
        for i, play in enumerate(edge_plays[:5], 1):
            print(f"  {i}. {play['player']} {play['market']} {play['side']} {play['line']} @ {play['bookmaker']} (+{play['ev']:.2f}% EV)")
    else:
        print(f"\n⚠️ No plays found above {MIN_EV_THRESHOLD}% EV threshold")
        print("Try lowering MIN_EV_THRESHOLD in the script if you want to see smaller edges")
    
    # Generate HTML
    html_content = generate_html(edge_plays)
    
    # Save to file
    output_file = 'nba_player_props_all_books.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard generated successfully!")
    print(f"📁 Saved to: {output_file}")

if __name__ == "__main__":
    main()