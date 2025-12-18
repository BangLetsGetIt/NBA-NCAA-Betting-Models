# Props Tracking Implementation Guide

This document explains how to add self-tracking functionality to prop betting models. The tracking system automatically:
- Tracks picks when the model runs
- Grades pending picks using NBA API
- Calculates ROI and win/loss records
- Displays performance metrics in HTML (overall + OVER/UNDER splits)

## Overview

The tracking system maintains a JSON file with all historical picks and their results. Each time the model runs:
1. **Grade pending picks** - Fetch actual stats and update win/loss status
2. **Generate new picks** - Run model analysis
3. **Track new picks** - Save to JSON (or update odds if duplicate)
4. **Calculate stats** - Compute ROI and win rates
5. **Display stats** - Show performance breakdown in HTML

## Implementation Steps

### 1. Add Tracking File Path to Configuration

Add to configuration section (after cache file paths):

```python
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_[stat]_props_tracking.json")
```

Example:
- Points: `nba_points_props_tracking.json`
- Rebounds: `nba_rebounds_props_tracking.json`
- Assists: `nba_assists_props_tracking.json`

### 2. Add Tracking Functions

Add these functions after the Colors class:

#### 2.1 Load/Save Functions

```python
def load_tracking_data():
    """Load tracking data from JSON file"""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {'picks': [], 'summary': {}}

def save_tracking_data(tracking_data):
    """Save tracking data to JSON file"""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)
```

#### 2.2 Track New Picks

```python
def track_new_picks(over_plays, under_plays):
    """Track new picks in the tracking file"""
    tracking_data = load_tracking_data()
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}📊 TRACKING NEW PICKS{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")
    
    new_count = 0
    updated_count = 0
    
    for play in over_plays + under_plays:
        # Extract prop line from prop string (e.g., "OVER 23.5 PTS" -> 23.5)
        prop_str = play.get('prop', '')
        bet_type = 'over' if 'OVER' in prop_str else 'under'
        
        # Parse prop line from string
        import re
        match = re.search(r'(\d+\.?\d*)', prop_str)
        prop_line = float(match.group(1)) if match else 0
        
        # Generate unique pick ID
        pick_id = f"{play['player']}_{prop_line}_{bet_type}_{play.get('game_time', '')}"
        
        # Check if pick already exists
        existing_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == pick_id), None)
        
        if existing_pick:
            # Update latest odds if different
            if existing_pick.get('latest_odds') != play.get('odds'):
                existing_pick['latest_odds'] = play.get('odds')
                existing_pick['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
                updated_count += 1
        else:
            # Add new pick
            new_pick = {
                'pick_id': pick_id,
                'player': play['player'],
                'prop_line': prop_line,
                'bet_type': bet_type,
                'team': play.get('team'),
                'opponent': play.get('opponent'),
                'ai_score': play.get('ai_score'),
                'odds': play.get('odds'),
                'opening_odds': play.get('odds'),
                'latest_odds': play.get('odds'),
                'game_time': play.get('game_time'),
                'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                'status': 'pending',
                'result': None,
                'actual_pts': None  # Change to actual_[stat] for other props
            }
            tracking_data['picks'].append(new_pick)
            new_count += 1
    
    save_tracking_data(tracking_data)
    
    if new_count > 0:
        print(f"{Colors.GREEN}✓ Tracked {new_count} new picks{Colors.END}")
    if updated_count > 0:
        print(f"{Colors.YELLOW}✓ Updated odds for {updated_count} existing picks{Colors.END}")
    if new_count == 0 and updated_count == 0:
        print(f"{Colors.CYAN}No new picks to track{Colors.END}")
```

**Adaptations for other stats:**
- Points: `actual_pts`
- Rebounds: `actual_reb`
- Assists: `actual_ast`
- 3-pointers: `actual_3pm`

#### 2.3 Grade Pending Picks

```python
def grade_pending_picks():
    """Grade pending picks by fetching actual stats from NBA API"""
    tracking_data = load_tracking_data()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
    
    if not pending_picks:
        print(f"\n{Colors.GREEN}✓ No pending picks to grade{Colors.END}")
        return
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}🎯 GRADING PENDING PICKS{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"\n{Colors.YELLOW}📋 Found {len(pending_picks)} pending picks...{Colors.END}\n")
    
    graded_count = 0
    
    for pick in pending_picks:
        # Check if game has passed (add 4 hour buffer for games to complete)
        try:
            game_time_str = pick.get('game_time')
            if not game_time_str:
                continue
                
            game_time_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            current_time = datetime.now(pytz.UTC)
            hours_since_game = (current_time - game_time_utc).total_seconds() / 3600
            
            if hours_since_game < 4:
                continue  # Game too recent, wait for stats
            
            # Fetch actual stat from NBA API
            # NOTE: Use appropriate fetch function for each stat type:
            # - Points: fetch_player_points_from_nba_api()
            # - Rebounds: fetch_player_rebounds_from_nba_api()
            # - Assists: fetch_player_assists_from_nba_api()
            player_name = pick.get('player')
            team_name = pick.get('team')
            game_date = game_time_utc.strftime('%Y-%m-%d')
            
            actual_stat = fetch_player_points_from_nba_api(player_name, team_name, game_date)
            
            if actual_stat is None:
                print(f"{Colors.YELLOW}  ⚠ Could not find stats for {player_name} on {game_date}{Colors.END}")
                continue
            
            # Grade the pick
            prop_line = pick.get('prop_line')
            bet_type = pick.get('bet_type')
            
            if bet_type == 'over':
                is_win = actual_stat > prop_line
            else:  # under
                is_win = actual_stat < prop_line
            
            # Calculate profit/loss - CRITICAL: Use opening_odds (the odds bet was placed at)
            # opening_odds is the odds when pick was first tracked, odds might be updated later
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if is_win:
                if odds > 0:
                    profit_loss = int(odds)  # Store as cents
                else:
                    profit_loss = int((100.0 / abs(odds)) * 100)  # Store as cents
                status = 'win'
                result = 'WIN'
                result_color = Colors.GREEN
            else:
                profit_loss = -100  # Lost 1 unit (100 cents)
                status = 'loss'
                result = 'LOSS'
                result_color = Colors.RED
            
            # Update pick
            pick['status'] = status
            pick['result'] = result
            pick['actual_pts'] = actual_stat  # Change to actual_[stat] for other props
            pick['profit_loss'] = profit_loss
            pick['updated_at'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
            
            print(f"    {result_color}{result}{Colors.END}: {player_name} had {actual_stat} points (line: {prop_line}, bet: {bet_type.upper()})")
            graded_count += 1
            
        except Exception as e:
            print(f"{Colors.RED}  Error grading pick {pick.get('player')}: {e}{Colors.END}")
            continue
    
    if graded_count > 0:
        save_tracking_data(tracking_data)
        print(f"\n{Colors.GREEN}✓ Graded {graded_count} picks{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}No picks ready for grading yet{Colors.END}")
```

**NOTE**: You must have a fetch function for the specific stat. For points, the model already has `fetch_player_points_from_nba_api()`. For other stats, create equivalent functions.

#### 2.3.5 Backfill Profit Loss Function

**CRITICAL**: Add this function to fix any picks that were graded before profit_loss was implemented:

```python
def backfill_profit_loss():
    """Backfill profit_loss for graded picks that are missing it - CRITICAL for accurate ROI"""
    tracking_data = load_tracking_data()
    updated_count = 0
    
    for pick in tracking_data['picks']:
        # Only process picks that are graded but missing profit_loss
        if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
            # USE OPENING ODDS (the odds the bet was actually placed at)
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if pick.get('status') == 'win':
                if odds > 0:
                    # Positive odds: +150 means bet $100 to win $150, profit = 150 cents
                    profit_loss = int(odds)
                else:
                    # Negative odds: -110 means bet $110 to win $100, profit = (100/110)*100 = 91 cents
                    profit_loss = int((100.0 / abs(odds)) * 100)
            else:  # loss
                # Lost the bet: -100 cents (lost 1 unit)
                profit_loss = -100
            
            pick['profit_loss'] = profit_loss
            pick['profit_loss_backfilled'] = True
            updated_count += 1
    
    if updated_count > 0:
        save_tracking_data(tracking_data)
        print(f"{Colors.GREEN}✓ Backfilled profit_loss for {updated_count} picks{Colors.END}")
    
    return updated_count
```

#### 2.4 Calculate Tracking Stats

```python
def calculate_tracking_stats(tracking_data):
    """Calculate performance statistics from tracking data"""
    completed_picks = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]
    
    if not completed_picks:
        return {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'roi': 0.0,
            'roi_pct': 0.0,
            'over_record': '0-0',
            'over_win_rate': 0.0,
            'over_roi': 0.0,
            'under_record': '0-0',
            'under_win_rate': 0.0,
            'under_roi': 0.0
        }
    
    wins = sum(1 for p in completed_picks if p.get('status') == 'win')
    losses = sum(1 for p in completed_picks if p.get('status') == 'loss')
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0.0
    
    # Calculate profit in units (cents / 100)
    total_profit_cents = sum(p.get('profit_loss', 0) for p in completed_picks)
    total_profit_units = total_profit_cents / 100.0
    
    # ROI = (profit / total bets) * 100
    roi_pct = (total_profit_units / total * 100) if total > 0 else 0.0
    
    # Calculate OVER stats
    over_picks = [p for p in completed_picks if p.get('bet_type') == 'over']
    over_wins = sum(1 for p in over_picks if p.get('status') == 'win')
    over_losses = sum(1 for p in over_picks if p.get('status') == 'loss')
    over_total = over_wins + over_losses
    over_win_rate = (over_wins / over_total * 100) if over_total > 0 else 0.0
    over_profit_cents = sum(p.get('profit_loss', 0) for p in over_picks)
    over_profit_units = over_profit_cents / 100.0
    over_roi = (over_profit_units / over_total * 100) if over_total > 0 else 0.0
    
    # Calculate UNDER stats
    under_picks = [p for p in completed_picks if p.get('bet_type') == 'under']
    under_wins = sum(1 for p in under_picks if p.get('status') == 'win')
    under_losses = sum(1 for p in under_picks if p.get('status') == 'loss')
    under_total = under_wins + under_losses
    under_win_rate = (under_wins / under_total * 100) if under_total > 0 else 0.0
    under_profit_cents = sum(p.get('profit_loss', 0) for p in under_picks)
    under_profit_units = under_profit_cents / 100.0
    under_roi = (under_profit_units / under_total * 100) if under_total > 0 else 0.0
    
    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 2),
        'total_profit': round(total_profit_units, 2),
        'roi': round(total_profit_units, 2),
        'roi_pct': round(roi_pct, 2),
        'over_record': f'{over_wins}-{over_losses}',
        'over_win_rate': round(over_win_rate, 2),
        'over_roi': round(over_roi, 2),
        'under_record': f'{under_wins}-{under_losses}',
        'under_win_rate': round(under_win_rate, 2),
        'under_roi': round(under_roi, 2)
    }
```

### 3. Update Main Function

Modify the main() function execution order:

```python
def main():
    """Main execution"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}NBA [STAT] PROPS A.I. MODEL{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    # 1. Grade pending picks FIRST (before generating new ones)
    grade_pending_picks()
    
    # 1.5. CRITICAL: Backfill profit_loss for any graded picks missing it (fixes ROI calculation)
    backfill_profit_loss()

    # 2. Fetch data and analyze props
    player_stats = get_nba_player_[stat]_stats()
    [other_factors] = get_opponent_[stat]_factors()
    props_list = get_player_props()
    
    over_plays, under_plays = analyze_props(props_list, player_stats, [other_factors])

    # 3. Track new picks
    track_new_picks(over_plays, under_plays)
    
    # 4. Calculate tracking stats for HTML display
    tracking_data = load_tracking_data()
    stats = calculate_tracking_stats(tracking_data)

    # 5. Print plays (existing code)
    # ... existing print statements ...

    # 6. Generate HTML with stats
    print(f"\n{Colors.CYAN}Generating HTML report...{Colors.END}")
    html_content = generate_html_output(over_plays, under_plays, stats)
    save_html(html_content)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Model execution complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")
```

### 4. Update HTML Generation

#### 4.1 Update Function Signature

```python
def generate_html_output(over_plays, under_plays, stats=None):
    """Generate HTML output matching NBA model card-based style"""
```

#### 4.1.5 Add Odds Formatting Function

Add this helper function inside `generate_html_output()` (after `format_game_time()`):

```python
# Helper function to format odds for display
def format_odds(odds_value):
    """Format odds value to American odds format (e.g., -110, +150)"""
    if odds_value is None:
        return 'N/A'
    try:
        odds = int(odds_value)
        if odds > 0:
            return f'+{odds}'
        else:
            return str(odds)
    except:
        return str(odds_value) if odds_value else 'N/A'
```

#### 4.1.6 Add Odds Display to Pick Cards

**For OVER plays** (after game_time_formatted line, before rating_display):

```python
<div class="odds-line" style="text-align: left;">
    <strong>{game_time_formatted}</strong>
</div>
<div class="odds-line">
    <span>Odds:</span>
    <strong style="color: #10b981;">{format_odds(play.get('odds'))}</strong>
</div>
{rating_display}
```

**For UNDER plays** (same location, but use red color):

```python
<div class="odds-line" style="text-align: left;">
    <strong>{game_time_formatted}</strong>
</div>
<div class="odds-line">
    <span>Odds:</span>
    <strong style="color: #ef4444;">{format_odds(play.get('odds'))}</strong>
</div>
{rating_display}
```

**IMPORTANT**: The odds displayed are the opening odds (the odds when the pick was first tracked). This is critical because prop bets have varying odds (not standardized like -110 for sides/totals), so users need to see what odds the bet was actually placed at.

#### 4.2 Add Stats HTML Section

Before the footer_text line, add:

```python
# Generate stats card if stats provided
stats_html = ""
if stats and stats.get('total', 0) > 0:
    total = stats['total']
    wins = stats['wins']
    losses = stats['losses']
    win_rate = stats['win_rate']
    roi_pct = stats['roi_pct']
    total_profit = stats['total_profit']
    
    roi_color = '#10b981' if roi_pct > 0 else '#ef4444'
    roi_sign = '+' if roi_pct > 0 else ''
    profit_sign = '+' if total_profit > 0 else ''
    
    over_record = stats['over_record']
    over_win_rate = stats['over_win_rate']
    over_roi = stats['over_roi']
    over_roi_color = '#10b981' if over_roi > 0 else '#ef4444'
    over_roi_sign = '+' if over_roi > 0 else ''
    
    under_record = stats['under_record']
    under_win_rate = stats['under_win_rate']
    under_roi = stats['under_roi']
    under_roi_color = '#10b981' if under_roi > 0 else '#ef4444'
    under_roi_sign = '+' if under_roi > 0 else ''
    
    stats_html = f"""
        <div class="card">
            <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #3b82f6;">NBA [STAT] Model Performance</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                <div class="stat-box">
                    <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">Overall Record</div>
                    <div style="font-size: 1.75rem; font-weight: 700; color: #ffffff;">{wins}-{losses}</div>
                    <div style="font-size: 1rem; color: #10b981; margin-top: 0.25rem;">{win_rate:.1f}% Win Rate</div>
                </div>
                <div class="stat-box">
                    <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">ROI</div>
                    <div style="font-size: 1.75rem; font-weight: 700; color: {roi_color};">{roi_sign}{roi_pct:.1f}%</div>
                    <div style="font-size: 1rem; color: {roi_color}; margin-top: 0.25rem;">{profit_sign}{total_profit:.2f} Units</div>
                </div>
                <div class="stat-box">
                    <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">OVER Bets</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">{over_record}</div>
                    <div style="font-size: 0.875rem; margin-top: 0.25rem;">
                        <span style="color: #10b981;">{over_win_rate:.1f}% Win</span> | 
                        <span style="color: {over_roi_color};">{over_roi_sign}{over_roi:.1f}% ROI</span>
                    </div>
                </div>
                <div class="stat-box">
                    <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">UNDER Bets</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444;">{under_record}</div>
                    <div style="font-size: 0.875rem; margin-top: 0.25rem;">
                        <span style="color: #ef4444;">{under_win_rate:.1f}% Win</span> | 
                        <span style="color: {under_roi_color};">{under_roi_sign}{under_roi:.1f}% ROI</span>
                    </div>
                </div>
            </div>
        </div>
    """
```

#### 4.3 Add Stats to HTML Template

In the HTML template, add `{stats_html}` before the footer:

```python
html = f"""<!DOCTYPE html>
...
    {over_html}
    
    {under_html}
    
    {stats_html}
    
    <div class="card" style="text-align: center;">
        <p style="color: #94a3b8; ...">{footer_text}</p>
    </div>
...
</html>"""
```

### 5. Required Fetch Function for Grading

You need a function to fetch actual stats from NBA API. For points props, this already exists in the model:

```python
def fetch_player_points_from_nba_api(player_name, team_name, game_date_str):
    """Fetch actual player points from NBA API for a specific game"""
    try:
        # Find player ID
        player_list = players.get_players()
        player_info = None
        
        # Match player name (handle variations)
        name_parts = player_name.lower().split()
        for p in player_list:
            p_name = p['full_name'].lower()
            p_parts = p_name.split()
            if len(name_parts) >= 2 and len(p_parts) >= 2:
                if name_parts[0] in p_parts[0] and name_parts[-1] in p_parts[-1]:
                    player_info = p
                    break
        
        if not player_info:
            print(f"{Colors.YELLOW}    Could not find player {player_name} in NBA API{Colors.END}")
            return None
        
        player_id = player_info['id']
        
        # Get player game log
        game_log = playergamelog.PlayerGameLog(player_id=player_id, season=CURRENT_SEASON, timeout=30)
        df = game_log.get_data_frames()[0]
        
        if df.empty:
            return None
        
        # Find the game by date
        target_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        
        for _, row in df.iterrows():
            game_date_str_nba = row.get('GAME_DATE', '')
            if not game_date_str_nba:
                continue
            
            # Parse NBA date format
            try:
                game_date = datetime.strptime(game_date_str_nba, '%b %d, %Y').date()
            except:
                try:
                    game_date = datetime.strptime(game_date_str_nba, '%Y-%m-%d').date()
                except:
                    continue
            
            if game_date == target_date:
                stat_value = row.get('PTS', 0)  # Change to REB, AST, FG3M, etc.
                return int(stat_value) if stat_value else 0
        
        return None
        
    except Exception as e:
        print(f"{Colors.YELLOW}  Error fetching stats from NBA API for {player_name}: {str(e)}{Colors.END}")
        return None
```

**Adaptations for other stats:**
- Points: `row.get('PTS', 0)`
- Rebounds: `row.get('REB', 0)`
- Assists: `row.get('AST', 0)`
- 3-pointers: `row.get('FG3M', 0)`

### 6. ROI Calculation Formula

**CRITICAL**: Always use `opening_odds` (the odds when the pick was first tracked) for profit calculations, NOT `odds` or `latest_odds`. The `odds` field may be updated later if the pick is tracked again, but profit must be calculated based on the odds the bet was actually placed at.

ROI is calculated based on actual betting outcomes:

**For each completed pick:**
```python
# CRITICAL: Use opening_odds (the odds bet was placed at)
odds = pick.get('opening_odds') or pick.get('odds', -110)

if status == "win":
    if odds > 0:
        profit = odds / 100.0  # e.g., +150 = 1.5 units profit
    else:
        profit = 100.0 / abs(odds)  # e.g., -110 = 0.909 units profit
elif status == "loss":
    profit = -1.0  # Lost the bet unit
```

**Total ROI:**
```python
total_profit_units = sum(all profits)  # in units
total_bets = number of completed picks
roi_percentage = (total_profit_units / total_bets) * 100
```

**Storage:** Profit/loss is stored as **cents** in the JSON (multiply units by 100), then divided by 100 for display.

### 7. Data Structure

#### Pick Object in tracking JSON:

```json
{
  "pick_id": "LeBron James_23.5_over_2025-12-14T20:00:00Z",
  "player": "LeBron James",
  "prop_line": 23.5,
  "bet_type": "over",
  "team": "Los Angeles Lakers",
  "opponent": "Phoenix Suns",
  "ai_score": 10.0,
  "odds": -110,
  "opening_odds": -110,
  "latest_odds": -114,
  "game_time": "2025-12-14T20:00:00Z",
  "tracked_at": "2025-12-14T15:00:00-05:00",
  "status": "win",
  "result": "WIN",
  "actual_pts": 28,
  "profit_loss": 91,
  "updated_at": "2025-12-15T02:00:00-05:00"
}
```

#### Summary Object:

```json
{
  "picks": [...],
  "summary": {
    "total": 50,
    "wins": 30,
    "losses": 20,
    "pending": 10,
    "win_rate": 60.0,
    "roi": 5.0,
    "roi_pct": 5.0
  }
}
```

### 8. HTML Display Format

The stats card displays:

```
Model Performance
┌─────────────────────────┐
│ Overall Record          │
│ 46-35                   │
│ 56.8% Win Rate         │
└─────────────────────────┘

┌─────────────────────────┐
│ ROI                     │
│ +3.0%                   │
│ +2.45 Units            │
└─────────────────────────┘

┌─────────────────────────┐
│ OVER Bets               │
│ 29-18                   │
│ 61.7% Win | -2.1% ROI   │
└─────────────────────────┘

┌─────────────────────────┐
│ UNDER Bets              │
│ 17-17                   │
│ 50.0% Win | +10.2% ROI  │
└─────────────────────────┘
```

### 9. Testing Checklist

- [ ] Run model - verify it tracks new picks
- [ ] Check tracking JSON - verify picks are saved correctly
- [ ] Wait for games to complete (or test with past games)
- [ ] Run model again - verify pending picks are graded
- [ ] Check tracking JSON - verify status updated to win/loss
- [ ] Verify actual_[stat] field populated
- [ ] Verify profit_loss calculated correctly
- [ ] Check HTML output - verify stats card displays
- [ ] Verify overall record is correct
- [ ] Verify ROI calculation is accurate (using opening_odds)
- [ ] Verify OVER/UNDER split is correct
- [ ] Verify colors (green for positive ROI, red for negative)
- [ ] Verify odds are displayed on each pick card
- [ ] Verify opening_odds is used for profit calculations (not latest_odds)

### 10. Common Issues & Solutions

**Issue: prop_line showing as 0**
- Cause: Not parsing prop line from prop string correctly
- Solution: Use regex to extract numeric value from "OVER 23.5 PTS" format

**Issue: Stats not grading**
- Cause: Game time buffer too short or player name mismatch
- Solution: Increase buffer to 4+ hours, improve name matching logic

**Issue: ROI calculation wrong**
- Cause: Not handling positive/negative odds correctly OR using wrong odds field
- Solution: 
  - Always use `opening_odds` for profit calculations (not `odds` or `latest_odds`)
  - Use correct formulas (see section 6)
  - Run `backfill_profit_loss()` to fix existing picks

**Issue: Missing profit_loss fields causing incorrect ROI**
- Cause: Picks graded before profit_loss calculation was implemented
- Solution: Add and call `backfill_profit_loss()` function in main() before calculating stats

**Issue: Odds not displayed on HTML cards**
- Cause: format_odds() function not added or not called in HTML generation
- Solution: Add format_odds() helper function and display odds after game_time in both OVER and UNDER card sections

**Issue: Duplicate picks**
- Cause: pick_id not unique enough
- Solution: Include game_time in pick_id

### 11. Applying to Other Models

To apply this tracking system to other prop models:

1. **Copy tracking functions** (load, save, track, grade, calculate)
2. **Update file paths** (tracking file name)
3. **Update field names** (actual_pts → actual_reb, actual_ast, etc.)
4. **Update fetch function** (PTS → REB, AST, FG3M field in NBA API)
5. **Update print statements** (points → rebounds, assists, etc.)
6. **Update main() flow** (same pattern: grade, analyze, track, calculate, display)
7. **Update HTML generation** (add stats parameter and stats_html section)
8. **Test thoroughly** (verify grading works for the specific stat)

### 12. File Checklist

When implementing tracking for a prop model, ensure these files exist:

- `nba/nba_[stat]_props_model.py` - Main model with tracking integrated
- `nba/nba_[stat]_props_tracking.json` - Tracking data (auto-generated)
- `nba/nba_[stat]_props.html` - Output HTML with performance stats

### 13. Performance Metrics Explained

- **Overall Record**: W-L count of all completed picks
- **Win Rate**: Wins / (Wins + Losses) × 100
- **ROI %**: (Total Profit / Total Bets) × 100
- **Units**: Total profit in betting units (1 unit = standard bet amount)
- **OVER Record**: W-L count for OVER bets only
- **UNDER Record**: W-L count for UNDER bets only
- **Split ROI**: ROI calculated separately for OVER and UNDER bets

### 14. Example Output

After running the model:

**Console:**
```
🎯 GRADING PENDING PICKS
Found 42 pending picks...

    WIN: LeBron James had 28 points (line: 23.5, bet: OVER)
    LOSS: Draymond Green had 9 points (line: 8.5, bet: UNDER)

✓ Graded 11 picks

📊 TRACKING NEW PICKS
✓ Tracked 10 new picks
```

**HTML Display:**
- Overall: 46-35 (56.8%)
- ROI: +3.0% (+2.45 Units)
- OVER: 29-18 (61.7%) | -2.1% ROI
- UNDER: 17-17 (50.0%) | +10.2% ROI

## Summary

The tracking system provides complete performance transparency:
1. Automatically tracks all generated picks
2. Grades them when games complete
3. Calculates accurate ROI based on actual odds
4. Displays performance breakdown in HTML
5. Separates OVER/UNDER performance for analysis

This enables data-driven model improvement and demonstrates profitability over time.
