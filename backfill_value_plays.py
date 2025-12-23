
import json
import os
import sys
from datetime import datetime
import best_plays_bot
from best_plays_bot import (
    TRACKING_SOURCES, 
    FIRE_TRACKING_FILE, 
    load_tracking_data, 
    load_fire_tracking, 
    save_fire_tracking,
    VALUE_SCORE_THRESHOLD,
    SOLID_SCORE_THRESHOLD,
    calculate_model_stats,
    calculate_bet_type_stats,
    calculate_confidence_score
)

def backfill_value_plays():
    print("🔍 Starting Value Plays Backfill (Dynamic Calculation)...")
    print(f"   Target Confidence Range: {VALUE_SCORE_THRESHOLD} - {SOLID_SCORE_THRESHOLD - 0.1}")
    
    # Load existing tracking
    tracking = load_fire_tracking()
    tracked_plays = tracking.get('plays', [])
    
    # Create set of existing IDs/Keys to prevent duplicates
    existing_keys = set()
    existing_pick_ids = set()
    
    for p in tracked_plays:
        if p.get('source_pick_id'):
            existing_pick_ids.add(p['source_pick_id'])
        else:
            # Fallback key generation
            gt = p.get('game_time', '')
            try:
                if 'T' in gt: gt = gt.split('T')[0]
            except: pass  
            key = f"{p.get('player','').strip().lower()}_{p.get('bet_type','').strip().upper()}_{gt}_{p.get('line','')}"
            existing_keys.add(key)
            
    print(f"   Loaded {len(tracked_plays)} existing tracked plays.")
    
    new_plays_count = 0
    
    for name, filepath, sport, category in TRACKING_SOURCES:
        full_path = os.path.join(best_plays_bot.SCRIPT_DIR, filepath)
        if not os.path.exists(full_path):
            continue
            
        print(f"   Scanning {name}...")
        picks = load_tracking_data(filepath)
        
        # 1. Calculate Model Stats for this file
        model_stats = calculate_model_stats(picks)
        
        for p in picks:
            # Only consider graded plays for backfill (Win/Loss/Push/Void)
            # Pending plays will be picked up by bot normally.
            # actually user wants "results from yesterday" so graded is key.
            
            # 2. Calculate Bet Type Stats
            bet_type = p.get('bet_type') or p.get('pick_type') or ''
            bet_type_rate = calculate_bet_type_stats(picks, bet_type)
            
            # 3. Calculate Confidence Score dynamically
            # If the play already has a confidence score (some might), use it, otherwise calculate.
            if p.get('confidence'):
                confidence = float(p.get('confidence'))
            else:
                confidence = calculate_confidence_score(p, model_stats, bet_type_rate)
            
            # 4. Check Value Threshold
            if confidence >= VALUE_SCORE_THRESHOLD:
                
                # Check duplication
                is_duplicate = False
                src_id = p.get('pick_id') or p.get('pickId')
                
                # Game time normalization
                gt_str = p.get('game_time') or p.get('game_date')
                
                if src_id and src_id in existing_pick_ids:
                    is_duplicate = True
                else:
                    try:
                        gt_key = gt_str
                        if 'T' in gt_key: gt_key = gt_key.split('T')[0]
                    except: gt_key = ''
                    key = f"{p.get('player','').strip().lower()}_{p.get('bet_type','').strip().upper()}_{gt_key}_{p.get('line','')}"
                    if key in existing_keys:
                        is_duplicate = True
                
                if not is_duplicate:
                    # Add it!
                    new_play = p.copy()
                    new_play['confidence'] = confidence # Save the calculated confidence
                    
                    if src_id:
                        new_play['source_pick_id'] = src_id
                        existing_pick_ids.add(src_id)
                    
                    if 'tracked_at' not in new_play:
                        new_play['tracked_at'] = datetime.now().isoformat()
                        
                    tracked_plays.append(new_play)
                    new_plays_count += 1
                    
    print(f"   Added {new_plays_count} new Value plays.")
    
    # Save updated tracking
    tracking['plays'] = tracked_plays
    save_fire_tracking(tracking)
    
    print("✅ Backfill saved.")
    
    # Recalculate records
    print("🔄 Recalculating records...")
    best_plays_bot.update_fire_tracking([])
    print("✅ Records updated.")

if __name__ == "__main__":
    backfill_value_plays()
