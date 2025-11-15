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

def group_props_by_player_and_market(props):
    """Group props by player and market, showing all bookmakers"""
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
    
    # Convert to list and sort
    result = list(grouped.values())
    result.sort(key=lambda x: (x['player'], x['market']))
    
    return result

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

def generate_html(grouped_props):
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
    
    # Group by player and market
    grouped_props = group_props_by_player_and_market(all_props)
    print(f"Organized into {len(grouped_props)} unique props")
    
    # Generate HTML
    html_content = generate_html(grouped_props)
    
    # Save to file
    output_file = '/mnt/user-data/outputs/nba_player_props_all_books.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard generated successfully!")
    print(f"📊 Total unique props: {len(grouped_props)}")
    print(f"👥 Total players: {len(set(prop['player'] for prop in grouped_props))}")
    print(f"📚 Total bookmaker offerings: {len(all_props)}")
    print(f"📁 Saved to: {output_file}")

if __name__ == "__main__":
    main()