import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import os

class NBAPlayerPropModel:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def get_nba_events(self):
        """Fetch upcoming NBA events/games"""
        url = f"{self.base_url}/sports/basketball_nba/events"
        params = {
            'apiKey': self.api_key,
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            events = response.json()
            print(f"✅ Found {len(events)} NBA games")
            print(f"📊 Remaining API requests: {response.headers.get('x-requests-remaining', 'Unknown')}")
            return events
        except Exception as e:
            print(f"❌ Error fetching NBA events: {e}")
            return []
    
    def get_event_odds(self, event_id):
        """Fetch odds for a specific event including player props"""
        url = f"{self.base_url}/sports/basketball_nba/events/{event_id}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,spreads,totals',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Could not fetch props for event {event_id}: {e}")
            return None
    
    def analyze_prop(self, player_name, prop_type, line, over_odds, under_odds, bookmaker, game_info):
        """Analyze a player prop and generate recommendation"""
        
        # Prop type analysis factors
        analysis = {
            'player': player_name,
            'prop_type': prop_type,
            'line': line,
            'over_odds': over_odds,
            'under_odds': under_odds,
            'bookmaker': bookmaker,
            'is_hard_rock': 'hard' in bookmaker.lower() and 'rock' in bookmaker.lower(),
            'game_info': game_info,
            'confidence': 0,
            'recommendation': 'PASS',
            'edge': 0,
            'reasoning': []
        }
        
        # Convert American odds to implied probability
        def american_to_implied_prob(odds):
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        
        over_prob = american_to_implied_prob(over_odds) if over_odds else 0.5
        under_prob = american_to_implied_prob(under_odds) if under_odds else 0.5
        
        # Calculate true probability (removing vig)
        true_over_prob = over_prob / (over_prob + under_prob)
        true_under_prob = under_prob / (over_prob + under_prob)
        
        # Value threshold (look for 5%+ edge)
        value_threshold = 0.05
        
        # Analyze based on prop type
        if 'points' in prop_type.lower():
            # Points analysis
            if line < 15:
                analysis['reasoning'].append("Lower scoring prop - check recent minutes")
                target_prob = 0.56  # Target 56% for lower variance
            elif line < 25:
                analysis['reasoning'].append("Mid-range scorer prop")
                target_prob = 0.57
            else:
                analysis['reasoning'].append("High scoring prop - star player")
                target_prob = 0.58
                
        elif 'rebound' in prop_type.lower():
            # Rebounds analysis
            if line < 5:
                analysis['reasoning'].append("Low rebound total - likely guard")
                target_prob = 0.55
            elif line < 10:
                analysis['reasoning'].append("Mid-range rebounds - wing/forward")
                target_prob = 0.56
            else:
                analysis['reasoning'].append("High rebound total - big man")
                target_prob = 0.57
                
        elif 'assist' in prop_type.lower():
            # Assists analysis
            if line < 3:
                analysis['reasoning'].append("Low assist total - off-ball player")
                target_prob = 0.55
            elif line < 7:
                analysis['reasoning'].append("Mid-range assists - secondary playmaker")
                target_prob = 0.56
            else:
                analysis['reasoning'].append("High assist total - primary ball handler")
                target_prob = 0.57
                
        elif 'three' in prop_type.lower():
            # Three-pointers analysis
            if line < 2:
                analysis['reasoning'].append("Low 3PT total - not a primary shooter")
                target_prob = 0.54
            elif line < 4:
                analysis['reasoning'].append("Mid-range 3PT - volume shooter")
                target_prob = 0.56
            else:
                analysis['reasoning'].append("High 3PT total - elite shooter")
                target_prob = 0.58
        else:
            target_prob = 0.57
        
        # Check for value on OVER
        if true_over_prob < target_prob:
            edge = target_prob - over_prob
            if edge > value_threshold:
                analysis['recommendation'] = 'OVER'
                analysis['confidence'] = min(int(edge * 200), 100)
                analysis['edge'] = round(edge * 100, 1)
                analysis['reasoning'].append(f"Strong value on OVER: {analysis['edge']}% edge vs book")
        
        # Check for value on UNDER
        elif true_under_prob < target_prob:
            edge = target_prob - under_prob
            if edge > value_threshold:
                analysis['recommendation'] = 'UNDER'
                analysis['confidence'] = min(int(edge * 200), 100)
                analysis['edge'] = round(edge * 100, 1)
                analysis['reasoning'].append(f"Strong value on UNDER: {analysis['edge']}% edge vs book")
        
        # Additional reasoning based on odds value
        if over_odds and over_odds > 110:
            analysis['reasoning'].append(f"Plus money on OVER ({over_odds})")
        if under_odds and under_odds > 110:
            analysis['reasoning'].append(f"Plus money on UNDER ({under_odds})")
            
        return analysis
    
    def process_props(self):
        """Process all player props and generate recommendations"""
        # Get all NBA events
        events = self.get_nba_events()
        
        if not events:
            print("❌ No NBA events found")
            return []
        
        recommendations = []
        processed = set()  # Avoid duplicates
        
        print(f"\n🔍 Analyzing player props across {len(events)} games...")
        
        for idx, event in enumerate(events, 1):
            event_id = event.get('id')
            home_team = event.get('home_team', 'Unknown')
            away_team = event.get('away_team', 'Unknown')
            commence_time = event.get('commence_time', '')
            
            # Format game time - convert from UTC to ET
            game_time = 'TBD'
            if commence_time:
                try:
                    from datetime import datetime, timedelta
                    
                    # Parse UTC time (API returns ISO format with Z)
                    dt_utc = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    
                    # Convert to ET
                    # EST is UTC-5, EDT is UTC-4
                    # DST ended Nov 3, 2024, so we're in EST (UTC-5) now
                    dt_et = dt_utc - timedelta(hours=5)
                    game_time = dt_et.strftime('%a %b %d, %I:%M %p ET')
                except Exception as e:
                    game_time = commence_time
            
            print(f"   {idx}. {away_team} @ {home_team}", end=" ")
            
            # Get odds for this event
            event_data = self.get_event_odds(event_id)
            
            if not event_data or 'bookmakers' not in event_data:
                print("- No props available")
                continue
            
            props_found = 0
            
            # Extract spread and total from bookmakers
            spread = None
            total = None
            
            for bookmaker in event_data.get('bookmakers', []):
                if 'markets' not in bookmaker:
                    continue
                
                for market in bookmaker['markets']:
                    if market.get('key') == 'spreads' and spread is None:
                        outcomes = market.get('outcomes', [])
                        for outcome in outcomes:
                            if outcome.get('name') == home_team:
                                spread = outcome.get('point')
                                break
                    elif market.get('key') == 'totals' and total is None:
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            total = outcomes[0].get('point')
                
                # If we found both, we can stop searching
                if spread is not None and total is not None:
                    break
            
            # Build game info object
            game_info = {
                'away_team': away_team,
                'home_team': home_team,
                'matchup': f"{away_team} @ {home_team}",
                'game_time': game_time,
                'spread': spread,
                'total': total
            }
            
            for bookmaker in event_data.get('bookmakers', []):
                if 'markets' not in bookmaker:
                    continue
                
                bookmaker_name = bookmaker.get('title', bookmaker.get('key', 'Unknown'))
                    
                for market in bookmaker['markets']:
                    market_key = market.get('key', '')
                    
                    # Process each prop type
                    if 'player' in market_key:
                        outcomes = market.get('outcomes', [])
                        
                        # Group outcomes by player
                        player_outcomes = defaultdict(list)
                        for outcome in outcomes:
                            player = outcome.get('description', '')
                            if player:
                                player_outcomes[player].append(outcome)
                        
                        # Process each player's prop
                        for player, player_outs in player_outcomes.items():
                            if len(player_outs) < 2:
                                continue
                                
                            # Find over and under
                            over_outcome = None
                            under_outcome = None
                            
                            for out in player_outs:
                                if out.get('name') == 'Over':
                                    over_outcome = out
                                elif out.get('name') == 'Under':
                                    under_outcome = out
                            
                            if over_outcome and under_outcome:
                                point = over_outcome.get('point')
                                if not point:
                                    continue
                                    
                                prop_id = f"{player}_{market_key}_{point}_{bookmaker_name}"
                                if prop_id not in processed:
                                    processed.add(prop_id)
                                    props_found += 1
                                    
                                    analysis = self.analyze_prop(
                                        player,
                                        market_key.replace('player_', '').replace('_', ' ').title(),
                                        point,
                                        over_outcome.get('price'),
                                        under_outcome.get('price'),
                                        bookmaker_name,
                                        game_info
                                    )
                                    
                                    if analysis['recommendation'] != 'PASS':
                                        recommendations.append(analysis)
            
            print(f"- {props_found} props analyzed")
        
        # Sort by confidence/edge
        recommendations.sort(key=lambda x: (x['confidence'], x['edge']), reverse=True)
        
        return recommendations
    
    def generate_html_report(self, recommendations):
        """Generate beautiful HTML report"""
        
        timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p ET')
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Player Props Model</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            border: 2px solid #d4af37;
            box-shadow: 0 10px 40px rgba(212, 175, 55, 0.3);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            color: #d4af37;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
        }}
        
        .header p {{
            color: #888;
            font-size: 0.95em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #1a1a1a 0%, #252525 100%);
            padding: 25px;
            border-radius: 15px;
            border: 1px solid #333;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            border-color: #d4af37;
            box-shadow: 0 5px 20px rgba(212, 175, 55, 0.2);
        }}
        
        .stat-card h3 {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card .value {{
            color: #d4af37;
            font-size: 2em;
            font-weight: bold;
        }}
        
        .prop-card {{
            background: linear-gradient(135deg, #1a1a1a 0%, #252525 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border: 2px solid #333;
            transition: all 0.3s ease;
        }}
        
        .prop-card:hover {{
            transform: translateY(-3px);
            border-color: #d4af37;
            box-shadow: 0 8px 25px rgba(212, 175, 55, 0.2);
        }}
        
        .prop-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .game-context {{
            background: rgba(212, 175, 55, 0.1);
            border-left: 3px solid #d4af37;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        
        .game-context-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .game-context-item label {{
            color: #888;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}
        
        .game-context-item .value {{
            color: #fff;
            font-size: 0.95em;
            font-weight: 600;
        }}
        
        .matchup-text {{
            color: #d4af37;
            font-size: 1.1em;
            font-weight: bold;
        }}
        
        .player-name {{
            font-size: 1.5em;
            font-weight: bold;
            color: #fff;
        }}
        
        .confidence {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .confidence-high {{
            background: linear-gradient(135deg, #d4af37 0%, #f4c844 100%);
            color: #000;
        }}
        
        .confidence-medium {{
            background: linear-gradient(135deg, #4a90e2 0%, #5fa3ef 100%);
            color: #fff;
        }}
        
        .bookmaker-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: #ccc;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .hard-rock-badge {{
            background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%);
            color: #fff;
            border: 2px solid #ff3333;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.4);
            animation: pulse 2s ease-in-out infinite;
        }}
        
        .must-play {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%);
            color: #fff;
            font-weight: bold;
            font-size: 0.9em;
            margin-left: 10px;
            border: 2px solid #ff3333;
            box-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
            animation: pulse 2s ease-in-out infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{
                box-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
            }}
            50% {{
                box-shadow: 0 0 25px rgba(255, 0, 0, 0.8);
            }}
        }}
        
        .hard-rock-card {{
            border: 3px solid #ff0000 !important;
            box-shadow: 0 0 30px rgba(255, 0, 0, 0.3);
        }}
        
        .hard-rock-section {{
            background: linear-gradient(135deg, #2a0a0a 0%, #3a1a1a 100%);
            border: 3px solid #ff0000;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 0 40px rgba(255, 0, 0, 0.3);
        }}
        
        .hard-rock-section h2 {{
            color: #ff3333;
            font-size: 2em;
            margin-bottom: 20px;
            text-align: center;
            text-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
        }}
        
        .prop-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .prop-detail {{
            background: rgba(255, 255, 255, 0.03);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #2a2a2a;
        }}
        
        .prop-detail label {{
            display: block;
            color: #888;
            font-size: 0.85em;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .prop-detail .value {{
            color: #fff;
            font-size: 1.2em;
            font-weight: bold;
        }}
        
        .recommendation {{
            display: inline-block;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 15px;
        }}
        
        .rec-over {{
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            color: #fff;
        }}
        
        .rec-under {{
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: #fff;
        }}
        
        .reasoning {{
            background: rgba(212, 175, 55, 0.1);
            border-left: 4px solid #d4af37;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .reasoning h4 {{
            color: #d4af37;
            margin-bottom: 10px;
            font-size: 0.95em;
        }}
        
        .reasoning ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .reasoning li {{
            padding: 5px 0;
            color: #ccc;
            font-size: 0.9em;
        }}
        
        .reasoning li:before {{
            content: "→ ";
            color: #d4af37;
            font-weight: bold;
            margin-right: 8px;
        }}
        
        .no-plays {{
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, #1a1a1a 0%, #252525 100%);
            border-radius: 15px;
            border: 2px dashed #333;
        }}
        
        .no-plays h2 {{
            color: #888;
            margin-bottom: 10px;
        }}
        
        .no-plays p {{
            color: #666;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .prop-details {{
                grid-template-columns: 1fr;
            }}
            
            .game-context {{
                grid-template-columns: 1fr;
            }}
            
            .prop-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏀 NBA Player Props Model</h1>
            <p>Sharp Analysis • Data-Driven Picks • Built for Value</p>
            <p style="margin-top: 10px;">Generated: {timestamp}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Hard Rock Must Plays</h3>
                <div class="value" style="color: #ff3333;">{len([r for r in recommendations if r['is_hard_rock']])}</div>
            </div>
            <div class="stat-card">
                <h3>Total Value Plays</h3>
                <div class="value">{len(recommendations)}</div>
            </div>
            <div class="stat-card">
                <h3>Target Win Rate</h3>
                <div class="value">56%+</div>
            </div>
            <div class="stat-card">
                <h3>Min Edge Required</h3>
                <div class="value">5%</div>
            </div>
        </div>
"""

        if recommendations:
            # Separate Hard Rock props from others
            hard_rock_props = [r for r in recommendations if r['is_hard_rock']]
            other_props = [r for r in recommendations if not r['is_hard_rock']]
            
            # Hard Rock MUST PLAY section
            if hard_rock_props:
                html += """
        <div class="hard-rock-section">
            <h2>🔥 HARD ROCK MUST PLAYS 🔥</h2>
"""
                for rec in hard_rock_props:
                    confidence_class = 'confidence-high' if rec['confidence'] >= 60 else 'confidence-medium'
                    rec_class = 'rec-over' if rec['recommendation'] == 'OVER' else 'rec-under'
                    game = rec['game_info']
                    
                    html += f"""
            <div class="prop-card hard-rock-card">
                <div class="prop-header">
                    <div class="player-name">
                        {rec['player']}
                        <span class="must-play">⚡ MUST PLAY</span>
                    </div>
                    <span class="confidence {confidence_class}">
                        {rec['confidence']}% Confidence
                    </span>
                </div>
                
                <div class="game-context">
                    <div class="game-context-item">
                        <label>Matchup</label>
                        <div class="matchup-text">{game['matchup']}</div>
                    </div>
                    <div class="game-context-item">
                        <label>Game Time</label>
                        <div class="value">{game['game_time']}</div>
                    </div>
                    <div class="game-context-item">
                        <label>Spread</label>
                        <div class="value">{game['home_team']} {'+' if game['spread'] and game['spread'] > 0 else ''}{game['spread'] if game['spread'] else 'N/A'}</div>
                    </div>
                    <div class="game-context-item">
                        <label>Total</label>
                        <div class="value">O/U {game['total'] if game['total'] else 'N/A'}</div>
                    </div>
                </div>
                
                <div class="prop-details">
                    <div class="prop-detail">
                        <label>Prop Type</label>
                        <div class="value">{rec['prop_type']}</div>
                    </div>
                    <div class="prop-detail">
                        <label>Line</label>
                        <div class="value">{rec['line']}</div>
                    </div>
                    <div class="prop-detail">
                        <label>Over Odds</label>
                        <div class="value">{'+' if rec['over_odds'] > 0 else ''}{rec['over_odds']}</div>
                    </div>
                    <div class="prop-detail">
                        <label>Under Odds</label>
                        <div class="value">{'+' if rec['under_odds'] > 0 else ''}{rec['under_odds']}</div>
                    </div>
                </div>
                
                <div>
                    <span class="recommendation {rec_class}">
                        ⚡ BET {rec['recommendation']} {rec['line']}
                    </span>
                    <span style="color: #d4af37; font-weight: bold; margin-left: 15px;">
                        {rec['edge']}% Edge
                    </span>
                    <span class="bookmaker-badge hard-rock-badge">
                        {rec['bookmaker']}
                    </span>
                </div>
                
                <div class="reasoning">
                    <h4>📊 Analysis</h4>
                    <ul>
"""
                    for reason in rec['reasoning']:
                        html += f"                        <li>{reason}</li>\n"
                    
                    html += """                    </ul>
                </div>
            </div>
"""
                html += """
        </div>
"""
            
            # Other bookmakers section
            if other_props:
                html += """
        <h2 style="color: #d4af37; margin: 30px 0 20px 0; font-size: 1.8em;">📊 All Other Value Plays</h2>
"""
                for rec in other_props:
                    confidence_class = 'confidence-high' if rec['confidence'] >= 60 else 'confidence-medium'
                    rec_class = 'rec-over' if rec['recommendation'] == 'OVER' else 'rec-under'
                    game = rec['game_info']
                    
                    html += f"""
        <div class="prop-card">
            <div class="prop-header">
                <div class="player-name">{rec['player']}</div>
                <span class="confidence {confidence_class}">
                    {rec['confidence']}% Confidence
                </span>
            </div>
            
            <div class="game-context">
                <div class="game-context-item">
                    <label>Matchup</label>
                    <div class="matchup-text">{game['matchup']}</div>
                </div>
                <div class="game-context-item">
                    <label>Game Time</label>
                    <div class="value">{game['game_time']}</div>
                </div>
                <div class="game-context-item">
                    <label>Spread</label>
                    <div class="value">{game['home_team']} {'+' if game['spread'] and game['spread'] > 0 else ''}{game['spread'] if game['spread'] else 'N/A'}</div>
                </div>
                <div class="game-context-item">
                    <label>Total</label>
                    <div class="value">O/U {game['total'] if game['total'] else 'N/A'}</div>
                </div>
            </div>
            
            <div class="prop-details">
                <div class="prop-detail">
                    <label>Prop Type</label>
                    <div class="value">{rec['prop_type']}</div>
                </div>
                <div class="prop-detail">
                    <label>Line</label>
                    <div class="value">{rec['line']}</div>
                </div>
                <div class="prop-detail">
                    <label>Over Odds</label>
                    <div class="value">{'+' if rec['over_odds'] > 0 else ''}{rec['over_odds']}</div>
                </div>
                <div class="prop-detail">
                    <label>Under Odds</label>
                    <div class="value">{'+' if rec['under_odds'] > 0 else ''}{rec['under_odds']}</div>
                </div>
            </div>
            
            <div>
                <span class="recommendation {rec_class}">
                    ⚡ BET {rec['recommendation']} {rec['line']}
                </span>
                <span style="color: #d4af37; font-weight: bold; margin-left: 15px;">
                    {rec['edge']}% Edge
                </span>
                <span class="bookmaker-badge">
                    {rec['bookmaker']}
                </span>
            </div>
            
            <div class="reasoning">
                <h4>📊 Analysis</h4>
                <ul>
"""
                    for reason in rec['reasoning']:
                        html += f"                    <li>{reason}</li>\n"
                    
                    html += """                </ul>
            </div>
        </div>
"""
        else:
            html += """
        <div class="no-plays">
            <h2>No Value Plays Currently</h2>
            <p>The model didn't find any props with sufficient edge at this time.</p>
            <p>Check back later for updated recommendations.</p>
        </div>
"""

        html += """
        <div class="footer">
            <p><strong>Sharp NBA Player Props Model</strong></p>
            <p>Targeting 56%+ win rate • Minimum 5% edge required • All picks tracked</p>
            <p style="margin-top: 15px; font-size: 0.85em;">
                This model analyzes player props for value by calculating true probabilities after removing bookmaker vig,
                then comparing against expected performance thresholds based on prop type and line value.
            </p>
        </div>
    </div>
</body>
</html>
"""
        return html


if __name__ == "__main__":
    # Initialize model with API key
    API_KEY = "671958bc1621170701241a09d5ecc627"
    model = NBAPlayerPropModel(API_KEY)
    
    print("🏀 NBA Player Props Model")
    print("=" * 50)
    print("Fetching player props data from The Odds API...")
    print()
    
    # Process props and generate recommendations
    recommendations = model.process_props()
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Found {len(recommendations)} value plays")
    
    # Generate HTML report
    html_output = model.generate_html_report(recommendations)
    
    # Save to current directory
    output_path = "nba_player_props.html"
    with open(output_path, 'w') as f:
        f.write(html_output)
    
    print(f"\n💾 Report saved: {output_path}")
    print("\n" + "=" * 50)
    
    # Display top picks
    if recommendations:
        # Show Hard Rock must plays first
        hard_rock_props = [r for r in recommendations if r['is_hard_rock']]
        other_props = [r for r in recommendations if not r['is_hard_rock']]
        
        if hard_rock_props:
            print("\n🔥 HARD ROCK MUST PLAYS:")
            for i, rec in enumerate(hard_rock_props, 1):
                game = rec['game_info']
                print(f"\n{i}. {rec['player']} - {rec['prop_type']} ({rec['bookmaker']})")
                print(f"   {game['matchup']} | {game['game_time']}")
                if game['spread'] or game['total']:
                    spread_str = f"{game['home_team']} {'+' if game['spread'] and game['spread'] > 0 else ''}{game['spread']}" if game['spread'] else "N/A"
                    total_str = f"O/U {game['total']}" if game['total'] else "N/A"
                    print(f"   Spread: {spread_str} | Total: {total_str}")
                print(f"   Line: {rec['line']} | Bet: {rec['recommendation']}")
                print(f"   Edge: {rec['edge']}% | Confidence: {rec['confidence']}%")
                print(f"   Odds: Over {rec['over_odds']} / Under {rec['under_odds']}")
        
        if other_props:
            print("\n\n📊 OTHER TOP PLAYS:")
            for i, rec in enumerate(other_props[:5], 1):
                game = rec['game_info']
                print(f"\n{i}. {rec['player']} - {rec['prop_type']} ({rec['bookmaker']})")
                print(f"   {game['matchup']} | {game['game_time']}")
                if game['spread'] or game['total']:
                    spread_str = f"{game['home_team']} {'+' if game['spread'] and game['spread'] > 0 else ''}{game['spread']}" if game['spread'] else "N/A"
                    total_str = f"O/U {game['total']}" if game['total'] else "N/A"
                    print(f"   Spread: {spread_str} | Total: {total_str}")
                print(f"   Line: {rec['line']} | Bet: {rec['recommendation']}")
                print(f"   Edge: {rec['edge']}% | Confidence: {rec['confidence']}%")
                print(f"   Odds: Over {rec['over_odds']} / Under {rec['under_odds']}")
    else:
        print("\n⏳ No value plays found at this time")
        print("   The model requires minimum 5% edge to recommend a play")
    
    print("\n" + "=" * 50)
