#!/usr/bin/env python3

import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# --- Configuration ---
# Match Prop_Model_Design.md colors
COLORS = {
    "bg": "#000000",
    "card": "#1a1a1a",
    "bet_box": "#262626",
    "win": "#10b981",
    "loss": "#ef4444",
    "text": "#ffffff",
    "secondary": "#94a3b8",
    "accent": "#3b82f6", # Blue for pushes
    "void": "#9ca3af"   # Gray for adds
}

class DailyRecapGenerator:
    def __init__(self, target_date):
        self.base_dir = Path("/Users/rico/Dev/sports-models")
        self.target_date = target_date
        self.all_picks = []
        self.tracking_files = [
            "nba/nba_picks_tracking.json",
            "nba/nba_points_props_tracking.json", 
            "nba/nba_rebounds_props_tracking.json",
            "nba/nba_assists_props_tracking.json",
            "nba/nba_3pt_props_tracking.json",
            "ncaa/ncaab_picks_tracking.json",
            "ncaa/cbb_rebounds_props_tracking.json",
            "soccer/soccer_picks_tracking.json",
            "wnba/wnba_model_tracking.json",
            "wnba/wnba_props_tracking.json",
            "ufc/data/ufc_picks.json",
            "best_plays_tracking.json"
        ]
        
    def load_data(self):
        """Load data from all tracking files and filter by date"""
        print(f"Loading data for date: {self.target_date}")
        daily_picks = [] # Initialize local list for collecting all raw picks
        
        for file_path in self.tracking_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'picks' in data:
                            picks = data['picks']
                        elif isinstance(data, list):
                            picks = data
                        else:
                            continue
                            
                        filtered_picks = []
                        for pick in picks:
                            # Normalize Date
                            # Check game_date, then game_time, then date
                            pick_date_str = ""
                            
                            # Helper to parse ISO format and adjust to ET (UTC-5)
                            def parse_iso(date_str):
                                try:
                                    if 'T' in date_str:
                                        # Handle potential trailing Z or offset
                                        # Simple approach: If time is < 05:00:00, it belongs to previous day
                                        # But let's do real datetime math
                                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                        # Convert to ET (Approximating as UTC-5 for simplicity, or use pytz if avail)
                                        # Since we don't know if pytz is here, subtract 5 hours
                                        et_dt = dt - timedelta(hours=5)
                                        return et_dt.strftime('%Y-%m-%d')
                                    else:
                                        return date_str
                                except:
                                    return ""

                            if pick.get('game_time'):
                                pick_date_str = parse_iso(pick.get('game_time'))
                            elif pick.get('game_date'):
                                # game_date is usually YYYY-MM-DD
                                pick_date_str = parse_iso(pick.get('game_date'))
                            elif pick.get('date'):
                                pick_date_str = pick.get('date')
                                
                            if pick_date_str == self.target_date:
                                pick['sport'] = self.get_sport(file_path)
                                pick['model'] = self.get_model_name(file_path)
                                pick['file_path'] = file_path
                                self.normalize_pick(pick)
                                daily_picks.append(pick) # Add to daily_picks for deduplication
                                
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        original_count = len(daily_picks)

        # Deduplication Logic
        # Key: (player/team, prop_line, bet_type, game_time)
        # We want to keep the one with the most recent 'last_updated' or 'tracked_at'
        unique_picks_map = {}
        for pick in daily_picks:
            # Create a unique key
            # Use specific fields that define the "bet"
            player = pick.get('player', pick.get('team', 'Unknown'))
            prop = pick.get('prop_line', '')
            btype = pick.get('bet_type', '')
            gtime = pick.get('game_time', '')
            
            # If main model (no player), maybe rely on pick_text or mismatch?
            # Let's try to be specific for props mostly as that's where duplicates likely are
            if pick.get('sport') == 'NBA' and (pick.get('player') or 'prop' in pick.get('model', '').lower()): # Refined condition for props
                 # Ignore prop line value for deduplication to handle CLV line moves
                 # Include model to distinguish between Points, Rebs, 3PT etc for same player
                 model = pick.get('model', 'unknown')
                 key = f"{player}_{model}_{btype}_{gtime}"
            else:
                 # For game picks, maybe Team + Opponent + Model + Type?
                 # Or just pick_id if available? 
                 # Let's use pick_id if available, otherwise construct key
                 if pick.get('pick_id'):
                     # Normalize pick_id: convert UTC timestamp to ET date to avoid near-midnight duplicates
                     # e.g., "Team1_Team2_2026-01-30T00:00:29Z_spread" -> "Team1_Team2_2026-01-29_spread" (in ET)
                     raw_id = pick['pick_id']
                     if 'T' in raw_id:
                         parts = raw_id.rsplit('_', 1)
                         if len(parts) == 2:
                             prefix, suffix = parts
                             idx = prefix.rfind('_')
                             if idx > 0:
                                 teams = prefix[:idx]
                                 ts = prefix[idx+1:]
                                 # Convert UTC to ET (subtract 5 hours)
                                 try:
                                     from datetime import datetime as dt_parse
                                     utc_dt = dt_parse.fromisoformat(ts.replace('Z', '+00:00'))
                                     et_dt = utc_dt - timedelta(hours=5)
                                     date_only = et_dt.strftime('%Y-%m-%d')
                                 except:
                                     date_only = ts.split('T')[0]
                                 key = f"{teams}_{date_only}_{suffix}"
                             else:
                                 key = raw_id
                         else:
                             key = raw_id
                     else:
                         key = raw_id
                 else:
                     # Fallback
                     key = f"{pick.get('team')}_{pick.get('opponent')}_{pick.get('model')}_{pick.get('pick_text')}"
            
            # Conflict resolution: prefer the one with result/status if the other is pending?
            # Or prefer the one with later timestamp?
            # Let's check if we already have this key
            if key in unique_picks_map:
                existing = unique_picks_map[key]
                # If existing is pending and new is final, take new
                if existing.get('status') == 'pending' and pick.get('status') != 'pending':
                    unique_picks_map[key] = pick
                # Else if both same status, maybe check timestamps if available?
                # For now, just overwriting might be okay if the order is chronological, 
                # but JSON order isn't guaranteed. 
                # Let's just trust that later entries in JSON/processing might be newer? 
                # Actually, let's look at 'last_updated'
                elif pick.get('last_updated') and existing.get('last_updated'):
                    # Assuming 'last_updated' is a string in a comparable format (e.g., ISO 8601)
                    if pick['last_updated'] > existing['last_updated']:
                         unique_picks_map[key] = pick
                # If no 'last_updated' or both have same status, prefer the one with a result over pending
                elif existing.get('status') == 'pending' and pick.get('status') != 'pending':
                    unique_picks_map[key] = pick
                # Otherwise, keep the existing one (first one encountered or already updated)
            else:
                unique_picks_map[key] = pick
                
        self.all_picks.extend(list(unique_picks_map.values()))
        print(f"Found {len(self.all_picks)} unique picks for {self.target_date} (from {original_count} raw)")

    def get_sport(self, file_path):
        if 'nba' in file_path: return 'NBA'
        if 'ncaa' in file_path or 'cbb' in file_path: return 'NCAAB'
        if 'soccer' in file_path: return 'Soccer'
        if 'ufc' in file_path: return 'UFC'
        if 'wnba' in file_path: return 'WNBA'
        return 'Other'

    def get_model_name(self, file_path):
        name = file_path.split('/')[-1].replace('_tracking.json', '').replace('_picks', '').replace('.json', '')
        return name.replace('_', ' ').title()

    def normalize_pick(self, pick):
        # Normalize Status
        status = pick.get('status', 'pending').lower()
        if status == 'won': pick['status'] = 'win'
        elif status == 'lost': pick['status'] = 'loss'
        elif status == 'void': pick['status'] = 'void'  # Keep void separate
        elif status == 'push': pick['status'] = 'push'
        
        # Calculate Profit/Loss if missing
        if 'profit_loss' not in pick:
            if pick['status'] in ['win', 'loss']:
                units = float(pick.get('recommended_bet_size_unit', 1))
                odds = float(pick.get('odds', -110))
                if pick['status'] == 'win':
                    if odds > 0: profit = (odds / 100) * units * 100
                    else: profit = (100 / abs(odds)) * units * 100
                    pick['profit_loss'] = profit
                elif pick['status'] == 'loss':
                    pick['profit_loss'] = - (units * 100)
            else:
                pick['profit_loss'] = 0

    def calculate_stats(self):
        stats = {
            'total': {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0},
            'by_model': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0, 'picks': []}),
            'by_sport': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0}),
        }
        
        for pick in self.all_picks:
            status = pick.get('status', 'pending')
            # Count pending? Maybe separate bucket. For now just completed.
            if status not in ['win', 'loss', 'push', 'void']: continue
            
            pl = float(pick.get('profit_loss', 0)) / 100.0 # Convert to units
            
            # Total
            if status == 'win': stats['total']['wins'] += 1
            elif status == 'loss': stats['total']['losses'] += 1
            elif status == 'push': stats['total']['pushes'] += 1
            elif status == 'void': stats['total']['voids'] += 1
            stats['total']['units'] += pl
            
            # By Model
            model = pick['model']
            if status == 'win': stats['by_model'][model]['wins'] += 1
            elif status == 'loss': stats['by_model'][model]['losses'] += 1
            elif status == 'push': stats['by_model'][model]['pushes'] += 1
            elif status == 'void': stats['by_model'][model]['voids'] += 1
            stats['by_model'][model]['units'] += pl
            # Enriched Pick Data for Display
            stats['by_model'][model]['picks'].append(pick)
            
            # By Sport
            sport = pick['sport']
            if status == 'win': stats['by_sport'][sport]['wins'] += 1
            elif status == 'loss': stats['by_sport'][sport]['losses'] += 1
            elif status == 'push': stats['by_sport'][sport]['pushes'] += 1
            elif status == 'void': stats['by_sport'][sport]['voids'] += 1
            stats['by_sport'][sport]['units'] += pl

        return stats

    def get_highlights(self, stats):
        # Best model
        sorted_models = sorted(stats['by_model'].items(), key=lambda x: x[1]['units'], reverse=True)
        best_model = sorted_models[0] if sorted_models else None
        worst_model = sorted_models[-1] if sorted_models else None
        
        return {
            'best_model': best_model,
            'worst_model': worst_model
        }

    def generate_html(self, stats):
        highlights = self.get_highlights(stats)
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Recap - {self.target_date}</title>
    <style>
        body {{
            background-color: {COLORS['bg']};
            color: {COLORS['text']};
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{
            max_width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 1px solid {COLORS['bet_box']};
            padding-bottom: 20px;
        }}
        .date-badge {{
            background-color: {COLORS['bet_box']};
            color: {COLORS['secondary']};
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9em;
            display: inline-block;
            margin-bottom: 10px;
        }}
        h1 {{ margin: 10px 0; font-size: 2rem; }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background-color: {COLORS['card']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid {COLORS['bet_box']};
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            display: block;
        }}
        .stat-label {{
            color: {COLORS['secondary']};
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .win-text {{ color: {COLORS['win']}; }}
        .loss-text {{ color: {COLORS['loss']}; }}
        
        .section-title {{
            border-left: 4px solid {COLORS['win']};
            padding-left: 10px;
            margin: 40px 0 20px 0;
            font-size: 1.5rem;
            font-weight: bold;
        }}
        
        .model-section {{
            margin-bottom: 40px;
        }}
        
        .model-title {{
            font-size: 1.2rem;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: {COLORS['bet_box']};
            padding: 10px 15px;
            border-radius: 8px;
        }}
        
        .picks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        
        .pick-card {{
            background-color: {COLORS['card']};
            border-radius: 8px;
            padding: 15px;
            border: 1px solid {COLORS['bet_box']};
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }}
        
        .pick-card.win {{ border-top: 3px solid {COLORS['win']}; }}
        .pick-card.loss {{ border-top: 3px solid {COLORS['loss']}; }}
        .pick-card.push {{ border-top: 3px solid {COLORS['accent']}; }}
        .pick-card.void {{ border-top: 3px solid {COLORS['void']}; }}
        
        .pick-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: {COLORS['secondary']};
        }}
        
        .player-name {{
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 5px;
            color: {COLORS['text']};
        }}
        
        .matchup {{
            font-size: 0.9em;
            color: {COLORS['secondary']};
            margin-bottom: 15px;
        }}
        
        .pick-details {{
            background-color: {COLORS['bet_box']};
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 10px;
        }}
        
        .pick-line {{
            font-weight: bold;
            display: block;
            margin-bottom: 4px;
        }}
        
        .pick-odds {{
            font-size: 0.9em;
            color: {COLORS['secondary']};
        }}
        
        .pick-result {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px solid {COLORS['bet_box']};
        }}
        
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge-win {{ background-color: rgba(16, 185, 129, 0.2); color: {COLORS['win']}; }}
        .badge-loss {{ background-color: rgba(239, 68, 68, 0.2); color: {COLORS['loss']}; }}
        .badge-push {{ background-color: rgba(59, 130, 246, 0.2); color: {COLORS['accent']}; }}
        .badge-void {{ background-color: rgba(156, 163, 175, 0.2); color: {COLORS['void']}; }}
        
        .result-score {{
            font-family: monospace;
            font-size: 0.9em;
        }}

    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="date-badge">{self.target_date}</span>
            <h1>Daily Recap</h1>
        </div>

        <div class="summary-grid">
            <div class="stat-card">
                <span class="stat-value">{stats['total']['wins']}-{stats['total']['losses']}-{stats['total']['pushes']} <span style="font-size:0.6em; color:{COLORS['void']}">({stats['total']['voids']} void)</span></span>
                <span class="stat-label">Daily Record</span>
            </div>
            <div class="stat-card">
                <span class="stat-value { 'win-text' if stats['total']['units'] > 0 else 'loss-text' }">
                    {stats['total']['units']:+.2f}u
                </span>
                <span class="stat-label">Total Profit</span>
            </div>
        </div>
        
        <!-- Highlights -->
        <div class="summary-grid">
            <div class="stat-card">
                <span class="stat-label">Top Performer</span>
                <div style="margin-top:10px; font-weight:bold; font-size: 1.2rem;">
                    {highlights['best_model'][0] if highlights['best_model'] else 'N/A'}
                </div>
                <div class="win-text" style="font-size: 1.1rem;">
                    {f"{highlights['best_model'][1]['units']:+.2f}u" if highlights['best_model'] else '-'}
                </div>
            </div>
             <div class="stat-card">
                <span class="stat-label">Needs Improvement</span>
                <div style="margin-top:10px; font-weight:bold; font-size: 1.2rem;">
                    {highlights['worst_model'][0] if highlights['worst_model'] else 'N/A'}
                </div>
                <div class="loss-text" style="font-size: 1.1rem;">
                    {f"{highlights['worst_model'][1]['units']:+.2f}u" if highlights['worst_model'] else '-'}
                </div>
            </div>
        </div>

        <div class="section-title">Model Breakdown</div>
        
        <!-- Iterate Models -->
        {''.join([self.render_model_section(name, data) for name, data in sorted(stats['by_model'].items(), key=lambda x: x[1]['units'], reverse=True)])}
        
    </div>
</body>
</html>
        """
        return html

    def render_model_section(self, name, data):
        unit_color = "win-text" if data['units'] > 0 else "loss-text"
        
        # Sort picks: Wins, then Pushes, then Voids, then Losses
        def sort_key(p):
            s = p.get('status', 'pending')
            if s == 'win': return 0
            if s == 'push': return 1
            if s == 'void': return 2
            if s == 'loss': return 3
            return 4
            
        sorted_picks = sorted(data['picks'], key=sort_key)
        
        pick_cards = ""
        for pick in sorted_picks:
            pick_cards += self.render_pick_card(pick)
            
        return f"""
        <div class="model-section">
            <div class="model-title">
                <span>{name}</span>
                <span class="{unit_color}">
                    {data['wins']}-{data['losses']}-{data['pushes']} <span style="font-size:0.8em; color:{COLORS['void']}">({data['voids']} void)</span> ({data['units']:+.2f}u)
                </span>
            </div>
            <div class="picks-grid">
                {pick_cards}
            </div>
        </div>
        """

    def render_pick_card(self, pick):
        status = pick.get('status', 'pending')
        
        # Determine visual style based on status
        card_class = f"pick-card {status}"
        badge_class = f"badge-{status}"
        
        # Extract display fields
        player = pick.get('player')
        team = pick.get('team')
        opponent = pick.get('opponent')
        
        # If no player/team/opponent (e.g. main model pick), try to parse from text description
        text = pick.get('pick') or pick.get('pick_text') or "Unknown Pick"
        text = text.replace("✅ BET:", "").replace("❌ BET:", "").strip()
        
        # Determine "Matchup" string
        matchup = ""
        if team and opponent:
            matchup = f"{team} vs {opponent}"
        elif pick.get('matchup'):
            matchup = pick.get('matchup')
        elif pick.get('home_team') and pick.get('away_team'):
            matchup = f"{pick['away_team']} @ {pick['home_team']}"
            
        # Determine "Header" (Player Name or Team Name)
        header_text = player if player else text
        
        # Determine "Line" details
        line_text = ""
        if pick.get('bet_type') and pick.get('prop_line'):
            # e.g. OVER 11.5 Pts
            bet_type = pick['bet_type'].upper()
            line = pick['prop_line']
            # Try to infer unit (Pts, Reb, Ast) from file path or other clues
            unit = ""
            fp = pick.get('file_path', '').lower()
            if 'points' in fp: unit = "Pts"
            elif 'rebounds' in fp: unit = "Reb"
            elif 'assists' in fp: unit = "Ast"
            elif '3pt' in fp: unit = "3PT"
            
            line_text = f"{bet_type} {line} {unit}"
        else:
            # Fallback to description line (Main model picks)
            line_text = text
            # If line_text became same as header, maybe header should be Team
            if line_text == header_text and (pick.get('team') or pick.get('home_team')):
                 # If it's a spread pick, header is team, line is spread
                 pass

        # Odds
        odds = pick.get('odds')
        odds_text = f"{odds}" if odds else ""
        if odds and float(odds) > 0: odds_text = f"+{odds}"
        
        # Result Score
        result_display = ""
        
        # Checking for various "actual" stats based on prop type
        actual_val = None
        if pick.get('actual_pts') is not None: actual_val = pick['actual_pts']
        elif pick.get('actual_reb') is not None: actual_val = pick['actual_reb']
        elif pick.get('actual_ast') is not None: actual_val = pick['actual_ast']
        elif pick.get('actual_3pm') is not None: actual_val = pick['actual_3pm']
        
        if actual_val is not None:
             result_display = f"Actual: {actual_val}"
             if pick.get('status') == 'void':
                 result_display = "DNP" # Force DNP display for void props if no pts
                 if actual_val == 0:
                      result_display = "Actual: 0" # Unless they actually played and got 0
                      
        # Check for pre-formatted strings (like NCAAB)
        elif pick.get('actual_score'):
             # NCAAB often has "TeamA X, TeamB Y"
             score_str = pick['actual_score']
             # Try to make it more compact if possible start with original
             result_display = score_str
             
             # Attempt to strip team names to save space, but safely
             teams_to_strip = [team, opponent, pick.get('home_team'), pick.get('away_team')]
             for t in teams_to_strip:
                 if t:
                     result_display = result_display.replace(t, "")
                 
             result_display = result_display.replace(",", "-").strip()
             
        elif pick.get('actual_home_score') and pick.get('actual_away_score'):
             result_display = f"Score: {pick['actual_away_score']}-{pick['actual_home_score']}"
        elif pick.get('result') == 'DNP':
             result_display = "DNP"
        
        return f"""
        <div class="{card_class}">
            <div>
                <div class="pick-header">
                     <span>{pick.get('sport', 'SPORT')}</span>
                     <span>{pick.get('game_time', '00:00')[11:16]} ET</span>
                </div>
                <div class="player-name">{header_text}</div>
                <div class="matchup">{matchup}</div>
                
                <div class="pick-details">
                    <span class="pick-line">{line_text}</span>
                    <span class="pick-odds">Odds: {odds_text}</span>
                </div>
            </div>
            
            <div class="pick-result">
                <span class="result-score">{result_display}</span>
                <span class="badge {badge_class}">{status.upper()}</span>
            </div>
        </div>
        """

def main():
    parser = argparse.ArgumentParser(description='Generate Daily Recap Report')
    parser.add_argument('--date', type=str, default=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), help='Date in YYYY-MM-DD format')
    parser.add_argument('--output', type=str, default='daily_recap.html', help='Output HTML file')
    
    args = parser.parse_args()
    
    generator = DailyRecapGenerator(args.date)
    generator.load_data()
    stats = generator.calculate_stats()
    html = generator.generate_html(stats)
    
    with open(args.output, 'w') as f:
        f.write(html)
        
    print(f"Report generated: {args.output}")

if __name__ == "__main__":
    main()
