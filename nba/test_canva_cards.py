#!/usr/bin/env python3
"""
Test Canva Hybrid Cards
Generates test cards using your Canva template as background
"""

import os
import json
from datetime import datetime
from canva_hybrid_generator import CanvaHybridGenerator

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

def format_game_time(game_time_str):
    """Format game time from ISO format"""
    try:
        if not game_time_str:
            return 'TBD'
        from datetime import datetime as dt
        import pytz
        dt_obj = dt.fromisoformat(game_time_str.replace('Z', '+00:00'))
        et_tz = pytz.timezone('US/Eastern')
        dt_et = dt_obj.astimezone(et_tz)
        return dt_et.strftime('%m/%d %I:%M %p ET')
    except:
        return game_time_str if game_time_str else 'TBD'

def get_rating_label(ai_rating):
    """Get rating label based on AI rating"""
    if ai_rating >= 4.5:
        return 'PREMIUM PLAY'
    elif ai_rating >= 4.0:
        return 'STRONG PLAY'
    elif ai_rating >= 3.5:
        return 'GOOD PLAY'
    elif ai_rating >= 3.0:
        return 'STANDARD PLAY'
    else:
        return 'MARGINAL PLAY'

def create_test_cards():
    """Create test cards with sample data"""
    
    test_plays = [
        {
            'rank': 1,
            'player_name': 'Paolo Banchero',
            'team_name': 'Orlando Magic',
            'opponent': 'New York Knicks',
            'prop_type': 'Points',
            'prop_line': 22.5,
            'bet_type': 'under',
            'odds': 100,
            'season_avg': 20.2,
            'recent_avg': 14.3,
            'ai_score': 10.0,
            'ai_rating': 4.9,
            'ev': 37.3,
            'is_sharp': True,
            'is_tracked': True,
            'game_time': '2025-12-13T22:30:00Z',
        },
        {
            'rank': 1,
            'player_name': 'Stephen Curry',
            'team_name': 'Golden State Warriors',
            'opponent': 'Minnesota Timberwolves',
            'prop_type': 'Points',
            'prop_line': 24.5,
            'bet_type': 'over',
            'odds': -118,
            'season_avg': 28.5,
            'recent_avg': 30.2,
            'ai_score': 10.0,
            'ai_rating': 4.7,
            'ev': 25.5,
            'is_sharp': True,
            'is_tracked': True,
            'game_time': '2025-12-13T03:10:00Z',
        },
    ]
    
    print(f"\n{'='*60}")
    print("Generating Canva Hybrid Cards")
    print(f"{'='*60}\n")
    print(f"Output folder: {ICLOUD_CARDS_FOLDER}\n")
    
    generator = CanvaHybridGenerator()
    
    if not generator.background_path:
        print("✗ No Canva background found!")
        print(f"   Please save your design to: {generator.CANVA_BACKGROUND_DIR}/")
        return
    
    print(f"✓ Using background: {os.path.basename(generator.background_path)}\n")
    
    generated = []
    
    for i, play in enumerate(test_plays, 1):
        print(f"[{i}/{len(test_plays)}] Creating card for {play['player_name']}...")
        
        # Format prop text
        prop_text = f"{play['bet_type'].upper()} {play['prop_line']} {play['prop_type']}"
        
        # Format game time
        game_time = format_game_time(play.get('game_time', ''))
        
        # Get rating label
        rating_label = get_rating_label(play.get('ai_rating', 2.3))
        
        # CLV data
        clv_data = None
        if play.get('odds'):
            clv_data = {
                'opening': play['odds'],
                'latest': play['odds'] - 4 if play['odds'] < 0 else play['odds'] - 10,
                'positive': True
            }
        
        # Prepare card data
        card_data = {
            'rank': play.get('rank', 1),
            'player_name': play['player_name'],
            'team_name': play['team_name'],
            'opponent': play['opponent'],
            'prop_text': prop_text,
            'game_time': game_time,
            'ai_rating': play.get('ai_rating', 2.3),
            'rating_label': rating_label,
            'season_avg': play.get('season_avg', 0),
            'recent_avg': play.get('recent_avg', 0),
            'clv_data': clv_data,
            'ai_score': play.get('ai_score', 0),
            'ev': play.get('ev'),
            'is_sharp': play.get('is_sharp', False),
            'is_tracked': play.get('is_tracked', False),
        }
        
        # Create card
        card_img = generator.create_card(card_data)
        
        # Save to iCloud
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{play['player_name'].replace(' ', '_')}_Canva_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card_img.save(filepath, 'PNG', quality=95)
        
        generated.append(filepath)
        print(f"  ✓ Saved: {filename}\n")
    
    print(f"{'='*60}")
    print(f"✓ Generated {len(generated)} cards")
    print(f"  Location: {ICLOUD_CARDS_FOLDER}")
    print(f"\n📝 Next Steps:")
    print(f"  1. Check the preview: nba/images/canva_backgrounds/preview_with_labels.png")
    print(f"  2. Adjust coordinates in: nba/text_position_config.json")
    print(f"  3. Re-run to see updated positions")
    print(f"{'='*60}\n")
    
    return generated

if __name__ == "__main__":
    create_test_cards()
