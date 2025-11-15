#!/usr/bin/env python3
"""
NBA TRACKING - CORRECTED VERSION
Reads from nba_picks_tracking.json and generates dashboard with CORRECT stats
"""

import json
import os
from datetime import datetime

def load_tracking_data():
    """Load picks tracking data"""
    file = 'nba_picks_tracking.json'
    
    if not os.path.exists(file):
        print(f"❌ File not found: {file}")
        print(f"Looking for: {os.path.abspath(file)}")
        return None
    
    with open(file, 'r') as f:
        data = json.load(f)
    
    return data

def calculate_correct_stats(picks):
    """Calculate stats ONLY from completed picks"""
    
    # Separate by status
    completed_picks = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
    pending_picks = [p for p in picks if p.get('status', '').lower() == 'pending']
    
    if not completed_picks:
        return {
            'total_completed': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'win_rate': 0.0,
            'profit': 0.0,
            'roi': 0.0,
            'pending_count': len(pending_picks)
        }
    
    # Count results
    wins = sum(1 for p in completed_picks if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in completed_picks if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in completed_picks if p.get('status', '').lower() == 'push')
    
    # Calculate stats
    decisive = wins + losses
    win_rate = (wins / decisive * 100) if decisive > 0 else 0

    # Calculate profit (in cents, then convert to units)
    total_profit_cents = sum(p.get('profit_loss', 0) for p in completed_picks)
    profit_units = total_profit_cents / 100
    
    # ROI
    total_completed = len(completed_picks)
    roi = (profit_units / total_completed * 100) if total_completed > 0 else 0
    
    return {
        'total_completed': total_completed,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'pending_count': len(pending_picks)
    }

def generate_html(picks, stats):
    """Generate corrected HTML dashboard"""
    
    # Separate picks
    pending = [p for p in picks if p.get('status', '').lower() == 'pending']
    completed = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]

    # Sort: pending by date, completed by date descending
    pending.sort(key=lambda x: x.get('game_date', ''))
    completed.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Bet Tracking Dashboard - CORRECTED</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            padding: 2rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .card {{ 
            background: #1a1a1a; 
            border-radius: 1rem; 
            border: 1px solid #2a2a2a;
            padding: 2rem;
            margin-bottom: 1.5rem;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
            border: 2px solid #fbbf24;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 900;
            color: #fbbf24;
        }}
        .stat-value.positive {{ color: #10b981; }}
        .stat-value.negative {{ color: #ef4444; }}
        .stat-label {{
            color: #9ca3af;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        h1 {{ font-size: 2.5rem; font-weight: 900; margin-bottom: 0.5rem; color: #fbbf24; }}
        h2 {{ font-size: 1.875rem; font-weight: 700; margin-bottom: 1.5rem; color: #fbbf24; }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead {{ background: #0a0a0a; }}
        th {{ padding: 0.75rem 1rem; text-align: left; color: #fbbf24; font-weight: 700; }}
        td {{ padding: 0.75rem 1rem; border-bottom: 1px solid #2a2a2a; }}
        tr:hover {{ background: #0a0a0a; }}
        .text-center {{ text-align: center; }}
        .text-green-400 {{ color: #10b981; }}
        .text-red-400 {{ color: #ef4444; }}
        .text-yellow-400 {{ color: #fbbf24; }}
        .text-gray-400 {{ color: #9ca3af; }}
        .font-bold {{ font-weight: 700; }}
        .text-sm {{ font-size: 0.875rem; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .badge-pending {{ background: #78350f; color: #fbbf24; }}
        .badge-win {{ background: #064e3b; color: #10b981; }}
        .badge-loss {{ background: #450a0a; color: #ef4444; }}
        .badge-push {{ background: #374151; color: #9ca3af; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">🏀 NBA BET TRACKING - CORRECTED</h1>
            <p class="text-center text-gray-400" style="font-size: 1.25rem; margin-bottom: 2rem;">Performance Analytics Dashboard</p>
            
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['total_completed']}</div>
                    <div class="stat-label">Completed Bets</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['win_rate']:.1f}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {'positive' if stats['profit'] > 0 else 'negative' if stats['profit'] < 0 else ''}">
                        {'+' if stats['profit'] > 0 else ''}{stats['profit']:.2f}u
                    </div>
                    <div class="stat-label">Total Profit</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {'positive' if stats['roi'] > 0 else 'negative' if stats['roi'] < 0 else ''}">
                        {'+' if stats['roi'] > 0 else ''}{stats['roi']:.1f}%
                    </div>
                    <div class="stat-label">ROI</div>
                </div>
            </div>
            
            <div style="background: #0a0a0a; border-radius: 0.5rem; padding: 1rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; text-align: center;">
                <div>
                    <span class="text-gray-400">Wins:</span>
                    <span class="text-green-400 font-bold" style="margin-left: 0.5rem;">{stats['wins']}</span>
                </div>
                <div>
                    <span class="text-gray-400">Losses:</span>
                    <span class="text-red-400 font-bold" style="margin-left: 0.5rem;">{stats['losses']}</span>
                </div>
                <div>
                    <span class="text-gray-400">Pushes:</span>
                    <span class="text-gray-400 font-bold" style="margin-left: 0.5rem;">{stats['pushes']}</span>
                </div>
                <div>
                    <span class="text-gray-400">Pending:</span>
                    <span class="text-yellow-400 font-bold" style="margin-left: 0.5rem;">{stats['pending_count']}</span>
                </div>
            </div>
        </div>
"""

    # Pending section
    if pending:
        html += f"""
        <div class="card">
            <h2>🎯 Upcoming Bets ({len(pending)})</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for pick in pending:
            game_time = pick.get('game_date', 'TBD')[:16].replace('T', ' ')
            matchup = f"{pick.get('away_team', 'TBD')} @ {pick.get('home_team', 'TBD')}"
            pick_type = pick.get('pick_type', 'Unknown')
            pick_text = pick.get('pick_text', pick.get('pick', 'N/A'))
            
            html += f"""
                        <tr>
                            <td class="text-sm font-bold">{game_time}</td>
                            <td class="font-bold">{matchup}</td>
                            <td>{pick_type}</td>
                            <td class="text-yellow-400">{pick_text}</td>
                            <td><span class="badge badge-pending">Pending</span></td>
                        </tr>
"""
        html += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Completed section
    if completed:
        html += f"""
        <div class="card">
            <h2>📊 Completed Bets ({len(completed)})</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Score</th>
                            <th>Profit</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for pick in completed:
            game_time = pick.get('game_date', 'TBD')[:16].replace('T', ' ')
            matchup = f"{pick.get('away_team', 'TBD')} @ {pick.get('home_team', 'TBD')}"
            pick_type = pick.get('pick_type', 'Unknown')
            pick_text = pick.get('pick_text', pick.get('pick', 'N/A'))

            # Build score string
            away_score = pick.get('actual_away_score', 'N/A')
            home_score = pick.get('actual_home_score', 'N/A')
            score = f"{away_score}-{home_score}" if away_score != 'N/A' else 'N/A'

            status = pick.get('status', 'unknown').lower()
            status_class = status if status in ['win', 'loss', 'push'] else 'pending'
            status_display = status.capitalize()

            profit_cents = pick.get('profit_loss', 0)
            profit_units = profit_cents / 100
            profit_color = 'text-green-400' if profit_cents > 0 else 'text-red-400' if profit_cents < 0 else 'text-gray-400'
            profit_text = f"{'+' if profit_units > 0 else ''}{profit_units:.2f}u"
            
            html += f"""
                        <tr>
                            <td class="text-sm font-bold">{game_time}</td>
                            <td class="font-bold">{matchup}</td>
                            <td>{pick_type}</td>
                            <td class="text-sm">{pick_text}</td>
                            <td class="text-sm text-gray-400">{score}</td>
                            <td class="font-bold {profit_color}">{profit_text}</td>
                            <td><span class="badge badge-{status_class}">{status_display}</span></td>
                        </tr>
"""
        html += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Footer
    current_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    html += f"""
        <div class="text-center text-gray-400 text-sm" style="margin-top: 2rem;">
            <p>Last updated: {current_time}</p>
            <p style="margin-top: 0.5rem;">✅ Stats calculated from completed bets only</p>
        </div>
    </div>
</body>
</html>"""
    
    return html

def main():
    print("\n" + "="*60)
    print("🏀 NBA TRACKING DASHBOARD - CORRECTED VERSION")
    print("="*60 + "\n")
    
    # Load data
    data = load_tracking_data()
    if not data:
        return
    
    picks = data.get('picks', [])
    if not picks:
        print("❌ No picks found in tracking data")
        return
    
    print(f"📊 Loaded {len(picks)} total picks")
    
    # Calculate corrected stats
    stats = calculate_correct_stats(picks)
    
    print(f"\n✅ CORRECTED STATS:")
    print(f"   Completed Bets: {stats['total_completed']}")
    print(f"   Pending Bets: {stats['pending_count']}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Total Profit: {stats['profit']:+.2f}u")
    print(f"   ROI: {stats['roi']:+.1f}%")
    print(f"   Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}")
    
    # Generate HTML
    html = generate_html(picks, stats)
    
    # Save
    output_file = 'nba_tracking_dashboard.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated: {output_file}")
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
