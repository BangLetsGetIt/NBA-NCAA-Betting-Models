#!/usr/bin/env python3
"""
Unified Sports Betting Dashboard
Aggregates picks from all models (NBA, NCAA, MLB, CFB, Props) into one interface
Similar to DGFantasy optimizer
"""

import json
import os
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "unified_dashboard.html")

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
    """
    Normalize different pick formats into a unified structure
    """
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

    # Handle spread/total picks (NBA/NCAA/MLB/CFB)
    if model_type == 'spreads_totals':
        normalized.update({
            'game_date': pick.get('game_date'),
            'matchup': pick.get('matchup', f"{pick.get('away_team', '')} @ {pick.get('home_team', '')}"),
            'pick_description': pick.get('pick', ''),
            'odds': -110,  # Standard odds for spreads/totals
            'edge': pick.get('edge'),
            'pick_type': pick.get('pick_type', 'Unknown')
        })

    # Handle player props (3PT, etc.)
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
            'pick_type': 'Player Prop'
        })

    return normalized

def aggregate_all_picks():
    """
    Aggregate picks from all models
    Returns: dict with picks organized by sport and overall stats
    """
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}UNIFIED DASHBOARD - Aggregating All Models{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}\n")

    all_picks = []
    sport_summaries = {}

    # Process each sport
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

            # Normalize and add to collection
            for pick in picks:
                normalized = normalize_pick_format(pick, sport, model_type)
                sport_picks.append(normalized)
                all_picks.append(normalized)

        # Calculate sport summary
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

    # Calculate overall summary
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

def filter_picks(picks, filters):
    """
    Filter picks based on criteria
    filters = {
        'sport': 'NBA' | 'NCAA' | 'ALL',
        'status': 'pending' | 'completed' | 'all',
        'model_type': 'spreads_totals' | '3pt_props' | 'all',
        'min_ai_score': float (for props),
        'min_edge': float (for spreads/totals)
    }
    """
    filtered = picks

    # Filter by sport
    if filters.get('sport') and filters['sport'] != 'ALL':
        filtered = [p for p in filtered if p['sport'] == filters['sport']]

    # Filter by status
    if filters.get('status') == 'pending':
        filtered = [p for p in filtered if p['status'] == 'pending']
    elif filters.get('status') == 'completed':
        filtered = [p for p in filtered if p['status'] in ['win', 'loss']]

    # Filter by model type
    if filters.get('model_type') and filters['model_type'] != 'all':
        filtered = [p for p in filtered if p['model_type'] == filters['model_type']]

    # Filter by AI score (for props)
    if filters.get('min_ai_score'):
        filtered = [p for p in filtered if p.get('ai_score', 0) >= filters['min_ai_score']]

    # Filter by edge (for spreads/totals)
    if filters.get('min_edge'):
        filtered = [p for p in filtered if abs(p.get('edge', 0)) >= filters['min_edge']]

    return filtered

def get_today_picks(picks):
    """Get picks for today's games"""
    et = pytz.timezone('US/Eastern')
    today = datetime.now(et).date()

    today_picks = []
    for pick in picks:
        if pick.get('game_date'):
            try:
                game_dt = datetime.fromisoformat(pick['game_date'].replace('Z', '+00:00'))
                game_dt_et = game_dt.astimezone(et)
                if game_dt_et.date() == today:
                    today_picks.append(pick)
            except:
                continue

    return today_picks

def generate_unified_html(data):
    """
    Generate beautiful unified dashboard HTML
    """
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    date_str = now.strftime('%B %d, %Y %I:%M %p ET')

    picks = data['picks']
    sport_summaries = data['sport_summaries']
    overall = data['overall_summary']

    # Get today's picks
    today_picks = get_today_picks(picks)
    pending_picks = [p for p in picks if p['status'] == 'pending']

    # Sort pending picks by AI score (if available) or edge
    pending_picks.sort(key=lambda x: x.get('ai_score') or abs(x.get('edge', 0) or 0), reverse=True)

    # Group picks by sport
    picks_by_sport = defaultdict(list)
    for pick in pending_picks:
        picks_by_sport[pick['sport']].append(pick)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unified Sports Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1d3a 50%, #0f1419 100%);
            color: #ffffff;
            padding: 2rem;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%);
            border-radius: 1.5rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }}

        .header h1 {{
            font-size: 3rem;
            font-weight: 900;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 3px;
        }}

        .header .subtitle {{
            font-size: 1.2rem;
            color: #94a3b8;
            font-weight: 500;
        }}

        .header .timestamp {{
            margin-top: 1rem;
            font-size: 0.95rem;
            color: #64748b;
            font-weight: 400;
        }}

        /* Overall Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 1rem;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(59, 130, 246, 0.5);
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.2);
        }}

        .stat-value {{
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }}

        .stat-label {{
            font-size: 0.9rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-card.profit .stat-value {{
            color: #10b981;
        }}

        .stat-card.loss .stat-value {{
            color: #ef4444;
        }}

        .stat-card.pending .stat-value {{
            color: #f59e0b;
        }}

        .stat-card.winrate .stat-value {{
            color: #3b82f6;
        }}

        /* Sport Sections */
        .sport-section {{
            margin-bottom: 3rem;
        }}

        .sport-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 2rem;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(147, 51, 234, 0.15) 100%);
            border-radius: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}

        .sport-title {{
            font-size: 2rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .sport-stats {{
            display: flex;
            gap: 2rem;
            font-size: 0.95rem;
        }}

        .sport-stat {{
            text-align: center;
        }}

        .sport-stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
        }}

        .sport-stat-label {{
            color: #94a3b8;
            font-size: 0.85rem;
        }}

        /* Picks Table */
        .picks-table {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 1rem;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        thead {{
            background: rgba(0, 0, 0, 0.3);
        }}

        th {{
            padding: 1.25rem;
            text-align: left;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 1px;
            color: #94a3b8;
            border-bottom: 2px solid rgba(59, 130, 246, 0.3);
        }}

        td {{
            padding: 1.25rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 0.95rem;
        }}

        tbody tr {{
            transition: all 0.2s ease;
        }}

        tbody tr:hover {{
            background: rgba(59, 130, 246, 0.1);
        }}

        .matchup {{
            font-weight: 600;
            color: #e2e8f0;
        }}

        .pick-desc {{
            font-weight: 700;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            display: inline-block;
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.2) 100%);
            color: #10b981;
        }}

        .pick-type {{
            padding: 0.4rem 0.8rem;
            border-radius: 0.5rem;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-block;
        }}

        .pick-type.spread {{
            background: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
        }}

        .pick-type.total {{
            background: rgba(147, 51, 234, 0.2);
            color: #a78bfa;
        }}

        .pick-type.prop {{
            background: rgba(236, 72, 153, 0.2);
            color: #ec4899;
        }}

        .score-badge {{
            font-size: 1.5rem;
            font-weight: 800;
            color: #10b981;
        }}

        .edge-badge {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #f59e0b;
        }}

        .odds {{
            font-weight: 600;
            color: #94a3b8;
        }}

        .no-picks {{
            text-align: center;
            padding: 3rem;
            color: #64748b;
            font-size: 1.1rem;
        }}

        /* Filters */
        .filters {{
            background: rgba(255, 255, 255, 0.05);
            padding: 2rem;
            border-radius: 1rem;
            margin-bottom: 3rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .filter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }}

        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .filter-label {{
            font-size: 0.9rem;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        select {{
            padding: 0.75rem;
            border-radius: 0.5rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        select:hover {{
            border-color: rgba(59, 130, 246, 0.5);
        }}

        select:focus {{
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .sport-header {{
                flex-direction: column;
                gap: 1rem;
            }}

            .sport-stats {{
                width: 100%;
                justify-content: space-around;
            }}

            th, td {{
                padding: 0.75rem 0.5rem;
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Unified Sports Dashboard</h1>
            <div class="subtitle">All Your Models. One Platform.</div>
            <div class="timestamp">Last Updated: {date_str}</div>
        </div>

        <!-- Overall Stats -->
        <div class="stats-grid">
            <div class="stat-card pending">
                <div class="stat-value">{overall['pending']}</div>
                <div class="stat-label">Active Picks</div>
            </div>
            <div class="stat-card winrate">
                <div class="stat-value">{overall['win_rate']:.1f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card {'profit' if overall['profit_loss'] >= 0 else 'loss'}">
                <div class="stat-value">{overall['profit_loss']:+.0f}u</div>
                <div class="stat-label">Total P/L</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{overall['total']}</div>
                <div class="stat-label">All-Time Picks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{overall['wins']}-{overall['losses']}</div>
                <div class="stat-label">Record</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(today_picks)}</div>
                <div class="stat-label">Today's Games</div>
            </div>
        </div>
"""

    # Add each sport section
    for sport in ['NBA', 'NCAA', 'MLB', 'CFB']:
        if sport not in picks_by_sport or not picks_by_sport[sport]:
            continue

        sport_picks = picks_by_sport[sport]
        summary = sport_summaries.get(sport, {})

        html += f"""
        <div class="sport-section">
            <div class="sport-header">
                <div class="sport-title">{sport}</div>
                <div class="sport-stats">
                    <div class="sport-stat">
                        <div class="sport-stat-value">{summary.get('pending', 0)}</div>
                        <div class="sport-stat-label">Pending</div>
                    </div>
                    <div class="sport-stat">
                        <div class="sport-stat-value">{summary.get('win_rate', 0):.1f}%</div>
                        <div class="sport-stat-label">Win Rate</div>
                    </div>
                    <div class="sport-stat">
                        <div class="sport-stat-value">{summary.get('wins', 0)}-{summary.get('losses', 0)}</div>
                        <div class="sport-stat-label">Record</div>
                    </div>
                </div>
            </div>

            <div class="picks-table">
                <table>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Matchup</th>
                            <th>Pick</th>
                            <th>Odds</th>
                            <th>Score/Edge</th>
                        </tr>
                    </thead>
                    <tbody>"""

        for pick in sport_picks[:20]:  # Limit to top 20 per sport
            # Determine pick type styling
            pick_type = pick.get('pick_type', 'Unknown')
            type_class = 'prop' if 'Prop' in pick_type else ('spread' if 'Spread' in pick_type else 'total')

            # Format odds
            odds = pick.get('odds')
            odds_str = f"{odds:+d}" if odds else "N/A"

            # Score or edge
            score_display = ""
            if pick.get('ai_score'):
                score_display = f'<span class="score-badge">{pick["ai_score"]:.2f}</span>'
            elif pick.get('edge'):
                score_display = f'<span class="edge-badge">{abs(pick["edge"]):.1f}</span>'

            html += f"""
                        <tr>
                            <td><span class="pick-type {type_class}">{pick_type}</span></td>
                            <td class="matchup">{pick['matchup']}</td>
                            <td><span class="pick-desc">{pick['pick_description']}</span></td>
                            <td class="odds">{odds_str}</td>
                            <td>{score_display}</td>
                        </tr>"""

        html += """
                    </tbody>
                </table>
            </div>
        </div>"""

    html += """
    </div>
</body>
</html>"""

    return html

def save_html(html_content):
    """Save HTML to file"""
    try:
        with open(OUTPUT_HTML, 'w') as f:
            f.write(html_content)
        print(f"\n{Colors.GREEN}✓ Dashboard saved: {OUTPUT_HTML}{Colors.END}")
        return True
    except Exception as e:
        print(f"\n{Colors.RED}✗ Error saving HTML: {e}{Colors.END}")
        return False

def main():
    """Main execution"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}UNIFIED SPORTS DASHBOARD GENERATOR{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    # Aggregate all data
    data = aggregate_all_picks()

    # Display summary
    print(f"\n{Colors.BOLD}{Colors.GREEN}OVERALL SUMMARY{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    overall = data['overall_summary']
    print(f"Total Picks: {overall['total']}")
    print(f"Record: {overall['wins']}-{overall['losses']} ({overall['win_rate']:.1f}%)")
    print(f"Pending: {overall['pending']}")
    print(f"Profit/Loss: {overall['profit_loss']:+.0f}u")

    print(f"\n{Colors.BOLD}{Colors.GREEN}BY SPORT{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    for sport, summary in data['sport_summaries'].items():
        print(f"{sport:8s} | {summary['wins']:3d}-{summary['losses']:<3d} | "
              f"{summary['win_rate']:5.1f}% | Pending: {summary['pending']:3d} | "
              f"P/L: {summary['profit_loss']:+6.0f}u")

    # Generate HTML
    print(f"\n{Colors.CYAN}Generating unified dashboard...{Colors.END}")
    html = generate_unified_html(data)
    save_html(html)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Dashboard generation complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")

if __name__ == "__main__":
    main()
