
import json
import os
from datetime import datetime
import pytz

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(SCRIPT_DIR, "best_plays_tracking.json")

def normalize_key(play):
    """Create a consistent key for deduplication"""
    sport = (play.get('sport') or '').strip().upper()
    category = (play.get('category') or '').strip().upper()
    
    player = (play.get('player') or play.get('team') or '').strip().lower()
    if player == 'unk' or not player:
        # Fallback for old entries without player
        player = (play.get('matchup') or '').lower()
        
    bet_type = (play.get('bet_type') or play.get('pick_type') or '').strip().upper()
    
    # Normalize Date (ignore time if possible, or use date part)
    game_time = play.get('game_time') or play.get('game_date')
    date_str = ""
    try:
        if game_time:
            # Handle ISO format
            if 'T' in game_time:
                date_str = game_time.split('T')[0]
            else:
                date_str = game_time
    except:
        date_str = str(game_time)
        
    # Simplify bet type (e.g., OVER 24.5 -> OVER) to catch variations
    # Actually, we should keep the line if possible, but line might change slightly
    # Let's use the line if available
    line = str(play.get('line') or play.get('prop_line') or '')
    
    return f"{sport}|{category}|{player}|{bet_type}|{date_str}|{line}"

def clean_tracking():
    print(f"Reading {TRACKING_FILE}...")
    try:
        with open(TRACKING_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    plays = data.get('plays', [])
    print(f"Total entries before cleanup: {len(plays)}")
    
    # 1. Group by Natural Key
    grouped = {}
    for p in plays:
        # Also support dedup by pick_id if available
        pick_id = p.get('source_pick_id') or p.get('pick_id')
        
        if pick_id:
            key = f"ID:{pick_id}"
        else:
            key = normalize_key(p)
            
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(p)
        
    # 2. Select Best Version for each group
    cleaned_plays = []
    
    for key, group in grouped.items():
        if len(group) == 1:
            cleaned_plays.append(group[0])
        else:
            # Sort to find best
            # Priority: 
            # 1. Has Status (Win/Loss > Pending)
            # 2. Has Pick ID
            # 3. Tracked At (Most Recent)
            
            def sort_key(p):
                status_score = 0
                status = str(p.get('status', '')).lower()
                if status in ['win', 'loss', 'won', 'lost', 'void']:
                    status_score = 2
                elif status == 'pending':
                    status_score = 1
                
                has_id = 1 if (p.get('source_pick_id') or p.get('pick_id')) else 0
                
                tracked_at = p.get('tracked_at', '')
                
                return (status_score, has_id, tracked_at)
            
            group.sort(key=sort_key, reverse=True)
            best_play = group[0]
            cleaned_plays.append(best_play)

    print(f"Total entries after cleanup: {len(cleaned_plays)}")
    
    # 3. Recalculate Record
    fire_wins = 0
    fire_losses = 0
    solid_wins = 0
    solid_losses = 0
    value_wins = 0
    value_losses = 0
    
    # Thresholds from best_plays_bot.py
    FIRE = 80
    SOLID = 70
    VALUE = 50

    for p in cleaned_plays:
        status = str(p.get('status', '')).lower()
        confidence = p.get('confidence', 0)
        
        if status in ['win', 'won']:
            if confidence >= FIRE: fire_wins += 1
            elif confidence >= SOLID: solid_wins += 1
            elif confidence >= VALUE: value_wins += 1
        elif status in ['loss', 'lost']:
            if confidence >= FIRE: fire_losses += 1
            elif confidence >= SOLID: solid_losses += 1
            elif confidence >= VALUE: value_losses += 1
            
    record = {
        'fire': {
            'wins': fire_wins, 
            'losses': fire_losses, 
            'win_rate': (fire_wins / (fire_wins + fire_losses) * 100) if (fire_wins + fire_losses) > 0 else 0
        },
        'solid': {
            'wins': solid_wins, 
            'losses': solid_losses, 
            'win_rate': (solid_wins / (solid_wins + solid_losses) * 100) if (solid_wins + solid_losses) > 0 else 0
        },
        'value': {
            'wins': value_wins, 
            'losses': value_losses, 
            'win_rate': (value_wins / (value_wins + value_losses) * 100) if (value_wins + value_losses) > 0 else 0
        }
    }
    
    print("\nRecalculated Records:")
    print(f"Fire: {fire_wins}-{fire_losses} ({record['fire']['win_rate']:.1f}%)")
    print(f"Solid: {solid_wins}-{solid_losses} ({record['solid']['win_rate']:.1f}%)")
    print(f"Value: {value_wins}-{value_losses} ({record['value']['win_rate']:.1f}%)")
    
    # 4. Save
    data['plays'] = cleaned_plays
    data['record'] = record
    
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved cleaned data to {TRACKING_FILE}")

if __name__ == "__main__":
    clean_tracking()
