#!/usr/bin/env python3
"""
Best Plays Aggregator Bot
-------------------------
Scans all models, analyzes historical performance, and ranks upcoming plays.
Outputs TOP 20 best plays to bet in a styled HTML.

Run: python3 best_plays_bot.py
Output: best_plays.html
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "best_plays.html")

# Timezone
ET = pytz.timezone('US/Eastern')
NOW = datetime.now(ET)
TODAY = NOW.strftime('%Y-%m-%d')

# All tracking files to scan
TRACKING_SOURCES = [
    # (Name, File Path, Sport, Bet Category)
    ('NBA Points Props', 'nba/nba_points_props_tracking.json', 'NBA', 'Props'),
    ('NBA Assists Props', 'nba/nba_assists_props_tracking.json', 'NBA', 'Props'),
    ('NBA Rebounds Props', 'nba/nba_rebounds_props_tracking.json', 'NBA', 'Props'),
    ('NBA 3PT Props', 'nba/nba_3pt_props_tracking.json', 'NBA', 'Props'),
    ('NFL Passing Yards', 'nfl/nfl_passing_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Rushing Yards', 'nfl/nfl_rushing_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Receiving Yards', 'nfl/nfl_receiving_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Receptions', 'nfl/nfl_receptions_props_tracking.json', 'NFL', 'Props'),
    ('NBA Main', 'nba/nba_picks_tracking.json', 'NBA', 'Spread/Total'),
    ('NFL Main', 'nfl/nfl_picks_tracking.json', 'NFL', 'Spread/Total'),
    ('NCAAB', 'ncaa/ncaab_picks_tracking.json', 'NCAAB', 'Spread/Total'),
    ('Soccer', 'soccer/soccer_picks_tracking.json', 'Soccer', 'Total'),
]


def load_tracking_data(filepath):
    """Load tracking data from JSON file"""
    full_path = os.path.join(SCRIPT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
        return data.get('picks', []) if isinstance(data, dict) else data
    except:
        return []


def calculate_model_stats(picks):
    """Calculate win rate and recent form for a model"""
    graded = [p for p in picks if p.get('status', '').lower() in ['win', 'won', 'loss', 'lost']]
    wins = sum(1 for p in graded if p.get('status', '').lower() in ['win', 'won'])
    losses = sum(1 for p in graded if p.get('status', '').lower() in ['loss', 'lost'])
    total = wins + losses
    
    win_rate = (wins / total * 100) if total > 0 else 50.0
    
    # Recent form (last 10)
    recent = graded[-10:] if len(graded) >= 10 else graded
    recent_wins = sum(1 for p in recent if p.get('status', '').lower() in ['win', 'won'])
    recent_total = len(recent)
    recent_rate = (recent_wins / recent_total * 100) if recent_total > 0 else 50.0
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate,
        'recent_rate': recent_rate,
        'record': f"{wins}-{losses}"
    }


def calculate_bet_type_stats(picks, bet_type):
    """Calculate win rate for a specific bet type (OVER/UNDER/Spread)"""
    bt = bet_type.lower()
    filtered = [p for p in picks if bt in p.get('bet_type', '').lower() or bt in p.get('pick_type', '').lower()]
    graded = [p for p in filtered if p.get('status', '').lower() in ['win', 'won', 'loss', 'lost']]
    wins = sum(1 for p in graded if p.get('status', '').lower() in ['win', 'won'])
    total = len(graded)
    
    return (wins / total * 100) if total > 0 else 50.0


def parse_game_time(game_time_str):
    """Parse game time string to datetime in ET"""
    if not game_time_str:
        return None
    try:
        if 'Z' in game_time_str:
            dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(game_time_str)
        return dt.astimezone(ET)
    except:
        return None


def calculate_confidence_score(play, model_stats, bet_type_rate):
    """
    Calculate composite confidence score (0-100)
    
    Weights:
    - Model Win Rate: 30%
    - Bet Type Win Rate: 25%
    - AI Score: 20%
    - Edge: 15%
    - Recent Form: 10%
    """
    # Model win rate (0-100) -> scaled to 0-30
    model_score = (model_stats['win_rate'] / 100) * 30
    
    # Bet type win rate (0-100) -> scaled to 0-25
    bet_type_score = (bet_type_rate / 100) * 25
    
    # AI Score (typically 8-10) -> scaled to 0-20
    ai_score = play.get('ai_score', 8.0)
    ai_component = ((ai_score - 7) / 3) * 20  # 7=0, 10=20
    ai_component = max(0, min(20, ai_component))
    
    # Edge (varies by model) -> scaled to 0-15
    edge = abs(play.get('edge', 0))
    # Normalize edge: props typically 1-5, spreads 5-15
    if edge > 0:
        edge_normalized = min(edge / 10, 1.0)  # Cap at 10 points of edge
        edge_component = edge_normalized * 15
    else:
        edge_component = 5  # Neutral if no edge data
    
    # Recent form -> scaled to 0-10
    recent_score = (model_stats['recent_rate'] / 100) * 10
    
    # Total
    total = model_score + bet_type_score + ai_component + edge_component + recent_score
    
    return round(min(100, max(0, total)), 1)


def get_pending_plays():
    """Gather all pending plays from all models with confidence scores"""
    all_plays = []
    
    for model_name, filepath, sport, category in TRACKING_SOURCES:
        picks = load_tracking_data(filepath)
        if not picks:
            continue
        
        # Calculate model stats
        model_stats = calculate_model_stats(picks)
        
        # Get pending plays
        pending = [p for p in picks if p.get('status', 'pending').lower() == 'pending']
        
        for p in pending:
            # Parse game time - only include future games
            game_time = parse_game_time(p.get('game_time') or p.get('game_date'))
            if game_time and game_time < NOW:
                continue  # Skip past games
            
            # Get bet type
            bet_type = p.get('bet_type', p.get('pick_type', 'unknown'))
            bet_type_rate = calculate_bet_type_stats(picks, bet_type)
            
            # Calculate confidence score
            confidence = calculate_confidence_score(p, model_stats, bet_type_rate)
            
            # Build play object
            play = {
                'model': model_name,
                'sport': sport,
                'category': category,
                'player': p.get('player', p.get('team', 'Unknown')),
                'bet_type': bet_type.upper() if bet_type else 'N/A',
                'line': p.get('prop_line', p.get('line', '')),
                'odds': p.get('odds', '-110'),
                'edge': p.get('edge', 0),
                'ai_score': p.get('ai_score', 0),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p') if game_time else 'TBD',
                'matchup': p.get('matchup', p.get('opponent', '')),
                'model_record': model_stats['record'],
                'model_win_rate': model_stats['win_rate'],
                'confidence': confidence,
            }
            all_plays.append(play)
    
    # Sort by confidence score (highest first)
    all_plays.sort(key=lambda x: x['confidence'], reverse=True)
    
    return all_plays


def get_confidence_tier(score):
    """Get tier label and color based on confidence score"""
    if score >= 80:
        return '🔥 FIRE', '#ff6b35'
    elif score >= 65:
        return '✅ SOLID', '#4ade80'
    elif score >= 50:
        return '⚡ VALUE', '#60a5fa'
    else:
        return '📊 PLAY', '#8e8e93'


def generate_html(plays):
    """Generate styled HTML output"""
    # Show up to 50 plays (or all if less than 50)
    top_plays = plays[:50]
    timestamp = NOW.strftime('%Y-%m-%d %I:%M %p ET')
    
    # Build play cards HTML
    play_cards = ""
    for i, play in enumerate(top_plays, 1):
        tier_label, tier_color = get_confidence_tier(play['confidence'])
        
        # Format bet display
        if play['line']:
            bet_display = f"{play['bet_type']} {play['line']}"
        else:
            bet_display = play['bet_type']
        
        # Format edge
        edge_display = f"+{play['edge']:.1f}" if play['edge'] > 0 else f"{play['edge']:.1f}"
        
        play_cards += f'''
        <div class="play-card">
            <div class="play-rank" style="background: {tier_color};">#{i}</div>
            <div class="play-content">
                <div class="play-header">
                    <div class="play-score" style="color: {tier_color};">{play['confidence']}</div>
                    <div class="play-tier">{tier_label}</div>
                </div>
                <div class="play-main">
                    <div class="play-player">{play['player']}</div>
                    <div class="play-bet">{bet_display}</div>
                </div>
                <div class="play-meta">
                    <span class="meta-tag">{play['sport']}</span>
                    <span class="meta-tag">{play['model']}</span>
                    <span class="meta-tag">{play['game_time_str']}</span>
                </div>
                <div class="play-stats">
                    <div class="stat">
                        <span class="stat-label">Model Record</span>
                        <span class="stat-value">{play['model_record']} ({play['model_win_rate']:.1f}%)</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Edge</span>
                        <span class="stat-value">{edge_display}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">AI Score</span>
                        <span class="stat-value">{play['ai_score']:.1f}</span>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Best Plays • CourtSide Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0a0a0a;
            --bg-card: #141414;
            --bg-card-hover: #1a1a1a;
            --text-primary: #ffffff;
            --text-secondary: #8e8e93;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --accent-orange: #ff6b35;
            --border-color: #2a2a2a;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-main);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem 1rem;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #4ade80, #60a5fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
        }}
        
        .timestamp {{
            display: inline-block;
            background: var(--bg-card);
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-size: 0.85rem;
            margin-top: 1rem;
        }}
        
        .plays-grid {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        
        .play-card {{
            display: flex;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            transition: transform 0.2s, border-color 0.2s;
        }}
        
        .play-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-green);
        }}
        
        .play-rank {{
            width: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.1rem;
            color: #000;
        }}
        
        .play-content {{
            flex: 1;
            padding: 1rem;
        }}
        
        .play-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}
        
        .play-score {{
            font-size: 1.5rem;
            font-weight: 800;
        }}
        
        .play-tier {{
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
        }}
        
        .play-main {{
            margin-bottom: 0.75rem;
        }}
        
        .play-player {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        
        .play-bet {{
            font-size: 1rem;
            color: var(--accent-green);
            font-weight: 600;
        }}
        
        .play-meta {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 0.75rem;
        }}
        
        .meta-tag {{
            background: var(--bg-main);
            color: var(--text-secondary);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        
        .play-stats {{
            display: flex;
            gap: 1.5rem;
        }}
        
        .stat {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }}
        
        .stat-value {{
            font-size: 0.9rem;
            font-weight: 600;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }}
        
        @media (max-width: 600px) {{
            h1 {{ font-size: 1.8rem; }}
            .play-stats {{ flex-wrap: wrap; gap: 1rem; }}
            .play-rank {{ width: 40px; font-size: 0.9rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Best Plays</h1>
            <div class="subtitle">Top 50 Highest Confidence Bets Across All Models</div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>
        
        <div class="plays-grid">
            {play_cards if play_cards else '<div class="empty-state">No pending plays found. Check back after models run.</div>'}
        </div>
    </div>
</body>
</html>'''
    
    return html


def main():
    print("🎯 Best Plays Aggregator")
    print("=" * 50)
    
    # Get all pending plays with scores
    print("📊 Scanning all models...")
    plays = get_pending_plays()
    print(f"   Found {len(plays)} pending plays across all models")
    
    # Generate HTML
    print("📄 Generating HTML...")
    html = generate_html(plays)
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    
    print(f"✅ Created: {OUTPUT_HTML}")
    
    # Show top 5 in console
    if plays:
        print("\n🔥 TOP 5 PLAYS:")
        print("-" * 50)
        for i, p in enumerate(plays[:5], 1):
            print(f"  #{i} [{p['confidence']:.0f}] {p['player']} {p['bet_type']} {p['line']}")
            print(f"      {p['model']} ({p['model_record']})")
    
    return len(plays)


if __name__ == "__main__":
    main()
