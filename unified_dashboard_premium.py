#!/usr/bin/env python3
"""
Premium Unified Sports Betting Dashboard
Rich cards with team performance history, filters, and all the info you need
NO SERVER REQUIRED - all data embedded directly in HTML
"""

import json
import os
from datetime import datetime
import pytz
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "unified_dashboard_premium.html")

# Model tracking files
MODEL_FILES = {
    'NBA': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'nba', 'nba_picks_tracking.json'),
        '3pt_props': os.path.join(SCRIPT_DIR, 'nba', 'nba_3pt_props_tracking.json')
    },
    'NCAA': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'ncaa', 'ncaab_picks_tracking.json')
    }
}

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_tracking_data():
    """Load all tracking data and calculate team performance history"""
    print(f"{Colors.CYAN}Loading model data...{Colors.END}")

    all_picks = []
    team_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})

    for sport, models in MODEL_FILES.items():
        for model_type, file_path in models.items():
            if not file_path or not os.path.exists(file_path):
                continue

            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                for pick in data.get('picks', []):
                    # Build matchup string if not provided
                    matchup = pick.get('matchup', '')
                    if not matchup and pick.get('away_team') and pick.get('home_team'):
                        matchup = f"{pick['away_team']} @ {pick['home_team']}"

                    # NCAA uses 'profit' field, NBA uses 'profit_loss'
                    profit_loss = pick.get('profit_loss') if pick.get('profit_loss') is not None else pick.get('profit', 0)
                    if profit_loss is None:
                        profit_loss = 0

                    # Normalize pick format
                    normalized = {
                        'sport': sport,
                        'model_type': model_type,
                        'status': pick.get('status', 'pending'),
                        'game_date': pick.get('game_date') or pick.get('game_time'),
                        'matchup': matchup,
                        'pick_description': pick.get('pick_text', pick.get('pick', '')).replace('✅', '').replace('BET:', '').strip(),
                        'pick_type': pick.get('pick_type', 'Unknown').capitalize(),
                        'odds': pick.get('odds', -110),
                        'edge': pick.get('edge'),
                        'ai_score': pick.get('ai_score'),
                        'result': pick.get('result'),
                        'profit_loss': profit_loss,
                        'home_team': pick.get('home_team', ''),
                        'away_team': pick.get('away_team', ''),
                        'player': pick.get('player', ''),
                        'team': pick.get('team', '')
                    }

                    all_picks.append(normalized)

                    # Track team performance - find which team we're betting on
                    if normalized['status'] in ['win', 'loss']:
                        # Determine the team being bet on from the pick description
                        pick_desc = normalized['pick_description']
                        bet_team = None

                        # Check if home or away team is in the pick
                        if normalized['home_team'] and normalized['home_team'] in pick_desc:
                            bet_team = normalized['home_team']
                        elif normalized['away_team'] and normalized['away_team'] in pick_desc:
                            bet_team = normalized['away_team']
                        elif normalized['team']:  # For player props
                            bet_team = normalized['team']

                        # Only track stats for the team we're actually betting on
                        if bet_team:
                            if normalized['status'] == 'win':
                                team_stats[bet_team]['wins'] += 1
                                team_stats[bet_team]['profit'] += normalized['profit_loss']
                            else:
                                team_stats[bet_team]['losses'] += 1
                                team_stats[bet_team]['profit'] += normalized['profit_loss']

            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    # Attach team stats to picks
    for pick in all_picks:
        teams = [pick['home_team'], pick['away_team'], pick['team']]
        pick['team_performance'] = {}
        for team in teams:
            if team and team in team_stats:
                stats = team_stats[team]
                total = stats['wins'] + stats['losses']
                win_rate = (stats['wins'] / total * 100) if total > 0 else 0
                pick['team_performance'][team] = {
                    'record': f"{stats['wins']}-{stats['losses']}",
                    'win_rate': win_rate,
                    'profit': stats['profit']
                }

    print(f"{Colors.GREEN}✓ Loaded {len(all_picks)} picks{Colors.END}")
    return all_picks

def calculate_overall_stats(picks):
    """Calculate overall statistics"""
    completed = [p for p in picks if p['status'] in ['win', 'loss']]
    wins = [p for p in picks if p['status'] == 'win']
    losses = [p for p in picks if p['status'] == 'loss']
    pending = [p for p in picks if p['status'] == 'pending']

    return {
        'total': len(picks),
        'wins': len(wins),
        'losses': len(losses),
        'pending': len(pending),
        'win_rate': (len(wins) / len(completed) * 100) if completed else 0,
        'profit_loss': sum(p['profit_loss'] for p in picks),
        'record': f"{len(wins)}-{len(losses)}"
    }

def generate_html(picks, stats):
    """Generate premium HTML dashboard with embedded data"""

    # Convert data to JSON for embedding
    data_json = json.dumps({
        'picks': picks,
        'stats': stats,
        'generated_at': datetime.now(pytz.timezone('US/Eastern')).strftime('%B %d, %Y %I:%M %p ET')
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Premium Sports Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 1.5rem;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: #1a1a1a;
            border-radius: 1rem;
            border: 2px solid #fbbf24;
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 900;
            color: #fbbf24;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            font-size: 1.1rem;
            color: #9ca3af;
        }}

        .timestamp {{
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.5rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: #1a1a1a;
            padding: 1.5rem;
            border-radius: 0.75rem;
            text-align: center;
            border: 2px solid #2a2a2a;
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: #fbbf24;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 900;
            margin-bottom: 0.5rem;
        }}

        .stat-label {{
            font-size: 0.75rem;
            color: #9ca3af;
            text-transform: uppercase;
        }}

        .stat-card.profit .stat-value {{ color: #10b981; }}
        .stat-card.pending .stat-value {{ color: #fbbf24; }}
        .stat-card.winrate .stat-value {{ color: #3b82f6; }}

        .filters {{
            background: #1a1a1a;
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
            border: 1px solid #2a2a2a;
        }}

        .filter-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #fbbf24;
            margin-bottom: 1rem;
        }}

        .filter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}

        .filter-group label {{
            display: block;
            font-size: 0.75rem;
            color: #9ca3af;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}

        select, input {{
            width: 100%;
            padding: 0.75rem;
            background: #0a0a0a;
            border: 1px solid #2a2a2a;
            border-radius: 0.5rem;
            color: #e2e8f0;
            font-size: 0.875rem;
        }}

        select:focus, input:focus {{
            outline: none;
            border-color: #fbbf24;
        }}

        .picks-grid {{
            display: grid;
            gap: 1.5rem;
        }}

        .pick-card {{
            background: #1a1a1a;
            border: 2px solid #2a2a2a;
            border-radius: 1rem;
            padding: 1.5rem;
            transition: all 0.2s;
        }}

        .pick-card:hover {{
            transform: translateY(-2px);
            border-color: #fbbf24;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}

        .pick-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .sport-badge {{
            padding: 0.35rem 0.75rem;
            border-radius: 0.4rem;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .sport-badge.nba {{ background: #ec4899; color: #fff; }}
        .sport-badge.ncaa {{ background: #3b82f6; color: #fff; }}

        .status-badge {{
            padding: 0.35rem 0.75rem;
            border-radius: 0.4rem;
            font-size: 0.75rem;
            font-weight: 700;
        }}

        .status-badge.pending {{ background: #78350f; color: #fbbf24; }}
        .status-badge.win {{ background: #064e3b; color: #10b981; }}
        .status-badge.loss {{ background: #450a0a; color: #ef4444; }}

        .matchup {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #fbbf24;
            margin-bottom: 0.5rem;
        }}

        .game-time {{
            font-size: 0.875rem;
            color: #9ca3af;
            margin-bottom: 1rem;
        }}

        .pick-details {{
            background: #0a0a0a;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }}

        .pick-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #2a2a2a;
        }}

        .pick-row:last-child {{
            border-bottom: none;
        }}

        .pick-label {{
            color: #9ca3af;
            font-size: 0.875rem;
        }}

        .pick-value {{
            font-weight: 700;
            font-size: 0.875rem;
        }}

        .pick-value.pick-text {{
            color: #10b981;
            font-size: 1rem;
        }}

        .pick-value.edge {{
            color: #fbbf24;
            font-size: 1.1rem;
        }}

        .team-performance {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #2a2a2a;
        }}

        .perf-title {{
            font-size: 0.75rem;
            color: #9ca3af;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}

        .perf-stats {{
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}

        .perf-item {{
            display: flex;
            flex-direction: column;
        }}

        .perf-team {{
            font-size: 0.75rem;
            color: #6b7280;
        }}

        .perf-record {{
            font-size: 0.875rem;
            font-weight: 700;
            color: #e2e8f0;
        }}

        .perf-winrate {{
            font-size: 0.75rem;
            color: #9ca3af;
        }}

        .perf-profit {{
            font-size: 0.75rem;
        }}

        .perf-profit.positive {{ color: #10b981; }}
        .perf-profit.negative {{ color: #ef4444; }}

        .no-results {{
            text-align: center;
            padding: 3rem;
            color: #6b7280;
            font-size: 1.1rem;
        }}

        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8rem; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .filter-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏀 PREMIUM SPORTS DASHBOARD</h1>
            <div class="subtitle">All Your Models. Rich Data. Smart Filters.</div>
            <div class="timestamp" id="timestamp"></div>
        </div>

        <div id="stats" class="stats-grid"></div>

        <div class="filters">
            <div class="filter-title">🎯 FILTER PICKS</div>
            <div class="filter-grid">
                <div class="filter-group">
                    <label>Sport</label>
                    <select id="sportFilter">
                        <option value="all">All Sports</option>
                        <option value="NBA">NBA</option>
                        <option value="NCAA">NCAA Basketball</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Status</label>
                    <select id="statusFilter">
                        <option value="all">All</option>
                        <option value="pending">Pending Only</option>
                        <option value="win">Wins Only</option>
                        <option value="loss">Losses Only</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Pick Type</label>
                    <select id="typeFilter">
                        <option value="all">All Types</option>
                        <option value="Spread">Spreads</option>
                        <option value="Total">Totals</option>
                        <option value="Player prop">Player Props</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Min Edge</label>
                    <input type="number" id="minEdgeFilter" placeholder="e.g. 5.0" step="0.5" min="0">
                </div>
                <div class="filter-group">
                    <label>Min AI Score</label>
                    <input type="number" id="minScoreFilter" placeholder="e.g. 8.0" step="0.1" min="0" max="10">
                </div>
                <div class="filter-group">
                    <label>Search</label>
                    <input type="text" id="searchFilter" placeholder="Team, player, matchup...">
                </div>
            </div>
        </div>

        <div id="picks-container" class="picks-grid"></div>
    </div>

    <script>
        // Embedded data - no server required!
        const dashboardData = {data_json};

        let filteredPicks = [];

        function init() {{
            document.getElementById('timestamp').textContent = `Last Updated: ${{dashboardData.generated_at}}`;
            updateStats();
            applyFilters();

            // Add event listeners
            document.getElementById('sportFilter').addEventListener('change', applyFilters);
            document.getElementById('statusFilter').addEventListener('change', applyFilters);
            document.getElementById('typeFilter').addEventListener('change', applyFilters);
            document.getElementById('minEdgeFilter').addEventListener('input', applyFilters);
            document.getElementById('minScoreFilter').addEventListener('input', applyFilters);
            document.getElementById('searchFilter').addEventListener('input', applyFilters);
        }}

        function updateStats() {{
            const stats = dashboardData.stats;
            document.getElementById('stats').innerHTML = `
                <div class="stat-card pending">
                    <div class="stat-value">${{stats.pending}}</div>
                    <div class="stat-label">Active Picks</div>
                </div>
                <div class="stat-card winrate">
                    <div class="stat-value">${{stats.win_rate.toFixed(1)}}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card profit">
                    <div class="stat-value">${{stats.profit_loss >= 0 ? '+' : ''}}${{(stats.profit_loss/100).toFixed(0)}}u</div>
                    <div class="stat-label">Total P/L</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${{stats.total}}</div>
                    <div class="stat-label">All-Time Picks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${{stats.record}}</div>
                    <div class="stat-label">Record</div>
                </div>
            `;
        }}

        function applyFilters() {{
            const sport = document.getElementById('sportFilter').value;
            const status = document.getElementById('statusFilter').value;
            const type = document.getElementById('typeFilter').value;
            const minEdge = parseFloat(document.getElementById('minEdgeFilter').value) || 0;
            const minScore = parseFloat(document.getElementById('minScoreFilter').value) || 0;
            const search = document.getElementById('searchFilter').value.toLowerCase();

            filteredPicks = dashboardData.picks.filter(pick => {{
                if (sport !== 'all' && pick.sport !== sport) return false;
                if (status !== 'all' && pick.status !== status) return false;
                if (type !== 'all' && pick.pick_type !== type) return false;
                if (pick.edge && Math.abs(pick.edge) < minEdge) return false;
                if (pick.ai_score && pick.ai_score < minScore) return false;
                if (search) {{
                    const searchText = JSON.stringify(pick).toLowerCase();
                    if (!searchText.includes(search)) return false;
                }}
                return true;
            }});

            renderPicks();
        }}

        function renderPicks() {{
            const container = document.getElementById('picks-container');

            if (filteredPicks.length === 0) {{
                container.innerHTML = '<div class="no-results">No picks match your filters</div>';
                return;
            }}

            let html = '';
            filteredPicks.forEach(pick => {{
                // Format game date
                let gameTime = 'TBD';
                if (pick.game_date) {{
                    try {{
                        const date = new Date(pick.game_date);
                        gameTime = date.toLocaleString('en-US', {{
                            month: '2-digit',
                            day: '2-digit',
                            hour: 'numeric',
                            minute: '2-digit',
                            hour12: true
                        }});
                    }} catch (e) {{
                        gameTime = pick.game_date;
                    }}
                }}

                // Build performance history HTML
                let perfHTML = '';
                if (pick.team_performance && Object.keys(pick.team_performance).length > 0) {{
                    perfHTML = '<div class="team-performance"><div class="perf-title">📊 YOUR BETTING RECORD ON THESE TEAMS</div><div class="perf-stats">';
                    for (const [team, stats] of Object.entries(pick.team_performance)) {{
                        const profitClass = stats.profit >= 0 ? 'positive' : 'negative';

                        // Determine hot/cold status
                        let tempIcon = '';
                        let tempColor = '';
                        if (stats.win_rate >= 60) {{
                            tempIcon = '🔥 HOT';
                            tempColor = '#10b981';
                        }} else if (stats.win_rate >= 55) {{
                            tempIcon = '✅ GOOD';
                            tempColor = '#3b82f6';
                        }} else if (stats.win_rate <= 45) {{
                            tempIcon = '❄️ COLD';
                            tempColor = '#ef4444';
                        }} else {{
                            tempIcon = '➖ NEUTRAL';
                            tempColor = '#9ca3af';
                        }}

                        perfHTML += `
                            <div class="perf-item">
                                <span class="perf-team">${{team}}</span>
                                <span class="perf-record">${{stats.record}}</span>
                                <span class="perf-winrate">${{stats.win_rate.toFixed(1)}}% WR</span>
                                <span class="perf-profit ${{profitClass}}">${{stats.profit >= 0 ? '+' : ''}}${{(stats.profit/100).toFixed(2)}}u</span>
                                <span style="color: ${{tempColor}}; font-size: 0.75rem; font-weight: 700; margin-top: 0.25rem;">${{tempIcon}}</span>
                            </div>
                        `;
                    }}
                    perfHTML += '</div></div>';
                }}

                // Edge or AI score display
                let scoreHTML = '';
                if (pick.ai_score) {{
                    scoreHTML = `<div class="pick-row">
                        <span class="pick-label">AI Score</span>
                        <span class="pick-value edge">${{pick.ai_score.toFixed(2)}}/10</span>
                    </div>`;
                }}
                if (pick.edge) {{
                    scoreHTML += `<div class="pick-row">
                        <span class="pick-label">Edge</span>
                        <span class="pick-value edge">${{pick.edge >= 0 ? '+' : ''}}${{pick.edge.toFixed(1)}} pts</span>
                    </div>`;
                }}

                // Result/Profit display
                let resultHTML = '';
                if (pick.status !== 'pending') {{
                    resultHTML = `<div class="pick-row">
                        <span class="pick-label">Result</span>
                        <span class="pick-value">${{pick.result || pick.status.toUpperCase()}}</span>
                    </div>
                    <div class="pick-row">
                        <span class="pick-label">P/L</span>
                        <span class="pick-value" style="color: ${{pick.profit_loss >= 0 ? '#10b981' : '#ef4444'}}">${{pick.profit_loss >= 0 ? '+' : ''}}${{(pick.profit_loss/100).toFixed(2)}}u</span>
                    </div>`;
                }}

                html += `
                    <div class="pick-card">
                        <div class="pick-header">
                            <span class="sport-badge ${{pick.sport.toLowerCase()}}">${{pick.sport}}</span>
                            <span class="sport-badge" style="background: #2a2a2a; color: #e2e8f0;">${{pick.pick_type}}</span>
                            <span class="status-badge ${{pick.status}}">${{pick.status.toUpperCase()}}</span>
                        </div>
                        <div class="matchup">${{pick.matchup}}</div>
                        <div class="pick-value pick-text" style="font-size: 1.25rem; margin: 0.75rem 0; text-align: center;">${{pick.pick_description}}</div>
                        <div class="game-time">🕐 ${{gameTime}}</div>
                        <div class="pick-details">
                            <div class="pick-row">
                                <span class="pick-label">Odds</span>
                                <span class="pick-value">${{pick.odds >= 0 ? '+' : ''}}${{pick.odds}}</span>
                            </div>
                            ${{scoreHTML}}
                            ${{resultHTML}}
                        </div>
                        ${{perfHTML}}
                    </div>
                `;
            }});

            container.innerHTML = html;
        }}

        // Initialize on page load
        init();
    </script>
</body>
</html>"""

    return html

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}PREMIUM DASHBOARD GENERATOR{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

    # Load data
    picks = load_tracking_data()
    stats = calculate_overall_stats(picks)

    print(f"\n{Colors.BOLD}{Colors.GREEN}OVERALL STATS{Colors.END}")
    print(f"Total Picks: {stats['total']}")
    print(f"Record: {stats['record']} ({stats['win_rate']:.1f}%)")
    print(f"Pending: {stats['pending']}")
    print(f"P/L: {stats['profit_loss']/100:+.0f}u\n")

    # Generate HTML
    print(f"{Colors.CYAN}Generating premium dashboard...{Colors.END}")
    html = generate_html(picks, stats)

    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)

    print(f"{Colors.GREEN}✓ Premium dashboard saved: {OUTPUT_HTML}{Colors.END}")
    print(f"\n{Colors.YELLOW}Open the file in your browser - NO SERVER NEEDED!{Colors.END}\n")

if __name__ == "__main__":
    main()
