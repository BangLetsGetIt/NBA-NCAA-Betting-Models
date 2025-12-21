#!/usr/bin/env python3
"""
Best Plays Aggregator Bot
-------------------------
Scans all models, analyzes historical performance, and ranks upcoming plays.
Outputs TOP 20 best plays to bet in a styled HTML.

Run: python3 best_plays_bot.py
Output: best_plays.html
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "best_plays.html")
FIRE_TRACKING_FILE = os.path.join(SCRIPT_DIR, "best_plays_tracking.json")
FIRE_SCORE_THRESHOLD = 80  # Minimum score for FIRE
SOLID_SCORE_THRESHOLD = 70 # Minimum score for SOLID

# Timezone
ET = pytz.timezone('US/Eastern')

def now_et():
    return datetime.now(ET)

def today_str():
    return now_et().strftime('%Y-%m-%d')

# All tracking files to scan
TRACKING_SOURCES = [
    # (Name, File Path, Sport, Bet Category)
    ('NBA Points Props', 'nba/nba_points_props_tracking.json', 'NBA', 'Props'),
    ('NBA Assists Props', 'nba/nba_assists_props_tracking.json', 'NBA', 'Props'),
    ('NBA Rebounds Props', 'nba/nba_rebounds_props_tracking.json', 'NBA', 'Props'),
    ('NBA 3PT Props', 'nba/nba_3pt_props_tracking.json', 'NBA', 'Props'),
    ('NFL Passing Yards', 'nfl/nfl_passing_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Rushing Yards', 'nfl/nfl_rushing_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Receiving Yards', 'nfl/nfl_receiving_yards_props_tracking.json', 'NFL', 'Props'),
    ('NFL Receptions', 'nfl/nfl_receptions_props_tracking.json', 'NFL', 'Props'),
    ('NBA Main', 'nba/nba_picks_tracking.json', 'NBA', 'Spread/Total'),
    ('NFL Main', 'nfl/nfl_picks_tracking.json', 'NFL', 'Spread/Total'),
    ('NCAAB', 'ncaa/ncaab_picks_tracking.json', 'NCAAB', 'Spread/Total'),
    ('Soccer', 'soccer/soccer_picks_tracking.json', 'Soccer', 'Total'),
]


def load_tracking_data(filepath):
    """Load tracking data from JSON file"""
    full_path = os.path.join(SCRIPT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
        picks = data.get('picks', []) if isinstance(data, dict) else data
        # print(f"Loaded {len(picks)} picks from {filepath}")
        return picks
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []


def calculate_model_stats(picks):
    """Calculate win rate and recent form for a model"""
    graded = [p for p in picks if p.get('status', '').lower() in ['win', 'won', 'loss', 'lost']]
    wins = sum(1 for p in graded if p.get('status', '').lower() in ['win', 'won'])
    losses = sum(1 for p in graded if p.get('status', '').lower() in ['loss', 'lost'])
    total = wins + losses
    
    win_rate = (wins / total * 100) if total > 0 else 50.0
    
    # Recent form (last 10)
    recent = graded[-10:] if len(graded) >= 10 else graded
    recent_wins = sum(1 for p in recent if p.get('status', '').lower() in ['win', 'won'])
    recent_total = len(recent)
    recent_rate = (recent_wins / recent_total * 100) if recent_total > 0 else 50.0
    
    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': win_rate,
        'recent_rate': recent_rate,
        'record': f"{wins}-{losses}"
    }

def calculate_bet_type_stats(picks, bet_type):
    """Calculate win rate for a specific bet type (OVER/UNDER/Spread)"""
    bt = bet_type.lower()
    filtered = [p for p in picks if bt in p.get('bet_type', '').lower() or bt in p.get('pick_type', '').lower()]
    graded = [p for p in filtered if p.get('status', '').lower() in ['win', 'won', 'loss', 'lost']]
    wins = sum(1 for p in graded if p.get('status', '').lower() in ['win', 'won'])
    total = len(graded)
    
    return (wins / total * 100) if total > 0 else 50.0


def get_record_breakdown():
    """Aggregate records by sport and model"""
    breakdown = []
    for model_name, filepath, sport, category in TRACKING_SOURCES:
        picks = load_tracking_data(filepath)
        stats = calculate_model_stats(picks)
        if stats['total'] > 0:
            breakdown.append({
                'name': model_name,
                'sport': sport,
                'category': category,
                'record': stats['record'],
                'win_rate': stats['win_rate']
            })
    # Sort by win rate descending
    return sorted(breakdown, key=lambda x: x['win_rate'], reverse=True)


def parse_game_time(game_time_str):
    """Parse game time string to datetime in ET"""
    if not game_time_str:
        return None
    try:
        if 'Z' in game_time_str:
            dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(game_time_str)
        return dt.astimezone(ET)
    except:
        return None


def calculate_confidence_score(play, model_stats, bet_type_rate):
    """
    Calculate composite confidence score (0-100)
    
    Weights:
    - Model Win Rate: 30%
    - Bet Type Win Rate: 25%
    - AI Score: 20%
    - Edge: 15%
    - Recent Form: 10%
    """
    # Model win rate (0-100) -> scaled to 0-30
    model_score = (model_stats['win_rate'] / 100) * 30
    
    # Bet type win rate (0-100) -> scaled to 0-25
    bet_type_score = (bet_type_rate / 100) * 25
    
    # AI Score (typically 8-10) -> scaled to 0-20
    ai_score = play.get('ai_score', 8.0)
    ai_component = ((ai_score - 7) / 3) * 20  # 7=0, 10=20
    ai_component = max(0, min(20, ai_component))
    
    # Edge (varies by model) -> scaled to 0-15
    edge = abs(play.get('edge', 0))
    # Normalize edge: props typically 1-5, spreads 5-15
    if edge > 0:
        edge_normalized = min(edge / 10, 1.0)  # Cap at 10 points of edge
        edge_component = edge_normalized * 15
    else:
        edge_component = 5  # Neutral if no edge data
    
    # Recent form -> scaled to 0-10
    recent_score = (model_stats['recent_rate'] / 100) * 10
    
    # Total
    total = model_score + bet_type_score + ai_component + edge_component + recent_score
    
    return round(min(100, max(0, total)), 1)


def get_pending_plays():
    """Gather all pending plays from all models with confidence scores"""
    all_plays = []
    now = now_et()

    for model_name, filepath, sport, category in TRACKING_SOURCES:
        picks = load_tracking_data(filepath)
        if not picks:
            continue
        
        # Calculate model stats
        model_stats = calculate_model_stats(picks)
        
        # Get pending plays
        pending = [p for p in picks if p.get('status', 'pending').lower() == 'pending']
        
        for p in pending:
            # Parse game time - only include future games
            game_time = parse_game_time(p.get('game_time') or p.get('game_date'))
            if game_time and game_time < now:
                continue  # Skip past games
            
            # Get bet type
            bet_type = p.get('bet_type', p.get('pick_type', 'unknown'))
            bet_type_rate = calculate_bet_type_stats(picks, bet_type)
            
            # Calculate confidence score
            confidence = calculate_confidence_score(p, model_stats, bet_type_rate)
            
            # Build play object
            play = {
                'model': model_name,
                'sport': sport,
                'category': category,
                'player': p.get('player', p.get('team', 'Unknown')),
                'bet_type': bet_type.upper() if bet_type else 'N/A',
                'line': p.get('prop_line', p.get('line', '')),
                'odds': p.get('odds', '-110'),
                'edge': p.get('edge', 0),
                'ai_score': p.get('ai_score', 0),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p') if game_time else 'TBD',
                'matchup': p.get('matchup', p.get('opponent', '')),
                'source_pick_id': p.get('pick_id'),
                'model_record': model_stats['record'],
                'model_win_rate': model_stats['win_rate'],
                'confidence': confidence,
                'team': p.get('team', ''),
                'season_avg': p.get('season_avg', 0),
                'recent_avg': p.get('recent_avg', 0),
                'season_record': p.get('season_record', ''),
            }
            all_plays.append(play)
    
    # Sort by confidence score (highest first) AND prioritize plays with stats
    all_plays.sort(key=lambda x: (x['confidence'], x.get('season_avg', 0) > 0), reverse=True)
    
    # Deduplicate: Keep only highest confidence play per player+category
    unique_plays = []
    seen_keys = set()
    
    for play in all_plays:
        # Filter invalid player names
        if play['player'] in ['Unknown', 'UNK', 'N/A']:
            continue

        # Create unique key (Sport + Category + Player)
        # We ignore side (OVER/UNDER) to prevent conflicting bets on same prop
        key = (play['sport'], play['category'], play['player'])
        
        if key not in seen_keys:
            seen_keys.add(key)
            unique_plays.append(play)
            
    return unique_plays


def get_team_logo_url(team_name, sport):
    """Get ESPN logo URL for team"""
    if not team_name or team_name == 'UNK':
        return "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nba.png" # Default
    
    # Normalize
    t = team_name.lower().replace('76ers', 'sixers')
    
    # Abbreviation Map
    abbr_map = {
        # NBA
        'atlanta hawks': 'atl', 'boston celtics': 'bos', 'brooklyn nets': 'bkn', 'charlotte hornets': 'cha',
        'chicago bulls': 'chi', 'cleveland cavaliers': 'cle', 'dallas mavericks': 'dal', 'denver nuggets': 'den',
        'detroit pistons': 'det', 'golden state warriors': 'gs', 'houston rockets': 'hou', 'indiana pacers': 'ind',
        'los angeles clippers': 'lac', 'los angeles lakers': 'lal', 'memphis grizzlies': 'mem', 'miami heat': 'mia',
        'milwaukee bucks': 'mil', 'minnesota timberwolves': 'min', 'new orleans pelicans': 'no', 'new york knicks': 'ny',
        'oklahoma city thunder': 'okc', 'orlando magic': 'orl', 'philadelphia 76ers': 'phi', 'phoenix suns': 'phx',
        'portland trail blazers': 'por', 'sacramento kings': 'sac', 'san antonio spurs': 'sas', 'toronto raptors': 'tor',
        'utah jazz': 'uta', 'washington wizards': 'was', 'sixers': 'phi', 'cavs': 'cle',
        # NFL
        'arizona cardinals': 'ari', 'atlanta falcons': 'atl', 'baltimore ravens': 'bal', 'buffalo bills': 'buf',
        'carolina panthers': 'car', 'chicago bears': 'chi', 'cincinnati bengals': 'cin', 'cleveland browns': 'cle',
        'dallas cowboys': 'dal', 'denver broncos': 'den', 'detroit lions': 'det', 'green bay packers': 'gb',
        'houston texans': 'hou', 'indianapolis colts': 'ind', 'jacksonville jaguars': 'jax', 'kansas city chiefs': 'kc',
        'las vegas raiders': 'lv', 'los angeles chargers': 'lac', 'los angeles rams': 'lar', 'miami dolphins': 'mia',
        'minnesota vikings': 'min', 'new england patriots': 'ne', 'new orleans saints': 'no', 'new york giants': 'nyg',
        'new york jets': 'nyj', 'philadelphia eagles': 'phi', 'pittsburgh steelers': 'pit', 'san francisco 49ers': 'sf',
        'seattle seahawks': 'sea', 'tampa bay buccaneers': 'tb', 'tennessee titans': 'ten', 'washington commanders': 'was'
    }
    
    # Try exact match first
    abbr = abbr_map.get(t)
    if not abbr:
        # Try finding key in name
        for k, v in abbr_map.items():
            if k in t: 
                abbr = v
                break
    
    if not abbr: abbr = team_name[:3].lower()
    
    sport_path = 'nba' if sport == 'NBA' else 'nfl' if sport == 'NFL' else 'ncaa'
    return f"https://a.espncdn.com/i/teamlogos/{sport_path}/500/{abbr}.png"


def get_confidence_tier(score):
    """Get tier label and color based on confidence score"""
    if score >= 80:
        return '🔥 FIRE', '#ff6b35'
    elif score >= 65:
        return '✅ SOLID', '#4ade80'
    elif score >= 50:
        return '⚡ VALUE', '#60a5fa'
    else:
        return '📊 PLAY', '#8e8e93'


def load_fire_tracking():
    """Load Fire plays tracking data"""
    if not os.path.exists(FIRE_TRACKING_FILE):
        return {'plays': [], 'record': {'wins': 0, 'losses': 0, 'win_rate': 0.0}}
    try:
        with open(FIRE_TRACKING_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'plays': [], 'record': {'wins': 0, 'losses': 0, 'win_rate': 0.0}}


def save_fire_tracking(data):
    """Save Fire plays tracking data"""
    with open(FIRE_TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def update_fire_tracking(current_plays):
    """
    Update Fire plays tracking:
    1. Add new high-confidence plays
    2. Check status of pending plays from source files
    3. Calculate Fire record
    """
    tracking = load_fire_tracking()
    tracked_plays = tracking.get('plays', [])
    
    # 1. Add new high-confidence plays
    # Create a set of existing tracked items to avoid duplicates
    # Prefer source `pick_id` when available, otherwise fallback to normalized key
    existing_keys = set()
    existing_pick_ids = set()
    for p in tracked_plays:
        if p.get('source_pick_id'):
            existing_pick_ids.add(p['source_pick_id'])
        else:
            key = f"{p.get('player','').strip().lower()}_{p.get('bet_type','').strip().upper()}_{p.get('game_time','') }_{p.get('line','') }"
            existing_keys.add(key)
    
    for play in current_plays:
        if play['confidence'] >= SOLID_SCORE_THRESHOLD:
            # Format game_time for storage
            gt_str = play['game_time'].isoformat() if play['game_time'] else today_str()
            key = f"{play['player']}_{play['bet_type']}_{gt_str}"
            
            # If source_pick_id present on play, prefer dedup by that
            src_id = play.get('pick_id') or play.get('pickId')
            if src_id and src_id in existing_pick_ids:
                continue

            if src_id:
                key = src_id
            else:
                key = f"{play.get('player','').strip().lower()}_{play.get('bet_type','').strip().upper()}_{gt_str}_{play.get('line','') }"

            if (src_id and src_id not in existing_pick_ids) or (not src_id and key not in existing_keys):
                # Add new play
                new_play = play.copy()
                new_play['game_time'] = gt_str # Serialize datetime
                new_play['status'] = 'pending'
                new_play['tracked_at'] = now_et().isoformat()
                if src_id:
                    new_play['source_pick_id'] = src_id
                    existing_pick_ids.add(src_id)
                else:
                    existing_keys.add(key)
                tracked_plays.append(new_play)
    
    # 2. Check status of pending plays
    # We need to reload source files to check for results
    # This is efficiently done by creating a map of results from source files
    results_map = {} # Key: player_bettype_date -> status
    
    for _, filepath, _, _ in TRACKING_SOURCES:
        picks = load_tracking_data(filepath)
        for p in picks:
            status = p.get('status', 'pending').lower()
            if status in ['win', 'won', 'loss', 'lost']:
                pass # Logic handled below

    # Step 2: Iterate through tracked pending plays and look for them in source files
    for i, tp in enumerate(tracked_plays):
        if tp.get('status') != 'pending':
            continue

        matched = False
        # If we have a source_pick_id, match exactly
        tp_src = tp.get('source_pick_id')

        for _, filepath, _, _ in TRACKING_SOURCES:
            picks = load_tracking_data(filepath)
            for p in picks:
                # If source id exists, prefer exact match
                p_src = p.get('pick_id') or p.get('pickId')
                if tp_src and p_src and tp_src == p_src:
                    status = (p.get('status') or 'pending').lower()
                    if status in ['win', 'won']:
                        tracked_plays[i]['status'] = 'win'
                        matched = True
                    elif status in ['loss', 'lost']:
                        tracked_plays[i]['status'] = 'loss'
                        matched = True
                    if matched: break

                # Fallback matching: normalize player, bet type, date, and line
                if not matched:
                    try:
                        p_player = (p.get('player') or p.get('team') or '').strip().lower()
                        tp_player = (tp.get('player') or '').strip().lower()
                        
                        # Primary bet type (OVER/UNDER/SPREAD/TOTAL)
                        p_bet = (p.get('bet_type') or p.get('pick_type') or '').strip().upper()
                        tp_bet = (tp.get('bet_type') or '').strip().upper()

                        # Compare game dates (YYYY-MM-DD) to avoid timezone mismatches
                        p_time = parse_game_time(p.get('game_time') or p.get('game_date'))
                        tp_time = None
                        try:
                            if isinstance(tp.get('game_time'), str):
                                tp_time = parse_game_time(tp.get('game_time'))
                            else:
                                tp_time = tp.get('game_time')
                        except:
                            tp_time = None

                        p_date = p_time.date().isoformat() if p_time else None
                        tp_date = tp_time.date().isoformat() if tp_time else None

                        # Match player
                        if p_player == tp_player:
                            # Match bet type (check for Over/Under/Spread inclusion)
                            # This handles "UNDER" vs "under" vs "Player Under 244.5"
                            bet_matched = (p_bet in tp_bet or tp_bet in p_bet)
                            
                            # Match date
                            date_matched = (p_date == tp_date) if (p_date and tp_date) else True
                            
                            if bet_matched and date_matched:
                                status = (p.get('status') or 'pending').lower()
                                if status in ['win', 'won']:
                                    tracked_plays[i]['status'] = 'win'
                                    matched = True
                                elif status in ['loss', 'lost']:
                                    tracked_plays[i]['status'] = 'loss'
                                    matched = True
                                elif status in ['push', 'void', 'cancelled', 'refunded']:
                                    tracked_plays[i]['status'] = 'void'
                                    matched = True
                                
                                if matched:
                                    break
                    except:
                        continue
            if matched:
                # stop searching other files for this tracked play
                continue
    
    # 3. Calculate Records
    fire_wins = 0
    fire_losses = 0
    solid_wins = 0
    solid_losses = 0

    for p in tracked_plays:
        status = p.get('status', '').lower()
        confidence = p.get('confidence', 0)
        
        if status == 'win':
            if confidence >= FIRE_SCORE_THRESHOLD:
                fire_wins += 1
            elif confidence >= SOLID_SCORE_THRESHOLD:
                solid_wins += 1
        elif status == 'loss':
            if confidence >= FIRE_SCORE_THRESHOLD:
                fire_losses += 1
            elif confidence >= SOLID_SCORE_THRESHOLD:
                solid_losses += 1
            
    fire_total = fire_wins + fire_losses
    fire_wr = (fire_wins / fire_total * 100) if fire_total > 0 else 0.0

    solid_total = solid_wins + solid_losses
    solid_wr = (solid_wins / solid_total * 100) if solid_total > 0 else 0.0
    
    tracking['plays'] = tracked_plays
    tracking['record'] = {
        'fire': {'wins': fire_wins, 'losses': fire_losses, 'win_rate': fire_wr},
        'solid': {'wins': solid_wins, 'losses': solid_losses, 'win_rate': solid_wr}
    }
    
    save_fire_tracking(tracking)
    return tracking['record']


def generate_html(plays, fire_record=None, breakdown=None):
    """Generate styled HTML output"""
    # Show up to 50 plays (or all if less than 50)
    top_plays = plays[:50]
    timestamp = now_et().strftime('%Y-%m-%d %I:%M %p ET')
    
    # Fire Record & Breakdown Display
    stats_header_html = ""
    
    # Left Side: Fire & Solid Records
    fire_stats_content = ""
    if fire_record:
        # Compatibility check: if it's the old flat dict, wrap it
        if 'wins' in fire_record:
             fire_data = fire_record
             solid_data = {'wins': 0, 'losses': 0, 'win_rate': 0.0}
        else:
             fire_data = fire_record.get('fire', {})
             solid_data = fire_record.get('solid', {})

        fire_wr = fire_data.get('win_rate', 0.0)
        fire_color = "#4ade80" if fire_wr >= 55 else "#ffffff" if fire_wr >= 50 else "#f87171"
        
        solid_wr = solid_data.get('win_rate', 0.0)
        solid_color = "#4ade80" if solid_wr >= 55 else "#ffffff" if solid_wr >= 50 else "#f87171"

        fire_stats_content = f'''
            <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                <div class="fire-stats-box">
                    <div class="fire-title">🔥 Fire Plays (80+)</div>
                    <div class="fire-record">
                        {fire_data.get('wins',0)}-{fire_data.get('losses',0)} 
                        <span style="color: {fire_color}; font-size: 0.8em;">({fire_wr:.1f}%)</span>
                    </div>
                </div>
                <div class="fire-stats-box" style="border-color: rgba(96, 165, 250, 0.3); background: rgba(96, 165, 250, 0.1);">
                    <div class="fire-title" style="color: #60a5fa;">💎 Solid Plays (70+)</div>
                    <div class="fire-record">
                        {solid_data.get('wins',0)}-{solid_data.get('losses',0)} 
                        <span style="color: {solid_color}; font-size: 0.8em;">({solid_wr:.1f}%)</span>
                    </div>
                </div>
            </div>
        '''

    # Right Side: Breakdown Table
    breakdown_html = ""
    if breakdown:
        rows = ""
        for b in breakdown:
            wr_color = "#4ade80" if b['win_rate'] >= 55 else "#ffffff" if b['win_rate'] >= 50 else "#f87171"
            rows += f'''
            <tr>
                <td style="text-align: left; padding: 4px 8px;">{b['name']}</td>
                <td style="padding: 4px 8px;">{b['record']}</td>
                <td style="padding: 4px 8px; color: {wr_color}; font-weight: 600;">{b['win_rate']:.1f}%</td>
            </tr>
            '''
        
        
        breakdown_html = f'''
        <div class="breakdown-section">
            <div class="breakdown-box">
                <div class="breakdown-title">📊 All Models Performance</div>
                <table class="breakdown-table">
                    <thead>
                        <tr>
                            <th style="text-align: left;">Model</th>
                            <th>Record</th>
                            <th>Win %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
        '''
    
    # Build play cards HTML
    play_cards = ""
    for i, play in enumerate(top_plays, 1):
        tier_label, tier_color = get_confidence_tier(play['confidence'])
        
        # Format bet display
        if play['line']:
            bet_display = f"{play['bet_type']} {play['line']}"
        else:
            bet_display = play['bet_type']
        
        # Bet color: green for OVER, red for UNDER
        bet_class = "play-bet-under" if "UNDER" in play['bet_type'].upper() else "play-bet-over"
        
        # Format edge
        edge_display = f"+{play['edge']:.1f}" if play['edge'] > 0 else f"{play['edge']:.1f}"
        
        # Stats Block (Always show at least Edge, Win Rate, and Model Record)
        season = play.get('season_avg', 0)
        recent = play.get('recent_avg', 0)
        season_record = play.get('season_record', '')
        
        # Base stats (Uniform for all cards)
        stats_html = f'''
                    <div class="stat">
                        <span class="stat-label">Edge</span>
                        <span class="stat-value">{edge_display}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Win Rate</span>
                        <span class="stat-value">{play['model_win_rate']:.0f}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Model Record</span>
                        <span class="stat-value">{play['model_record']}</span>
                    </div>
        '''
        
        # Additional context for Player Props
        if (isinstance(season, (int, float)) and season > 0) or (isinstance(recent, (int, float)) and recent > 0):
             stats_html += f'''
             <div class="stat">
                <span class="stat-label">Season</span>
                <span class="stat-value">{season}</span>
            </div>
            <div class="stat">
                <span class="stat-label">{"L10 Avg" if play.get('sport') == 'NBA' else "L5 Avg"}</span>
                <span class="stat-value">{recent}</span>
            </div>
             '''
        # Fallback for Team Bets if specific team record was backfilled
        elif season_record:
             stats_html += f'''
             <div class="stat">
                <span class="stat-label">Team Record</span>
                <span class="stat-value">{season_record}</span>
            </div>
             '''
        
        
        # Team Logo
        logo_url = get_team_logo_url(play.get('team', 'UNK'), play.get('sport', 'NBA'))
        
        play_cards += f'''
        <div class="play-card">
            <div class="play-content">
                <div class="play-header">
                    <div class="header-left-group" style="display: flex; align-items: center; gap: 10px;">
                        <img src="{logo_url}" alt="Team" style="width: 40px; height: 40px; object-fit: contain;">
                        <div>
                             <div class="play-player">{play['player']}</div>
                             <div class="play-matchup" style="font-size: 12px; color: var(--text-secondary);">{play['matchup']}</div>
                        </div>
                    </div>
                    <div class="play-rank-inline">#{i}</div>
                </div>
                
                <div class="play-main">
                    <div class="{bet_class}">{bet_display}</div>
                    <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">{play['model']}</div>
                </div>
                
                <div class="play-meta-row" style="display:flex; justify-content:space-between; align-items:flex-end;">
                     <div class="play-tier" style="color:{tier_color}">{tier_label} ({play['confidence']})</div>
                     <span class="meta-tag">{play['game_time_str']}</span>
                </div>
                
                <div class="play-stats" style="margin-top: 12px;">
                    {stats_html}
                </div>
            </div>
        </div>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Best Plays • CourtSide Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --border-color: #333333;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-main);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .header-left {{
             display: flex;
             flex-direction: column;
        }}
        
        h1 {{
            font-size: 24px;
            font-weight: 700;
            margin: 0 0 5px 0;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 14px;
        }}
        
        .timestamp {{
            background: var(--bg-card-secondary);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }}
        
        .plays-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 20px;
        }}
        
        /* Mobile adjustment */
        @media (max-width: 600px) {{
            .plays-grid {{
                grid-template-columns: 1fr;
            }}
            header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .timestamp {{
                align-self: flex-start;
            }}
        }}
        
        .play-card {{
            display: flex;
            flex-direction: column;
            background: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .play-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
            border-color: #444;
        }}
        
        .play-content {{
            padding: 15px 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        
        .play-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }}
        
        .play-rank-inline {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-secondary);
            background: var(--bg-card-secondary);
            padding: 4px 10px;
            border-radius: 6px;
        }}
        
        .play-score {{
            font-size: 24px;
            font-weight: 800;
        }}
        
        .play-tier {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
        }}
        
        .play-main {{
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .play-player {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        
        .play-bet-over {{
            font-size: 22px;
            font-weight: 800;
            color: var(--accent-green);
        }}
        
        .play-bet-under {{
            font-size: 22px;
            font-weight: 800;
            color: var(--accent-red);
        }}
        
        .play-meta {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }}
        
        .meta-tag {{
            background: var(--bg-card-secondary);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .play-stats {{
            display: flex;
            gap: 20px;
            background: var(--bg-main);
            padding: 10px;
            border-radius: 8px;
        }}
        
        .stat {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }}
        
        .stat-value {{
            font-size: 14px;
            font-weight: 700;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }}
        
        @media (max-width: 600px) {{
            header {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
            h1 {{ font-size: 20px; }}
            .play-stats {{ flex-wrap: wrap; gap: 12px; }}
            .play-rank {{ width: 45px; font-size: 14px; }}
            .play-bet {{ font-size: 18px; }}
        }}
        
        .fire-stats-box {{
            background: rgba(255, 69, 0, 0.1);
            border: 1px solid rgba(255, 69, 0, 0.3);
            border-radius: 12px;
            padding: 15px 25px;
            text-align: center;
            min-width: 250px;
        }}

        .breakdown-box {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px;
            font-size: 13px;
            max-width: 600px;
            flex-grow: 1;
        }}

        .stats-header-container {{
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }}

        .breakdown-section {{
            margin-top: 50px;
            margin-bottom: 30px;
            display: flex;
            justify-content: center;
        }}

        .breakdown-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-secondary);
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-align: center;
        }}

        .breakdown-table {{
            width: 100%;
            border-collapse: collapse;
            color: var(--text-primary);
        }}

        .breakdown-table th {{
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color);
        }}

        .breakdown-table td {{
            padding: 6px 0;
            text-align: center;
        }}

        .fire-title {{
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 2px;
        }}

        .fire-record {{
            font-size: 24px;
            font-weight: 800;
            color: var(--text-primary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-left">
                <h1>🎯 Best Plays</h1>
                <div class="subtitle">Top 50 Highest Confidence Bets</div>
            </div>
            {fire_stats_content}
            <div class="timestamp">Generated: {timestamp}</div>
        </header>
        
        <div class="plays-grid">
            {play_cards if play_cards else '<div class="empty-state">No pending plays found. Check back after models run.</div>'}
        </div>

        {breakdown_html}
    </div>
</body>
</html>'''
    
    return html


def main():
    print("🎯 Best Plays Aggregator")
    print("=" * 50)
    
    # Get all pending plays with scores
    print("📊 Scanning all models...")
    plays = get_pending_plays()
    print(f"   Found {len(plays)} pending plays across all models")
    
    # Update Fire plays tracking
    print("🔥 Updating Fire plays tracking...")
    fire_record = update_fire_tracking(plays)
    
    # Check for legacy format compatibility during transition
    if 'wins' in fire_record:
         # It's the old format
         print(f"   Fire Record: {fire_record['wins']}-{fire_record['losses']} ({fire_record['win_rate']:.1f}%)")
    else:
         # New nested format
         fr = fire_record.get('fire', {})
         sr = fire_record.get('solid', {})
         print(f"   Fire Record: {fr.get('wins',0)}-{fr.get('losses',0)} ({fr.get('win_rate',0):.1f}%)")
         print(f"   Solid Record: {sr.get('wins',0)}-{sr.get('losses',0)} ({sr.get('win_rate',0):.1f}%)")
    
    # 3. Calculate breakdown
    print("📋 Calculating breakdown stats...")
    breakdown = get_record_breakdown()

    # 4. Generate HTML
    print("📄 Generating HTML...")
    html = generate_html(plays, fire_record, breakdown)
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    
    print(f"✅ Created: {OUTPUT_HTML}")
    
    # Show top 5 in console
    if plays:
        print("\n🔥 TOP 5 PLAYS:")
        print("-" * 50)
        for i, p in enumerate(plays[:5], 1):
            print(f"  #{i} [{p['confidence']:.0f}] {p['player']} {p['bet_type']} {p['line']}")
            print(f"      {p['model']} ({p['model_record']})")
    
    return len(plays)


if __name__ == "__main__":
    main()
