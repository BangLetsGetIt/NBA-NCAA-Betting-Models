#!/usr/bin/env python3
"""
Interactive Unified Sports Betting Dashboard
Similar to DGFantasy - with live filtering, sorting, and parlay builder
"""

import json
import os
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "unified_dashboard_interactive.html")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "unified_dashboard_data.json")

# Model tracking files
MODEL_FILES = {
    'NBA': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'nba', 'nba_picks_tracking.json'),
        '3pt_props': os.path.join(SCRIPT_DIR, 'nba', 'nba_3pt_props_tracking.json')
    },
    'NCAA': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'ncaa', 'ncaab_picks_tracking.json')
    },
    'MLB': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'mlb', 'mlb_picks_tracking.json') if os.path.exists(os.path.join(SCRIPT_DIR, 'mlb', 'mlb_picks_tracking.json')) else None
    },
    'CFB': {
        'spreads_totals': os.path.join(SCRIPT_DIR, 'cfb', 'cfb_picks_tracking.json') if os.path.exists(os.path.join(SCRIPT_DIR, 'cfb', 'cfb_picks_tracking.json')) else None
    }
}

# ANSI colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_model_data(file_path):
    """Load data from a model's tracking JSON file"""
    if not file_path or not os.path.exists(file_path):
        return None

    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{Colors.RED}✗ Error loading {file_path}: {e}{Colors.END}")
        return None

def normalize_pick_format(pick, sport, model_type):
    """Normalize different pick formats into a unified structure"""
    normalized = {
        'sport': sport,
        'model_type': model_type,
        'pick_id': pick.get('pick_id', ''),
        'status': pick.get('status', 'pending'),
        'game_date': None,
        'matchup': '',
        'pick_description': '',
        'odds': None,
        'edge': None,
        'ai_score': None,
        'result': pick.get('result'),
        'profit_loss': pick.get('profit_loss', 0)
    }

    # Handle spread/total picks
    if model_type == 'spreads_totals':
        # Clean up pick description - remove emoji and "BET:" prefix
        # NCAA uses 'pick_text', NBA uses 'pick'
        pick_text = pick.get('pick_text', pick.get('pick', ''))
        # Remove checkmark emoji and "BET:" prefix
        pick_text = pick_text.replace('✅', '').replace('❌', '')
        pick_text = pick_text.replace('BET:', '').strip()

        # Capitalize pick_type if it's lowercase (NCAA format)
        pick_type = pick.get('pick_type', 'Unknown')
        if pick_type and isinstance(pick_type, str):
            pick_type = pick_type.capitalize()

        normalized.update({
            'game_date': pick.get('game_date'),
            'matchup': pick.get('matchup', f"{pick.get('away_team', '')} @ {pick.get('home_team', '')}"),
            'pick_description': pick_text,
            'odds': -110,
            'edge': pick.get('edge'),
            'pick_type': pick_type,
            'home_team': pick.get('home_team'),
            'away_team': pick.get('away_team')
        })

    # Handle player props
    elif model_type == '3pt_props':
        player = pick.get('player', 'Unknown')
        prop_line = pick.get('prop_line', 0)
        bet_type = pick.get('bet_type', 'over').upper()
        team = pick.get('team', '')
        opponent = pick.get('opponent', '')

        normalized.update({
            'game_date': pick.get('game_time'),
            'matchup': f"{team} vs {opponent}",
            'pick_description': f"{player} {bet_type} {prop_line} 3PT",
            'odds': pick.get('odds', -110),
            'ai_score': pick.get('ai_score'),
            'pick_type': 'Player Prop',
            'player': player,
            'team': team
        })

    return normalized

def aggregate_all_picks():
    """Aggregate picks from all models"""
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}INTERACTIVE DASHBOARD - Aggregating All Models{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")

    all_picks = []
    sport_summaries = {}

    for sport, models in MODEL_FILES.items():
        print(f"{Colors.CYAN}Loading {sport} models...{Colors.END}")
        sport_picks = []

        for model_type, file_path in models.items():
            if not file_path:
                continue

            data = load_model_data(file_path)
            if not data or 'picks' not in data:
                continue

            picks = data['picks']
            print(f"  {Colors.GREEN}✓ {model_type}: {len(picks)} picks{Colors.END}")

            for pick in picks:
                normalized = normalize_pick_format(pick, sport, model_type)
                sport_picks.append(normalized)
                all_picks.append(normalized)

        if sport_picks:
            completed = [p for p in sport_picks if p['status'] in ['win', 'loss']]
            wins = [p for p in sport_picks if p['status'] == 'win']
            losses = [p for p in sport_picks if p['status'] == 'loss']
            pending = [p for p in sport_picks if p['status'] == 'pending']

            win_rate = (len(wins) / len(completed) * 100) if completed else 0
            total_profit = sum(p.get('profit_loss', 0) for p in sport_picks)

            sport_summaries[sport] = {
                'total': len(sport_picks),
                'wins': len(wins),
                'losses': len(losses),
                'pending': len(pending),
                'win_rate': win_rate,
                'profit_loss': total_profit
            }

    all_completed = [p for p in all_picks if p['status'] in ['win', 'loss']]
    all_wins = [p for p in all_picks if p['status'] == 'win']
    all_losses = [p for p in all_picks if p['status'] == 'loss']
    all_pending = [p for p in all_picks if p['status'] == 'pending']

    overall_summary = {
        'total': len(all_picks),
        'wins': len(all_wins),
        'losses': len(all_losses),
        'pending': len(all_pending),
        'win_rate': (len(all_wins) / len(all_completed) * 100) if all_completed else 0,
        'profit_loss': sum(p.get('profit_loss', 0) for p in all_picks)
    }

    print(f"\n{Colors.GREEN}✓ Aggregated {len(all_picks)} total picks across {len(sport_summaries)} sports{Colors.END}")

    return {
        'picks': all_picks,
        'sport_summaries': sport_summaries,
        'overall_summary': overall_summary,
        'generated_at': datetime.now(pytz.timezone('US/Eastern')).isoformat()
    }

def save_json_data(data):
    """Save data as JSON for JavaScript to load"""
    try:
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(data, indent=2, fp=f)
        print(f"{Colors.GREEN}✓ Data JSON saved: {OUTPUT_JSON}{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ Error saving JSON: {e}{Colors.END}")
        return False

def generate_interactive_html(data):
    """Generate interactive HTML with embedded data - no external JSON needed"""

    # Embed data directly in JavaScript
    embedded_data = json.dumps(data, indent=2)

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
            background: #000000;
            color: #e2e8f0;
            min-height: 100vh;
            padding: 2rem;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
        }}

        /* Header */
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

        .header .subtitle {{
            font-size: 1.1rem;
            color: #9ca3af;
        }}

        .header .timestamp {{
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.5rem;
        }}

        /* Stats Cards */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: #1a1a1a;
            padding: 1.5rem;
            border-radius: 0.75rem;
            text-align: center;
            border: 2px solid #2a2a2a;
            transition: all 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-3px);
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
            letter-spacing: 0.5px;
        }}

        .stat-card.profit .stat-value {{ color: #10b981; }}
        .stat-card.loss .stat-value {{ color: #ef4444; }}
        .stat-card.pending .stat-value {{ color: #fbbf24; }}
        .stat-card.winrate .stat-value {{ color: #3b82f6; }}

        /* Filters */
        .filters {
            background: rgba(255, 255, 255, 0.05);
            padding: 1.75rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .filter-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #64ffda;
            margin-bottom: 1.25rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .filter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.25rem;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .filter-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        select, input {
            padding: 0.75rem;
            border-radius: 0.5rem;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #ffffff;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        select:hover, input:hover {
            border-color: rgba(59, 130, 246, 0.5);
        }

        select:focus, input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }

        /* Picks Table */
        .picks-section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 1rem;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .section-header {
            background: rgba(0, 0, 0, 0.3);
            padding: 1.25rem 1.5rem;
            font-size: 1.3rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        thead {
            background: rgba(0, 0, 0, 0.2);
        }

        th {
            padding: 1rem;
            text-align: left;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
            color: #94a3b8;
            cursor: pointer;
            transition: color 0.2s ease;
        }

        th:hover {
            color: #3b82f6;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.9rem;
        }

        tbody tr {
            transition: all 0.2s ease;
        }

        tbody tr:hover {
            background: rgba(59, 130, 246, 0.08);
        }

        .sport-badge {
            padding: 0.35rem 0.75rem;
            border-radius: 0.4rem;
            font-size: 0.8rem;
            font-weight: 700;
            display: inline-block;
        }

        .sport-badge.nba { background: rgba(237, 100, 166, 0.2); color: #ec4899; }
        .sport-badge.ncaa { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .sport-badge.mlb { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .sport-badge.cfb { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }

        .pick-type {
            padding: 0.35rem 0.75rem;
            border-radius: 0.4rem;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
        }

        .pick-type.spread { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .pick-type.total { background: rgba(147, 51, 234, 0.2); color: #a78bfa; }
        .pick-type.prop { background: rgba(236, 72, 153, 0.2); color: #ec4899; }

        .matchup {
            font-weight: 600;
            color: #e2e8f0;
        }

        .pick-desc {
            font-weight: 700;
            color: #10b981;
        }

        .score-badge {
            font-size: 1.3rem;
            font-weight: 800;
            color: #10b981;
        }

        .edge-badge {
            font-size: 1.2rem;
            font-weight: 700;
            color: #f59e0b;
        }

        .odds {
            font-weight: 600;
            color: #94a3b8;
        }

        .no-results {
            padding: 3rem;
            text-align: center;
            color: #64748b;
            font-size: 1.1rem;
        }

        /* Parlay Builder */
        .parlay-builder {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: rgba(16, 185, 129, 0.95);
            padding: 1.5rem;
            border-radius: 1rem;
            min-width: 250px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(16, 185, 129, 0.3);
            display: none;
        }

        .parlay-builder.active {
            display: block;
        }

        .parlay-header {
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 1rem;
            color: #ffffff;
        }

        .parlay-count {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 0.5rem;
        }

        .parlay-odds {
            font-size: 1.5rem;
            font-weight: 800;
            color: #ffffff;
        }

        @media (max-width: 768px) {
            .header h1 { font-size: 1.8rem; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .filter-grid { grid-template-columns: 1fr; }
            th, td { padding: 0.75rem 0.5rem; font-size: 0.85rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Interactive Sports Dashboard</h1>
            <div class="subtitle">Filter, Sort, and Build Parlays</div>
        </div>

        <!-- Stats -->
        <div id="stats" class="stats-grid"></div>

        <!-- Filters -->
        <div class="filters">
            <div class="filter-title">Filter Picks</div>
            <div class="filter-grid">
                <div class="filter-group">
                    <label class="filter-label">Sport</label>
                    <select id="sportFilter">
                        <option value="all">All Sports</option>
                        <option value="NBA">NBA</option>
                        <option value="NCAA">NCAA</option>
                        <option value="MLB">MLB</option>
                        <option value="CFB">CFB</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Status</label>
                    <select id="statusFilter">
                        <option value="all" selected>All</option>
                        <option value="pending">Pending Only</option>
                        <option value="completed">Completed Only</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Pick Type</label>
                    <select id="typeFilter">
                        <option value="all">All Types</option>
                        <option value="Spread">Spreads</option>
                        <option value="Total">Totals</option>
                        <option value="Player Prop">Player Props</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">Min AI Score</label>
                    <input type="number" id="minScoreFilter" placeholder="e.g. 8.0" step="0.1" min="0" max="10">
                </div>
                <div class="filter-group">
                    <label class="filter-label">Min Edge</label>
                    <input type="number" id="minEdgeFilter" placeholder="e.g. 5.0" step="0.5" min="0">
                </div>
                <div class="filter-group">
                    <label class="filter-label">Search</label>
                    <input type="text" id="searchFilter" placeholder="Player, team, matchup...">
                </div>
            </div>
        </div>

        <!-- Picks Table -->
        <div class="picks-section">
            <div class="section-header">
                <span id="resultCount">0 Picks</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th onclick="sortTable('sport')">Sport ▼</th>
                        <th onclick="sortTable('type')">Type ▼</th>
                        <th onclick="sortTable('matchup')">Matchup ▼</th>
                        <th onclick="sortTable('pick')">Pick ▼</th>
                        <th onclick="sortTable('odds')">Odds ▼</th>
                        <th onclick="sortTable('score')">Score/Edge ▼</th>
                    </tr>
                </thead>
                <tbody id="picksTable"></tbody>
            </table>
        </div>
    </div>

    <script>
        let allPicks = [];
        let filteredPicks = [];
        let currentSort = { column: 'score', ascending: false };

        // Load data
        fetch('unified_dashboard_data.json')
            .then(res => res.json())
            .then(data => {
                allPicks = data.picks;
                updateStats(data.overall_summary);
                applyFilters();
            });

        // Update stats
        function updateStats(summary) {
            const statsHTML = `
                <div class="stat-card pending">
                    <div class="stat-value">${summary.pending}</div>
                    <div class="stat-label">Active Picks</div>
                </div>
                <div class="stat-card winrate">
                    <div class="stat-value">${summary.win_rate.toFixed(1)}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card ${summary.profit_loss >= 0 ? 'profit' : 'loss'}">
                    <div class="stat-value">${summary.profit_loss >= 0 ? '+' : ''}${summary.profit_loss.toFixed(0)}u</div>
                    <div class="stat-label">Total P/L</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${summary.total}</div>
                    <div class="stat-label">All-Time Picks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${summary.wins}-${summary.losses}</div>
                    <div class="stat-label">Record</div>
                </div>
            `;
            document.getElementById('stats').innerHTML = statsHTML;
        }

        // Apply filters
        function applyFilters() {
            const sport = document.getElementById('sportFilter').value;
            const status = document.getElementById('statusFilter').value;
            const type = document.getElementById('typeFilter').value;
            const minScore = parseFloat(document.getElementById('minScoreFilter').value) || 0;
            const minEdge = parseFloat(document.getElementById('minEdgeFilter').value) || 0;
            const search = document.getElementById('searchFilter').value.toLowerCase();

            filteredPicks = allPicks.filter(pick => {
                if (sport !== 'all' && pick.sport !== sport) return false;
                if (status === 'pending' && pick.status !== 'pending') return false;
                if (status === 'completed' && !['win', 'loss'].includes(pick.status)) return false;
                if (type !== 'all' && pick.pick_type !== type) return false;
                if (pick.ai_score && pick.ai_score < minScore) return false;
                if (pick.edge && Math.abs(pick.edge) < minEdge) return false;
                if (search && !JSON.stringify(pick).toLowerCase().includes(search)) return false;
                return true;
            });

            sortPicks();
            renderTable();
        }

        // Sort picks
        function sortTable(column) {
            if (currentSort.column === column) {
                currentSort.ascending = !currentSort.ascending;
            } else {
                currentSort.column = column;
                currentSort.ascending = false;
            }
            sortPicks();
            renderTable();
        }

        function sortPicks() {
            filteredPicks.sort((a, b) => {
                let aVal, bVal;

                switch(currentSort.column) {
                    case 'sport': aVal = a.sport; bVal = b.sport; break;
                    case 'type': aVal = a.pick_type; bVal = b.pick_type; break;
                    case 'matchup': aVal = a.matchup; bVal = b.matchup; break;
                    case 'pick': aVal = a.pick_description; bVal = b.pick_description; break;
                    case 'odds': aVal = a.odds || 0; bVal = b.odds || 0; break;
                    case 'score':
                        aVal = a.ai_score || Math.abs(a.edge || 0);
                        bVal = b.ai_score || Math.abs(b.edge || 0);
                        break;
                }

                if (aVal < bVal) return currentSort.ascending ? -1 : 1;
                if (aVal > bVal) return currentSort.ascending ? 1 : -1;
                return 0;
            });
        }

        // Render table
        function renderTable() {
            const tbody = document.getElementById('picksTable');
            document.getElementById('resultCount').textContent = `${filteredPicks.length} Picks`;

            if (filteredPicks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="no-results">No picks match your filters</td></tr>';
                return;
            }

            let html = '';
            filteredPicks.forEach(pick => {
                const sportClass = pick.sport.toLowerCase();
                const typeClass = pick.pick_type.toLowerCase().replace(' ', '-');
                const odds = pick.odds ? (pick.odds > 0 ? `+${pick.odds}` : pick.odds) : 'N/A';

                let scoreDisplay = '';
                if (pick.ai_score) {
                    scoreDisplay = `<span class="score-badge">${pick.ai_score.toFixed(2)}</span>`;
                } else if (pick.edge) {
                    scoreDisplay = `<span class="edge-badge">${Math.abs(pick.edge).toFixed(1)}</span>`;
                }

                html += `
                    <tr>
                        <td><span class="sport-badge ${sportClass}">${pick.sport}</span></td>
                        <td><span class="pick-type ${typeClass}">${pick.pick_type}</span></td>
                        <td class="matchup">${pick.matchup}</td>
                        <td class="pick-desc">${pick.pick_description}</td>
                        <td class="odds">${odds}</td>
                        <td>${scoreDisplay}</td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
        }

        // Add event listeners
        document.getElementById('sportFilter').addEventListener('change', applyFilters);
        document.getElementById('statusFilter').addEventListener('change', applyFilters);
        document.getElementById('typeFilter').addEventListener('change', applyFilters);
        document.getElementById('minScoreFilter').addEventListener('input', applyFilters);
        document.getElementById('minEdgeFilter').addEventListener('input', applyFilters);
        document.getElementById('searchFilter').addEventListener('input', applyFilters);
    </script>
</body>
</html>"""

    return html

def save_html(html_content):
    """Save HTML to file"""
    try:
        with open(OUTPUT_HTML, 'w') as f:
            f.write(html_content)
        print(f"{Colors.GREEN}✓ Interactive dashboard saved: {OUTPUT_HTML}{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ Error saving HTML: {e}{Colors.END}")
        return False

def main():
    """Main execution"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}INTERACTIVE DASHBOARD GENERATOR{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    # Aggregate data
    data = aggregate_all_picks()

    # Save JSON for JavaScript
    save_json_data(data)

    # Display summary
    print(f"\n{Colors.BOLD}{Colors.GREEN}OVERALL SUMMARY{Colors.END}")
    overall = data['overall_summary']
    print(f"Total Picks: {overall['total']}")
    print(f"Record: {overall['wins']}-{overall['losses']} ({overall['win_rate']:.1f}%)")
    print(f"Pending: {overall['pending']}")
    print(f"Profit/Loss: {overall['profit_loss']:+.0f}u")

    # Generate HTML
    print(f"\n{Colors.CYAN}Generating interactive dashboard...{Colors.END}")
    html = generate_interactive_html()
    save_html(html)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Interactive dashboard complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")
    print(f"{Colors.YELLOW}Open {OUTPUT_HTML} in your browser{Colors.END}\n")

if __name__ == "__main__":
    main()
