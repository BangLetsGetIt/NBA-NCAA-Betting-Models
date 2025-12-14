#!/usr/bin/env python3
"""
Test Player Cards
Generates sample player prop cards for design review
"""

import os
import json
from datetime import datetime
from card_design import create_player_card
from player_photo_service import get_player_photo

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

def format_odds(odds):
    """Format American odds"""
    if odds > 0:
        return f"+{odds}"
    return str(odds)

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
    """Create test cards with sample data matching the example"""
    
    # Sample test data based on your tracking file structure
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
        {
            'rank': 1,
            'player_name': 'Luka Doncic',
            'team_name': 'Dallas Mavericks',
            'opponent': 'Brooklyn Nets',
            'prop_type': 'Assists',
            'prop_line': 9.5,
            'bet_type': 'over',
            'odds': 110,
            'season_avg': 11.1,
            'recent_avg': 11.8,
            'ai_score': 9.8,
            'ai_rating': 4.5,
            'ev': 18.2,
            'is_sharp': False,
            'is_tracked': True,
            'game_time': '2025-12-13T01:40:00Z',
        },
    ]
    
    print(f"\n{'='*60}")
    print("Generating Test Player Prop Cards")
    print(f"{'='*60}\n")
    print(f"Output folder: {ICLOUD_CARDS_FOLDER}\n")
    
    generated = []
    
    for i, play in enumerate(test_plays, 1):
        print(f"[{i}/{len(test_plays)}] Creating card for {play['player_name']}...")
        
        # Get player photo (try to get action photo, fallback to headshot)
        player_photo = get_player_photo(play['player_name'])
        
        # Format prop text
        prop_text = f"{play['bet_type'].upper()} {play['prop_line']} {play['prop_type']}"
        
        # Format game time
        game_time = format_game_time(play.get('game_time', ''))
        
        # Get rating label
        rating_label = get_rating_label(play.get('ai_rating', 2.3))
        
        # CLV data (sample - in production, get from tracking)
        clv_data = None
        if play.get('odds'):
            # Sample CLV showing positive movement
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
        card_img = create_player_card(card_data, player_photo)
        
        # Save to iCloud
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{play['player_name'].replace(' ', '_')}_{play['prop_type']}_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card_img.save(filepath, 'PNG', quality=95)
        
        generated.append(filepath)
        print(f"  ✓ Saved: {filename}\n")
    
    print(f"{'='*60}")
    print(f"✓ Generated {len(generated)} test cards")
    print(f"  Location: {ICLOUD_CARDS_FOLDER}")
    print(f"{'='*60}\n")
    
    return generated

if __name__ == "__main__":
    create_test_cards()
