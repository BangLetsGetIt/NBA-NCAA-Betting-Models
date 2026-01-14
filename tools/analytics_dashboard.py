#!/usr/bin/env python3
"""
Analytics Dashboard Generator
Aggregates all tracking JSON files and generates a comprehensive HTML dashboard
with charts, hot/cold analysis, and performance breakdowns.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Constants
LOOKBACK_DAYS = 14
BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "analytics_dashboard.html"

# All tracking files to aggregate
TRACKING_FILES = {
    "NBA Main": "nba/nba_picks_tracking.json",
    "NBA Points": "nba/nba_points_props_tracking.json",
    "NBA Rebounds": "nba/nba_rebounds_props_tracking.json",
    "NBA Assists": "nba/nba_assists_props_tracking.json",
    "NBA 3PT": "nba/nba_3pt_props_tracking.json",
    "NFL Main": "nfl/nfl_picks_tracking.json",
    "NFL Passing": "nfl/nfl_passing_yards_props_tracking.json",
    "NFL Rushing": "nfl/nfl_rushing_yards_props_tracking.json",
    "NFL Receiving": "nfl/nfl_receiving_yards_props_tracking.json",
    "NFL Receptions": "nfl/nfl_receptions_props_tracking.json",
    "NFL ATD": "nfl/atd_model_tracking.json",
    "NCAAB Main": "ncaa/ncaab_picks_tracking.json",
    "NCAAB Rebounds": "ncaa/cbb_rebounds_props_tracking.json",
    "Soccer": "soccer/soccer_picks_tracking.json",
    "MLB": "mlb/mlb_master_model_tracking.json",
}


def normalize_result(result):
    """Normalize result field to uppercase for consistent comparison."""
    if result is None:
        return None
    return str(result).upper()


def load_all_tracking_data():
    """Load and combine all tracking JSON files."""
    all_picks = []
    model_stats = {}
    
    for model_name, rel_path in TRACKING_FILES.items():
        file_path = BASE_DIR / rel_path
        if not file_path.exists():
            continue
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            picks = data.get('picks', [])
            # Add model source to each pick
            for pick in picks:
                pick['_model'] = model_name
            all_picks.extend(picks)
            
            # Calculate model-level stats (case-insensitive)
            graded = [p for p in picks if normalize_result(p.get('result')) in ['WIN', 'LOSS', 'PUSH']]
            wins = sum(1 for p in graded if normalize_result(p.get('result')) == 'WIN')
            losses = sum(1 for p in graded if normalize_result(p.get('result')) == 'LOSS')
            pushes = sum(1 for p in graded if normalize_result(p.get('result')) == 'PUSH')
            profit = sum(p.get('profit_loss', 0) for p in graded) / 100  # Convert to units
            
            model_stats[model_name] = {
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'profit': profit,
                'total': wins + losses,
                'win_rate': wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            }
        except Exception as e:
            print(f"Error loading {model_name}: {e}")
    
    return all_picks, model_stats


def calculate_overall_stats(picks):
    """Calculate overall performance statistics."""
    graded = [p for p in picks if normalize_result(p.get('result')) in ['WIN', 'LOSS', 'PUSH']]
    wins = sum(1 for p in graded if normalize_result(p.get('result')) == 'WIN')
    losses = sum(1 for p in graded if normalize_result(p.get('result')) == 'LOSS')
    pushes = sum(1 for p in graded if normalize_result(p.get('result')) == 'PUSH')
    profit = sum(p.get('profit_loss', 0) for p in graded) / 100  # Convert to units
    
    total_risked = (wins + losses) * 100  # Assuming $100 per bet
    roi = (profit / total_risked * 100) if total_risked > 0 else 0
    
    return {
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'profit': profit,
        'roi': roi,
        'total': wins + losses + pushes,
        'win_rate': wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    }


def calculate_hot_cold_teams(picks, days=14):
    """Find hot and cold teams based on recent performance."""
    cutoff = datetime.now() - timedelta(days=days)
    
    team_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
    
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        # Parse game time
        game_time_str = pick.get('game_time', '')
        try:
            if 'T' in game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            else:
                continue
        except:
            continue
        
        if game_time.replace(tzinfo=None) < cutoff:
            continue
        
        # Get teams involved in the pick
        home_team = pick.get('home_team', '')
        away_team = pick.get('away_team', '')
        direction = pick.get('direction', '')
        result = normalize_result(pick.get('result'))
        profit = pick.get('profit_loss', 0) / 100  # Convert to units
        
        # Determine which team the pick was on
        if direction == 'HOME':
            team = home_team
        elif direction == 'AWAY':
            team = away_team
        elif direction in ['OVER', 'UNDER']:
            # For totals, credit both teams
            team = f"{home_team} vs {away_team}"
        else:
            continue
        
        if result == 'WIN':
            team_stats[team]['wins'] += 1
        else:
            team_stats[team]['losses'] += 1
        team_stats[team]['profit'] += profit
    
    # Calculate win rates and sort
    team_list = []
    for team, stats in team_stats.items():
        total = stats['wins'] + stats['losses']
        if total >= 2:  # Minimum sample size
            win_rate = stats['wins'] / total * 100
            team_list.append({
                'team': team,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'profit': stats['profit'],
                'win_rate': win_rate,
                'total': total
            })
    
    # Sort for hot (best win rate) and cold (worst win rate)
    hot_teams = sorted(team_list, key=lambda x: (-x['win_rate'], -x['profit']))[:10]
    cold_teams = sorted(team_list, key=lambda x: (x['win_rate'], x['profit']))[:10]
    
    return hot_teams, cold_teams


def calculate_weekly_breakdown(picks, days=14):
    """Calculate daily performance for the last N days."""
    daily_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
    cutoff = datetime.now() - timedelta(days=days)
    
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        game_time_str = pick.get('game_time', '')
        try:
            if 'T' in game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            else:
                continue
        except:
            continue
        
        if game_time.replace(tzinfo=None) < cutoff:
            continue
        
        date_key = game_time.strftime('%Y-%m-%d')
        result = normalize_result(pick.get('result'))
        profit = pick.get('profit_loss', 0) / 100  # Convert to units
        
        if result == 'WIN':
            daily_stats[date_key]['wins'] += 1
        else:
            daily_stats[date_key]['losses'] += 1
        daily_stats[date_key]['profit'] += profit
    
    # Convert to sorted list
    daily_list = []
    for date, stats in sorted(daily_stats.items()):
        daily_list.append({
            'date': date,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'profit': stats['profit']
        })
    
    return daily_list


def calculate_league_stats(picks):
    """Calculate performance by league."""
    league_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
    
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        league = pick.get('league', 'Unknown')
        result = normalize_result(pick.get('result'))
        profit = pick.get('profit_loss', 0) / 100  # Convert to units
        
        if result == 'WIN':
            league_stats[league]['wins'] += 1
        else:
            league_stats[league]['losses'] += 1
        league_stats[league]['profit'] += profit
    
    league_list = []
    for league, stats in league_stats.items():
        total = stats['wins'] + stats['losses']
        if total > 0:
            league_list.append({
                'league': league,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'profit': stats['profit'],
                'win_rate': stats['wins'] / total * 100,
                'total': total
            })
    
    return sorted(league_list, key=lambda x: -x['profit'])


def calculate_prop_analysis(picks):
    """Analyze performance by pick type and direction."""
    prop_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})
    
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        pick_type = pick.get('pick_type', 'Unknown')
        direction = pick.get('direction', 'Unknown')
        result = normalize_result(pick.get('result'))
        profit = pick.get('profit_loss', 0) / 100  # Convert to units
        
        # Track by type
        if result == 'WIN':
            prop_stats[pick_type]['wins'] += 1
        else:
            prop_stats[pick_type]['losses'] += 1
        prop_stats[pick_type]['profit'] += profit
        
        # Track by direction
        if result == 'WIN':
            prop_stats[direction]['wins'] += 1
        else:
            prop_stats[direction]['losses'] += 1
        prop_stats[direction]['profit'] += profit
    
    prop_list = []
    for prop, stats in prop_stats.items():
        total = stats['wins'] + stats['losses']
        if total > 0:
            prop_list.append({
                'type': prop,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'profit': stats['profit'],
                'win_rate': stats['wins'] / total * 100,
                'total': total
            })
    
    return sorted(prop_list, key=lambda x: -x['profit'])


def calculate_edge_analysis(picks):
    """Analyze win rate by edge buckets."""
    edge_buckets = {
        '0-1': {'wins': 0, 'losses': 0},
        '1-2': {'wins': 0, 'losses': 0},
        '2-3': {'wins': 0, 'losses': 0},
        '3+': {'wins': 0, 'losses': 0}
    }
    
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        edge = abs(pick.get('edge', 0))
        result = normalize_result(pick.get('result'))
        
        if edge < 1:
            bucket = '0-1'
        elif edge < 2:
            bucket = '1-2'
        elif edge < 3:
            bucket = '2-3'
        else:
            bucket = '3+'
        
        if result == 'WIN':
            edge_buckets[bucket]['wins'] += 1
        else:
            edge_buckets[bucket]['losses'] += 1
    
    edge_list = []
    for bucket, stats in edge_buckets.items():
        total = stats['wins'] + stats['losses']
        if total > 0:
            edge_list.append({
                'bucket': bucket,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': stats['wins'] / total * 100,
                'total': total
            })
    
    return edge_list


def calculate_cumulative_profit(picks):
    """Calculate cumulative profit over time for charting."""
    # Get all graded picks with dates
    dated_picks = []
    for pick in picks:
        if normalize_result(pick.get('result')) not in ['WIN', 'LOSS']:
            continue
        
        game_time_str = pick.get('game_time', '')
        try:
            if 'T' in game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                dated_picks.append({
                    'date': game_time,
                    'profit': pick.get('profit_loss', 0) / 100  # Convert to units
                })
        except:
            continue
    
    # Sort by date
    dated_picks.sort(key=lambda x: x['date'])
    
    # Calculate cumulative
    cumulative = []
    running_total = 0
    for pick in dated_picks:
        running_total += pick['profit']
        cumulative.append({
            'date': pick['date'].strftime('%Y-%m-%d'),
            'profit': running_total
        })
    
    return cumulative


def generate_html_dashboard(overall, model_stats, hot_teams, cold_teams, 
                           weekly, leagues, props, edges, cumulative):
    """Generate the HTML dashboard with Chart.js visualizations."""
    
    # Prepare chart data
    weekly_labels = json.dumps([d['date'] for d in weekly])
    weekly_profits = json.dumps([d['profit'] for d in weekly])
    weekly_wins = json.dumps([d['wins'] for d in weekly])
    weekly_losses = json.dumps([d['losses'] for d in weekly])
    
    league_labels = json.dumps([l['league'][:15] for l in leagues[:10]])
    league_profits = json.dumps([l['profit'] for l in leagues[:10]])
    league_win_rates = json.dumps([round(l['win_rate'], 1) for l in leagues[:10]])
    
    prop_labels = json.dumps([p['type'] for p in props])
    prop_profits = json.dumps([p['profit'] for p in props])
    prop_win_rates = json.dumps([round(p['win_rate'], 1) for p in props])
    
    edge_labels = json.dumps([e['bucket'] for e in edges])
    edge_win_rates = json.dumps([round(e['win_rate'], 1) for e in edges])
    edge_totals = json.dumps([e['total'] for e in edges])
    
    # Last 30 days of cumulative profit
    recent_cumulative = cumulative[-60:] if len(cumulative) > 60 else cumulative
    cumulative_labels = json.dumps([c['date'] for c in recent_cumulative])
    cumulative_profits = json.dumps([c['profit'] for c in recent_cumulative])
    
    # Model comparison data
    model_names = json.dumps(list(model_stats.keys()))
    model_profits = json.dumps([s['profit'] for s in model_stats.values()])
    model_win_rates = json.dumps([round(s['win_rate'], 1) for s in model_stats.values()])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Analytics Dashboard | Quiet Wins</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-primary: #0a0a1a;
            --bg-secondary: #12122a;
            --bg-card: rgba(255, 255, 255, 0.03);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --accent-green: #00ff88;
            --accent-red: #ff4466;
            --accent-blue: #4488ff;
            --accent-purple: #8844ff;
            --accent-gold: #ffaa00;
            --glass-border: rgba(255, 255, 255, 0.1);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, #1a1a3a 50%, var(--bg-primary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px;
            background: var(--bg-card);
            border-radius: 20px;
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(10px);
        }}
        
        header h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-gold), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        
        header p {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        .overview-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            backdrop-filter: blur(10px);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        
        .stat-card .value {{
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 8px;
        }}
        
        .stat-card .label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.profit .value {{
            color: var(--accent-green);
        }}
        
        .stat-card.loss .value {{
            color: var(--accent-red);
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        @media (max-width: 900px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
        }}
        
        .chart-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .chart-card.full-width {{
            grid-column: 1 / -1;
        }}
        
        .tables-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        @media (max-width: 900px) {{
            .tables-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .table-card {{
            background: var(--bg-card);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
        }}
        
        .table-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 10px 8px;
            text-align: left;
            border-bottom: 1px solid var(--glass-border);
            font-size: 0.85rem;
        }}
        
        th {{
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
        }}
        
        .win {{ color: var(--accent-green); }}
        .loss {{ color: var(--accent-red); }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .badge.hot {{
            background: rgba(0, 255, 136, 0.15);
            color: var(--accent-green);
        }}
        
        .badge.cold {{
            background: rgba(255, 68, 102, 0.15);
            color: var(--accent-red);
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }}
        
        .canvas-container {{
            position: relative;
            height: 280px;
        }}
        
        .model-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 10px;
        }}
        
        .model-item {{
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--glass-border);
            border-radius: 10px;
            padding: 12px;
            text-align: center;
        }}
        
        .model-item .name {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .model-item .record {{
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        
        .model-item .profit {{
            font-size: 0.85rem;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Analytics Dashboard</h1>
            <p>Comprehensive performance analysis across all models • Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </header>
        
        <!-- Overview Cards -->
        <div class="overview-grid">
            <div class="stat-card">
                <div class="value">{overall['wins']}-{overall['losses']}-{overall['pushes']}</div>
                <div class="label">Overall Record</div>
            </div>
            <div class="stat-card {'profit' if overall['profit'] >= 0 else 'loss'}">
                <div class="value">{'+' if overall['profit'] >= 0 else ''}{overall['profit']:.0f}u</div>
                <div class="label">Net Profit (Units)</div>
            </div>
            <div class="stat-card {'profit' if overall['roi'] >= 0 else 'loss'}">
                <div class="value">{'+' if overall['roi'] >= 0 else ''}{overall['roi']:.1f}%</div>
                <div class="label">ROI</div>
            </div>
            <div class="stat-card">
                <div class="value">{overall['win_rate']:.1f}%</div>
                <div class="label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="value">{len(model_stats)}</div>
                <div class="label">Active Models</div>
            </div>
        </div>
        
        <!-- Charts Row 1 -->
        <div class="charts-grid">
            <div class="chart-card full-width">
                <h3>📈 Cumulative Profit Over Time</h3>
                <div class="canvas-container">
                    <canvas id="cumulativeChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Hot/Cold Tables -->
        <div class="tables-grid">
            <div class="table-card">
                <h3>🔥 Hot Teams (Last 14 Days)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Team</th>
                            <th>Record</th>
                            <th>Win %</th>
                            <th>Profit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"""<tr>
                            <td>{t['team'][:25]}</td>
                            <td>{t['wins']}-{t['losses']}</td>
                            <td><span class="badge hot">{t['win_rate']:.0f}%</span></td>
                            <td class="win">+{t['profit']:.0f}u</td>
                        </tr>""" for t in hot_teams[:8])}
                    </tbody>
                </table>
            </div>
            <div class="table-card">
                <h3>❄️ Cold Teams (Last 14 Days)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Team</th>
                            <th>Record</th>
                            <th>Win %</th>
                            <th>Profit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f"""<tr>
                            <td>{t['team'][:25]}</td>
                            <td>{t['wins']}-{t['losses']}</td>
                            <td><span class="badge cold">{t['win_rate']:.0f}%</span></td>
                            <td class="loss">{t['profit']:.0f}u</td>
                        </tr>""" for t in cold_teams[:8])}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Charts Row 2 -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📅 Daily Performance (14 Days)</h3>
                <div class="canvas-container">
                    <canvas id="dailyChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>🏆 League Performance</h3>
                <div class="canvas-container">
                    <canvas id="leagueChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>📊 Prop Type Analysis</h3>
                <div class="canvas-container">
                    <canvas id="propsChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>🎯 Edge vs Win Rate</h3>
                <div class="canvas-container">
                    <canvas id="edgeChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Model Breakdown -->
        <div class="chart-card" style="margin-bottom: 30px;">
            <h3>🤖 Model Breakdown</h3>
            <div class="model-grid">
                {''.join(f"""<div class="model-item">
                    <div class="name">{name}</div>
                    <div class="record">{stats['wins']}-{stats['losses']}</div>
                    <div class="profit {'win' if stats['profit'] >= 0 else 'loss'}">{'+' if stats['profit'] >= 0 else ''}{stats['profit']:.0f}u</div>
                </div>""" for name, stats in model_stats.items())}
            </div>
        </div>
        
        <footer>
            <p>Quiet Wins Analytics • Auto-generated from {len(model_stats)} tracking files • {overall['total']} total graded picks</p>
        </footer>
    </div>
    
    <script>
        // Chart.js defaults
        Chart.defaults.color = '#a0a0b0';
        Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
        
        // Cumulative Profit Chart
        new Chart(document.getElementById('cumulativeChart'), {{
            type: 'line',
            data: {{
                labels: {cumulative_labels},
                datasets: [{{
                    label: 'Cumulative Profit (Units)',
                    data: {cumulative_profits},
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        grid: {{ color: 'rgba(255,255,255,0.03)' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ maxTicksLimit: 10 }}
                    }}
                }}
            }}
        }});
        
        // Daily Performance Chart
        new Chart(document.getElementById('dailyChart'), {{
            type: 'bar',
            data: {{
                labels: {weekly_labels},
                datasets: [{{
                    label: 'Profit',
                    data: {weekly_profits},
                    backgroundColor: {weekly_profits}.map(v => v >= 0 ? 'rgba(0, 255, 136, 0.7)' : 'rgba(255, 68, 102, 0.7)'),
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        grid: {{ color: 'rgba(255,255,255,0.03)' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ maxTicksLimit: 7 }}
                    }}
                }}
            }}
        }});
        
        // League Performance Chart
        new Chart(document.getElementById('leagueChart'), {{
            type: 'bar',
            data: {{
                labels: {league_labels},
                datasets: [{{
                    label: 'Profit (Units)',
                    data: {league_profits},
                    backgroundColor: {league_profits}.map(v => v >= 0 ? 'rgba(68, 136, 255, 0.7)' : 'rgba(255, 68, 102, 0.7)'),
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255,255,255,0.03)' }}
                    }},
                    y: {{
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
        
        // Props Analysis Chart
        new Chart(document.getElementById('propsChart'), {{
            type: 'doughnut',
            data: {{
                labels: {prop_labels},
                datasets: [{{
                    data: {prop_profits}.map(Math.abs),
                    backgroundColor: [
                        'rgba(0, 255, 136, 0.7)',
                        'rgba(68, 136, 255, 0.7)',
                        'rgba(136, 68, 255, 0.7)',
                        'rgba(255, 170, 0, 0.7)',
                        'rgba(255, 68, 102, 0.7)',
                        'rgba(0, 200, 200, 0.7)'
                    ],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ boxWidth: 12, padding: 10 }}
                    }}
                }}
            }}
        }});
        
        // Edge Analysis Chart
        new Chart(document.getElementById('edgeChart'), {{
            type: 'bar',
            data: {{
                labels: {edge_labels},
                datasets: [{{
                    label: 'Win Rate %',
                    data: {edge_win_rates},
                    backgroundColor: 'rgba(136, 68, 255, 0.7)',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        max: 100,
                        grid: {{ color: 'rgba(255,255,255,0.03)' }}
                    }},
                    x: {{
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    return html


def main():
    """Main entry point."""
    print("📊 Generating Analytics Dashboard...")
    print(f"   Looking back {LOOKBACK_DAYS} days for hot/cold analysis")
    
    # Load all data
    all_picks, model_stats = load_all_tracking_data()
    print(f"   Loaded {len(all_picks)} total picks from {len(model_stats)} models")
    
    # Calculate all stats
    overall = calculate_overall_stats(all_picks)
    hot_teams, cold_teams = calculate_hot_cold_teams(all_picks, LOOKBACK_DAYS)
    weekly = calculate_weekly_breakdown(all_picks, LOOKBACK_DAYS)
    leagues = calculate_league_stats(all_picks)
    props = calculate_prop_analysis(all_picks)
    edges = calculate_edge_analysis(all_picks)
    cumulative = calculate_cumulative_profit(all_picks)
    
    # Generate HTML
    html = generate_html_dashboard(
        overall, model_stats, hot_teams, cold_teams,
        weekly, leagues, props, edges, cumulative
    )
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard saved to: {OUTPUT_FILE}")
    print(f"   Overall Record: {overall['wins']}-{overall['losses']}-{overall['pushes']}")
    print(f"   Net Profit: {overall['profit']:+.0f} units")
    print(f"   ROI: {overall['roi']:+.1f}%")


if __name__ == "__main__":
    main()
