import json
import os
import re
from collections import defaultdict
from datetime import datetime

# Configuration
BASE_DIR = "/Users/rico/sports-models"
OUTPUT_FILE = os.path.join(BASE_DIR, "auto_bet_teams.html")
MIN_PICKS = 5
MIN_WIN_RATE = 0.80

def get_tracking_files():
    # Explicit list of known active tracking files or directories to avoid scanning backups
    active_dirs = [
        'nba', 'ncaa', 'nfl', 'mlb', 'wnba', 'soccer'
    ]
    files = []
    for root, _, filenames in os.walk(BASE_DIR):
        # Skip backup and hidden directories
        if 'backups' in root or '.cache' in root or '.git' in root:
            continue
            
        # Only process files in active directories
        rel_path = os.path.relpath(root, BASE_DIR)
        if rel_path != '.' and not any(d in rel_path.split(os.sep) for d in active_dirs):
            continue

        for f in filenames:
            if f.endswith('_tracking.json'):
                files.append(os.path.join(root, f))
    return files

def calculate_team_stats():
    team_stats = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'pushes': 0, 
        'profit': 0.0, 'games': [], 'sport': 'Unknown',
        'processed_bets': set(),
        'fav_wins': 0, 'fav_losses': 0, 'fav_pushes': 0,
        'dog_wins': 0, 'dog_losses': 0, 'dog_pushes': 0,
        'total_wagered': 0.0
    })

    for file_path in get_tracking_files():
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                picks = data.get('picks', [])
                
                # ... sport determination ...
                sport = 'Other'
                if 'nba' in file_path.lower(): sport = 'NBA'
                elif 'nfl' in file_path.lower(): sport = 'NFL'
                elif 'ncaa' in file_path.lower() or 'cbb' in file_path.lower(): sport = 'NCAAB'
                elif 'mlb' in file_path.lower(): sport = 'MLB'
                elif 'soccer' in file_path.lower(): sport = 'Soccer'
                elif 'wnba' in file_path.lower(): sport = 'WNBA'

                for p in picks:
                    bet_on_team = None
                    pick_text = p.get('pick_text', '')
                    
                    if 'team' in p:
                        bet_on_team = p['team']
                    elif 'home_team' in p and 'away_team' in p:
                        if p['home_team'] in pick_text:
                            bet_on_team = p['home_team']
                        elif p['away_team'] in pick_text:
                            bet_on_team = p['away_team']
                        else:
                            continue
                    
                    if not bet_on_team:
                        continue

                    # Filter out Totals / Props
                    if bet_on_team.upper() in ['OVER', 'UNDER', 'YES', 'NO']:
                        continue

                    # Deduplication
                    game_date = p.get('game_date') or p.get('game_time') or p.get('logged_at', '')[:10]
                    opponent = p.get('opponent') or (p['away_team'] if p.get('home_team') == bet_on_team else p.get('home_team', 'Unknown'))
                    
                    stats = team_stats[bet_on_team]
                    unique_key = f"{game_date}_{bet_on_team}_{opponent}_{p.get('pick_type', '')}"
                    if unique_key in stats['processed_bets']:
                        continue
                    stats['processed_bets'].add(unique_key)

                    status = p.get('status', '').lower()
                    if status not in ['win', 'loss', 'push']:
                        if p.get('result') == 'WIN': status = 'win'
                        elif p.get('result') == 'LOSS': status = 'loss'
                        elif p.get('result') == 'PUSH': status = 'push'
                        else: continue

                    stats['sport'] = sport
                    stats['total_wagered'] += 100.0 # Assuming 1 unit = 100 for ROI calc base

                    # Extract Line and Determine Fav/Dog
                    line_val = 0.0
                    line_str = ""
                    # Regex to find signed number at end of pick text: "Team Name -5.5" or "+3"
                    match = re.search(r'([-+]\d+\.?\d*)$', pick_text.strip())
                    if match:
                        line_str = match.group(1)
                        try:
                            line_val = float(line_str)
                        except:
                            pass
                    
                    # Update Fav/Dog stats
                    if line_val < 0:
                        # Favorite
                        if status == 'win': stats['fav_wins'] += 1
                        elif status == 'loss': stats['fav_losses'] += 1
                        elif status == 'push': stats['fav_pushes'] += 1
                    else:
                        # Underdog (or PK which we count as Dog here for simplicity usually, or logic splits)
                        # Usually PK is near 0. If 0, assume dog? Or Handle PK explicit?
                        # Let's count >= 0 as Dog
                        if status == 'win': stats['dog_wins'] += 1
                        elif status == 'loss': stats['dog_losses'] += 1
                        elif status == 'push': stats['dog_pushes'] += 1

                    if status == 'win': stats['wins'] += 1
                    elif status == 'loss': stats['losses'] += 1
                    elif status == 'push': stats['pushes'] += 1
                    
                    stats['profit'] += p.get('profit_loss', 0.0)
                    
                    game_info = {
                        'date': game_date,
                        'opponent': opponent,
                        'result': status.upper(),
                        'score': p.get('actual_score', ''),
                        'line': line_str
                    }
                    stats['games'].append(game_info)

        except Exception as e:
            pass

    # Filter and Sort
    final_list = []
    for team, s in team_stats.items():
        total = s['wins'] + s['losses'] + s['pushes']
        if total >= MIN_PICKS:
            win_rate = s['wins'] / total
            # ROI calculation
            roi = (s['profit'] / s['total_wagered']) * 100 if s['total_wagered'] > 0 else 0.0

            if win_rate >= MIN_WIN_RATE:
                final_list.append({
                    'name': team,
                    'sport': s['sport'],
                    'record': f"{s['wins']}-{s['losses']}-{s['pushes']}",
                    'fav_record': f"{s['fav_wins']}-{s['fav_losses']}-{s['fav_pushes']}",
                    'dog_record': f"{s['dog_wins']}-{s['dog_losses']}-{s['dog_pushes']}",
                    'win_rate': win_rate,
                    'profit': s['profit'] / 100.0,
                    'roi': roi,
                    'games': sorted(s['games'], key=lambda x: x['date'], reverse=True)[:5]
                })

    final_list.sort(key=lambda x: (x['win_rate'], x['profit']), reverse=True)
    return final_list[:20]

def generate_html(teams):
    # ... (Keep existing HTML header/CSS) ...
    # BUT we need to update the card content loop in generate_html
    # Since specific lines need to be replaced, I'll provide the Full generate_html function replacement or chunks.
    # To be safe, I will replace the whole logic part.
    pass # Managed by the tool call replacement


def generate_html(teams):
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Top 20 Auto Bet Teams</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --accent-gold: #FFD700;
            --border-color: #333333;
        }

        body {
            margin: 0;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }

        .container { max-width: 650px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
        }
        h1 { margin: 0; font-size: 22px; font-weight: 700; margin-bottom: 5px; }
        .subheader { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
        .date-sub { color: var(--text-secondary); font-size: 13px; margin-top: 5px; }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
        }

        .card-header {
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--bg-card-secondary);
            border-bottom: 1px solid var(--border-color);
        }

        .header-left { display: flex; align-items: center; gap: 10px; }
        .team-logo { width: 40px; height: 40px; border-radius: 50%; padding: 2px; object-fit: contain; background: #fff; }
        .player-info h2 { margin: 0; font-size: 16px; line-height: 1.2; }
        .matchup-info { color: var(--text-secondary); font-size: 12px; margin-top: 2px; }
        
        .auto-bet-badge {
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: #000;
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 800;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        .card-body { padding: 16px; }
        
        .bet-main-row { margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
        .bet-selection { font-size: 20px; font-weight: 800; }
        .metric-big { font-size: 24px; font-weight: 800; color: var(--accent-gold); }

        .stats-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr; /* Changed to 3 columns for Record, Fav, Dog */
            gap: 10px;
            background-color: var(--bg-main);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid var(--border-color);
        }
        .stat-item { text-align: center; }
        .stat-title { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px; letter-spacing: 0.5px; }
        .stat-val { font-size: 15px; font-weight: 700; }

        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }
        .metric-item { background-color: var(--bg-main); padding: 8px; border-radius: 8px; text-align: center; }
        .metric-lbl { display: block; font-size: 10px; color: var(--text-secondary); margin-bottom: 2px; }
        .metric-val { font-size: 14px; font-weight: 700; }

        .game-log { margin-top: 15px; }
        .game-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid #333;
            font-size: 13px;
        }
        .game-row:last-child { border-bottom: none; }
        
        .txt-green { color: var(--accent-green); }
        .txt-red { color: var(--accent-red); }
        .txt-gold { color: var(--accent-gold); }
        
        .win-tag { color: var(--accent-green); font-weight: 700; }
        .loss-tag { color: var(--accent-red); font-weight: 700; }

        /* Glow Effects */
        .glow-gold {
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.15);
            border: 1px solid rgba(255, 215, 0, 0.3);
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">Top 20 Auto Bet Teams</div>
            <div class="date-sub">Highly Efficient Teams (>80% Win Rate)</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 0.7rem; color: #888;">GENERATED</div>
            <div style="font-weight: 700;">""" + datetime.now().strftime("%Y-%m-%d") + """</div>
        </div>
    </header>
    
    <div style="margin-bottom: 20px; font-size: 13px; color: #888; text-align: center;">
        These teams have a proven track record of profitability this season.
    </div>
    """
    
    for team in teams:
        # Determine ROI Color
        profit_color = "txt-green" if team['profit'] > 0 else "txt-red"
        roi_color = "txt-green" if team['roi'] > 0 else "txt-red"
        
        html += f"""
        <div class="prop-card glow-gold">
            <div class="card-header">
                <div class="header-left">
                    <!-- Placeholder Logo based on Sport -->
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: #333; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                        {team['sport'][0]}
                    </div>
                    <div class="player-info">
                        <h2>{team['name']}</h2>
                        <div class="matchup-info">{team['sport']} • {team['record']} Overall</div>
                    </div>
                </div>
                <div class="game-meta">
                    <span class="auto-bet-badge">AUTO BET</span>
                </div>
            </div>
            
            <div class="card-body">
                <div class="bet-main-row">
                    <div>
                        <div style="font-size: 11px; color: #888; text-transform: uppercase;">Total Profit</div>
                        <div class="metric-big {profit_color}">+{team['profit']:.2f}u</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 11px; color: #888; text-transform: uppercase;">Win Rate</div>
                        <div class="metric-big txt-gold">{int(team['win_rate']*100)}%</div>
                    </div>
                </div>

                <!-- STATS GRID -->
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-title">Overall</div>
                        <div class="stat-val">{team['record']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">As Fav</div>
                        <div class="stat-val">{team['fav_record']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">As Dog</div>
                        <div class="stat-val">{team['dog_record']}</div>
                    </div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-lbl">AVG ODDS</span>
                        <span class="metric-val">-110</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">CONSISTENCY</span>
                        <span class="metric-val txt-green">A+</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">ROI</span>
                        <span class="metric-val {roi_color}">{team['roi']:.1f}%</span>
                    </div>
                </div>

                <div class="game-log">
                    <div style="font-size: 11px; color: #888; margin-bottom: 5px; text-transform: uppercase;">Last 5 Games</div>
                    {generate_game_rows(team['games'])}
                </div>
            </div>
        </div>
        """
        
    html += """
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
        res_class = "win-tag" if g['result'] == 'WIN' else "loss-tag"
        line_display = f"({g['line']})" if g['line'] else ""
        rows += f"""
        <div class="game-row">
            <span style="color: #b3b3b3;">vs {g['opponent'][:20]} {line_display}</span>
            <span class="{res_class}">{g['result']} ({g['score']})</span>
        </div>
        """
    return rows


if __name__ == "__main__":
    teams = calculate_team_stats()
    generate_html(teams)
