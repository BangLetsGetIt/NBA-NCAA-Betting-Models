import pandas as pd
from datetime import datetime
import json
import os

def load_bet_history():
    """Load bet history from JSON file"""
    history_file = 'nba_bet_history.json'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return json.load(f)
    return []

def calculate_stats(bets_df):
    """Calculate stats ONLY from completed bets"""
    # Filter to ONLY completed bets (not pending)
    completed = bets_df[bets_df['Status'].isin(['Win', 'Loss', 'Push'])].copy()
    
    if len(completed) == 0:
        return {
            'total_bets': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'roi': 0.0
        }
    
    wins = len(completed[completed['Status'] == 'Win'])
    losses = len(completed[completed['Status'] == 'Loss'])
    pushes = len(completed[completed['Status'] == 'Push'])
    
    # Calculate win rate excluding pushes
    decisive_bets = wins + losses
    win_rate = (wins / decisive_bets * 100) if decisive_bets > 0 else 0
    
    # Calculate profit (assuming 1u bets at -110 odds)
    total_profit = (wins * 0.91) - (losses * 1.0)
    
    # Calculate ROI
    total_risk = len(completed) * 1.0
    roi = (total_profit / total_risk * 100) if total_risk > 0 else 0
    
    return {
        'total_bets': len(completed),  # ONLY completed bets
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'roi': roi
    }

def generate_dashboard_html(bets_df, stats):
    """Generate the tracking dashboard HTML"""
    
    # Separate pending and completed bets
    pending = bets_df[bets_df['Status'] == 'Pending'].copy()
    completed = bets_df[bets_df['Status'].isin(['Win', 'Loss', 'Push'])].copy()
    
    # Sort: pending by date ascending, completed by date descending
    pending = pending.sort_values('Game Date')
    completed = completed.sort_values('Game Date', ascending=False)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Bet Tracking Dashboard</title>
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
            <h1 class="text-center">🏀 NBA BET TRACKING</h1>
            <p class="text-center text-gray-400" style="font-size: 1.25rem; margin-bottom: 2rem;">Performance Analytics Dashboard</p>
            
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['total_bets']}</div>
                    <div class="stat-label">Completed Bets</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['win_rate']:.1f}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {'positive' if stats['total_profit'] > 0 else 'negative' if stats['total_profit'] < 0 else ''}">
                        {'+' if stats['total_profit'] > 0 else ''}{stats['total_profit']:.2f}u
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
            
            <div style="background: #0a0a0a; border-radius: 0.5rem; padding: 1rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; text-align: center;">
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
            </div>
        </div>
"""

    # Pending bets section
    if len(pending) > 0:
        html += """
        <div class="card">
            <h2>🎯 Upcoming Bets</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Line</th>
                            <th>Edge</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for _, bet in pending.iterrows():
            html += f"""
                        <tr>
                            <td class="text-sm font-bold">{bet['Game Date']}</td>
                            <td class="font-bold">{bet['Game']}</td>
                            <td>{bet['Type']}</td>
                            <td class="text-yellow-400">{bet['Pick']}</td>
                            <td>{bet['Line']}</td>
                            <td>{bet['Edge']}</td>
                            <td><span class="badge badge-pending">Pending</span></td>
                        </tr>
"""
        html += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Completed bets section
    if len(completed) > 0:
        html += """
        <div class="card">
            <h2>📊 Completed Bets</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Result</th>
                            <th>Margin</th>
                            <th>Profit</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for _, bet in completed.iterrows():
            status_class = 'win' if bet['Status'] == 'Win' else 'loss' if bet['Status'] == 'Loss' else 'push'
            profit_color = 'text-green-400' if bet['Status'] == 'Win' else 'text-red-400' if bet['Status'] == 'Loss' else 'text-gray-400'
            
            profit = bet.get('Profit', '+0.91u' if bet['Status'] == 'Win' else '-1.00u' if bet['Status'] == 'Loss' else '0.00u')
            
            html += f"""
                        <tr>
                            <td class="text-sm font-bold">{bet['Game Date']}</td>
                            <td class="font-bold">{bet['Game']}</td>
                            <td>{bet['Type']}</td>
                            <td class="text-sm">{bet['Pick']}</td>
                            <td class="text-sm text-gray-400">{bet.get('Result', '')}</td>
                            <td class="text-sm text-gray-400">{bet.get('Margin', '')}</td>
                            <td class="font-bold {profit_color}">{profit}</td>
                            <td><span class="badge badge-{status_class}">{bet['Status']}</span></td>
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
        </div>
    </div>
</body>
</html>"""
    
    return html

def main():
    """Main function to generate tracking dashboard"""
    # Load bet history
    bets = load_bet_history()
    
    if not bets:
        print("No bet history found. Create nba_bet_history.json first.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(bets)
    
    # Calculate stats (only from completed bets)
    stats = calculate_stats(df)
    
    # Generate HTML
    html = generate_dashboard_html(df, stats)
    
    # Save to file
    output_file = 'nba_tracking_dashboard.html'
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Dashboard generated: {output_file}")
    print(f"\nStats Summary:")
    print(f"  Completed Bets: {stats['total_bets']}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Total Profit: {stats['total_profit']:+.2f}u")
    print(f"  ROI: {stats['roi']:+.1f}%")
    print(f"  Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}")

if __name__ == "__main__":
    main()
