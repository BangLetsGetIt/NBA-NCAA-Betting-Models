import json
import os
from collections import defaultdict
from datetime import datetime

# Configuration
BASE_DIR = "/Users/rico/sports-models"
OUTPUT_FILE = os.path.join(BASE_DIR, "auto_bet_teams.html")
MIN_PICKS = 5
MIN_WIN_RATE = 0.80

def get_tracking_files():
    files = []
    for root, _, filenames in os.walk(BASE_DIR):
        for f in filenames:
            if f.endswith('_tracking.json'):
                files.append(os.path.join(root, f))
    return files

def calculate_team_stats():
    team_stats = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'pushes': 0, 
        'profit': 0.0, 'games': [], 'sport': 'Unknown'
    })

    for file_path in get_tracking_files():
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                picks = data.get('picks', [])
                
                # Determine sport from file path or content roughly
                sport = 'Other'
                if 'nba' in file_path.lower(): sport = 'NBA'
                elif 'nfl' in file_path.lower(): sport = 'NFL'
                elif 'ncaa' in file_path.lower() or 'cbb' in file_path.lower(): sport = 'NCAAB'
                elif 'mlb' in file_path.lower(): sport = 'MLB'
                elif 'soccer' in file_path.lower(): sport = 'Soccer'
                elif 'wnba' in file_path.lower(): sport = 'WNBA'

                for p in picks:
                    # We are looking for TEAM performance, usually spread/ml/totals
                    # Only include if pick text implies betting ON the team or it's a team-based prop
                    # For simplicity, we aggregate by 'Team' name found in pick.
                    
                    # Some files have 'home_team', 'away_team', others have 'team', 'opponent'
                    # We need to know who the bet was ON.
                    
                    bet_on_team = None
                    pick_text = p.get('pick_text', '')
                    
                    # Logic to determine team:
                    if 'team' in p:
                        bet_on_team = p['team']
                    elif 'home_team' in p and 'away_team' in p:
                        # Try to find team name in pick_text
                        if p['home_team'] in pick_text:
                            bet_on_team = p['home_team']
                        elif p['away_team'] in pick_text:
                            bet_on_team = p['away_team']
                        elif 'OVER' in pick_text or 'UNDER' in pick_text:
                            # Total - maybe assign to both? Or skip for "Team" auto bet?
                            # Usually Auto Bet implies backing a team. Let's skip totals for now unless requested.
                            continue
                    
                    if not bet_on_team:
                        continue

                    status = p.get('status', '').lower()
                    if status not in ['win', 'loss', 'push']:
                        if p.get('result') == 'WIN': status = 'win'
                        elif p.get('result') == 'LOSS': status = 'loss'
                        elif p.get('result') == 'PUSH': status = 'push'
                        else: continue

                    stats = team_stats[bet_on_team]
                    stats['sport'] = sport
                    if status == 'win': stats['wins'] += 1
                    elif status == 'loss': stats['losses'] += 1
                    elif status == 'push': stats['pushes'] += 1
                    
                    stats['profit'] += p.get('profit_loss', 0.0)
                    
                    # Keep last 5 games for display
                    game_info = {
                        'date': p.get('game_date') or p.get('game_time') or p.get('logged_at', '')[:10],
                        'opponent': p.get('opponent') or (p['away_team'] if p.get('home_team') == bet_on_team else p.get('home_team', 'Unknown')),
                        'result': status.upper(),
                        'score': p.get('actual_score', '')
                    }
                    stats['games'].append(game_info)

        except Exception as e:
            # print(f"Error reading {file_path}: {e}")
            pass

    # Filter and Sort
    final_list = []
    for team, s in team_stats.items():
        total = s['wins'] + s['losses'] + s['pushes']
        if total >= MIN_PICKS:
            win_rate = s['wins'] / total
            if win_rate >= MIN_WIN_RATE:
                final_list.append({
                    'name': team,
                    'sport': s['sport'],
                    'record': f"{s['wins']}-{s['losses']}-{s['pushes']}",
                    'win_rate': win_rate,
                    'profit': s['profit'],
                    'games': sorted(s['games'], key=lambda x: x['date'], reverse=True)[:5] # Last 5
                })

    # Sort by Win Rate desc, then Profit desc
    final_list.sort(key=lambda x: (x['win_rate'], x['profit']), reverse=True)
    return final_list[:20]

def generate_html(teams):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top 20 Auto Bet Teams</title>
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-gold: #FFD700;
            --success: #4ade80;
            --danger: #f87171;
            --border: #333333;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-main);
            color: var(--text-primary);
            padding: 20px;
            margin: 0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 2.5rem;
            margin: 0;
            background: linear-gradient(45deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            position: relative;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
            overflow: hidden;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.5);
            border-color: var(--accent-gold);
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--accent-gold);
        }
        .team-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .team-name {
            font-size: 1.25rem;
            font-weight: 700;
        }
        .sport-badge {
            background: #333;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-secondary);
        }
        .stats-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            font-family: monospace;
        }
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        .txt-gold { color: var(--accent-gold); }
        .txt-green { color: var(--success); }
        
        .auto-bet-badge {
            display: inline-block;
            background: var(--accent-gold);
            color: #000;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 800;
            margin-top: 5px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.4); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(255, 215, 0, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0); }
        }
        
        .last-5 {
            font-size: 0.85rem;
        }
        .last-5-title {
            color: var(--text-secondary);
            font-size: 0.75rem;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .game-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
            padding: 4px;
            background: rgba(255,255,255,0.03);
            border-radius: 4px;
        }
        .win { color: var(--success); }
        .loss { color: var(--danger); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Top 20 Auto Bet Teams</h1>
            <p style="color: var(--text-secondary);">Teams with >80% Win Rate (Min 5 Picks)</p>
        </div>
        
        <div class="grid">
    """
    
    for team in teams:
        html += f"""
            <div class="card">
                <div class="team-header">
                    <div class="team-name">
                        {team['name']}
                        <br>
                        <span class="auto-bet-badge">AUTO BET</span>
                    </div>
                    <span class="sport-badge">{team['sport']}</span>
                </div>
                
                <div class="stats-row">
                    <div class="stat">
                        <div class="stat-value txt-gold">{int(team['win_rate']*100)}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{team['record']}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value txt-green">+{team['profit']:.2f}u</div>
                        <div class="stat-label">Profit</div>
                    </div>
                </div>
                
                <div class="last-5">
                    <div class="last-5-title">Recent Form (Last 5)</div>
                    {generate_game_rows(team['games'])}
                </div>
            </div>
        """
        
    html += """
        </div>
    </div>
</body>
</html>
    """
    
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    print(f"Report generated: {OUTPUT_FILE}")

def generate_game_rows(games):
    rows = ""
    for g in games:
        color = "win" if g['result'] == 'WIN' else "loss" if g['result'] == 'LOSS' else ""
        rows += f"""
        <div class="game-row">
            <span style="color: #b3b3b3;">vs {g['opponent'][:15]}..</span>
            <span class="{color}"><b>{g['result']}</b></span>
        </div>
        """
    return rows

if __name__ == "__main__":
    teams = calculate_team_stats()
    generate_html(teams)
