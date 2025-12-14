#!/usr/bin/env python3
"""
Test PIL Card Generator
Generate a few sample cards to review before integration
"""

import os
from datetime import datetime
from pil_card_generator import create_card
from player_photo_service import get_player_photo

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

def format_game_time(game_time_str):
    """Format game time string"""
    if not game_time_str or game_time_str == 'TBD':
        return 'TBD'
    try:
        from datetime import datetime as dt
        import pytz
        dt_obj = dt.fromisoformat(game_time_str.replace('Z', '+00:00'))
        et_tz = pytz.timezone('US/Eastern')
        dt_et = dt_obj.astimezone(et_tz)
        return dt_et.strftime('%m/%d %I:%M %p ET')
    except:
        return game_time_str if game_time_str else 'TBD'

def get_rating_label(ai_rating):
    """Get rating label from AI rating"""
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

def generate_test_cards():
    """Generate a few test cards with different scenarios"""
    
    test_cases = [
        {
            'name': 'Premium Play - High EV',
            'data': {
                'rank': 1,
                'player_name': 'Paolo Banchero',
                'team_name': 'Orlando Magic',
                'opponent': 'New York Knicks',
                'prop_text': 'UNDER 22.5 PTS',
                'game_time': '12/13 05:30 PM ET',
                'ai_rating': 4.9,
                'rating_label': 'PREMIUM PLAY',
                'season_avg': 20.2,
                'recent_avg': 14.3,
                'clv_data': {
                    'opening': 100,
                    'latest': -104,
                    'positive': True
                },
                'ai_score': 10.0,
                'ev': 37.3,
                'is_sharp': True,
                'is_tracked': True,
            }
        },
        {
            'name': 'Strong Play - With CLV',
            'data': {
                'rank': 2,
                'player_name': 'Stephen Curry',
                'team_name': 'Golden State Warriors',
                'opponent': 'Minnesota Timberwolves',
                'prop_text': 'OVER 24.5 PTS',
                'game_time': '12/13 08:00 PM ET',
                'ai_rating': 4.2,
                'rating_label': 'STRONG PLAY',
                'season_avg': 28.5,
                'recent_avg': 30.2,
                'clv_data': {
                    'opening': -110,
                    'latest': -125,
                    'positive': False
                },
                'ai_score': 9.8,
                'ev': 15.5,
                'is_sharp': True,
                'is_tracked': False,
            }
        },
        {
            'name': 'Standard Play - No Badges',
            'data': {
                'rank': 3,
                'player_name': 'LeBron James',
                'team_name': 'Los Angeles Lakers',
                'opponent': 'Boston Celtics',
                'prop_text': 'OVER 25.5 PTS',
                'game_time': '12/13 10:00 PM ET',
                'ai_rating': 3.2,
                'rating_label': 'STANDARD PLAY',
                'season_avg': 24.8,
                'recent_avg': 26.1,
                'clv_data': {
                    'opening': -105,
                    'latest': -108,
                    'positive': True
                },
                'ai_score': 8.5,
                'ev': 8.2,
                'is_sharp': False,
                'is_tracked': False,
            }
        },
        {
            'name': 'Assists Prop',
            'data': {
                'rank': 1,
                'player_name': 'Tyrese Haliburton',
                'team_name': 'Indiana Pacers',
                'opponent': 'Philadelphia 76ers',
                'prop_text': 'OVER 11.5 AST',
                'game_time': '12/13 07:00 PM ET',
                'ai_rating': 4.6,
                'rating_label': 'PREMIUM PLAY',
                'season_avg': 12.3,
                'recent_avg': 13.8,
                'clv_data': {
                    'opening': -110,
                    'latest': -95,
                    'positive': True
                },
                'ai_score': 9.9,
                'ev': 28.4,
                'is_sharp': True,
                'is_tracked': True,
            }
        },
        {
            'name': 'Rebounds Prop',
            'data': {
                'rank': 2,
                'player_name': 'Nikola Jokic',
                'team_name': 'Denver Nuggets',
                'opponent': 'Phoenix Suns',
                'prop_text': 'UNDER 12.5 REB',
                'game_time': '12/13 09:30 PM ET',
                'ai_rating': 4.1,
                'rating_label': 'STRONG PLAY',
                'season_avg': 11.8,
                'recent_avg': 9.2,
                'clv_data': {
                    'opening': -105,
                    'latest': -115,
                    'positive': False
                },
                'ai_score': 9.2,
                'ev': 18.7,
                'is_sharp': False,
                'is_tracked': True,
            }
        },
    ]
    
    print("\n" + "="*60)
    print("Generating Test Cards")
    print("="*60 + "\n")
    
    generated_files = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case['name']}...")
        
        # Get player photo
        player_name = test_case['data']['player_name']
        player_photo = get_player_photo(player_name)
        
        # Create card
        card = create_card(test_case['data'], player_photo)
        
        # Save card
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = player_name.replace(' ', '_')
        filename = f"PIL_Test_{i}_{safe_name}_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card.save(filepath, 'PNG', quality=95)
        
        generated_files.append(filename)
        print(f"  ✓ Saved: {filename}")
    
    print(f"\n{'='*60}")
    print(f"✓ Generated {len(generated_files)} test cards")
    print(f"  Location: {ICLOUD_CARDS_FOLDER}")
    print(f"{'='*60}\n")
    
    return generated_files

if __name__ == "__main__":
    generate_test_cards()
