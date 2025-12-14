#!/usr/bin/env python3
"""
Precise Template Overlay
Uses your Canva template as exact background, overlays text with precise positioning
"""

import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

CANVA_BACKGROUND_DIR = Path(__file__).parent / "images" / "canva_backgrounds"
template_path = CANVA_BACKGROUND_DIR / "CourtSide Template.png"

def get_font(size, bold=False):
    """Get font"""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Inter-Bold.otf" if bold else "/System/Library/Fonts/Supplemental/Inter-Regular.otf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        try:
            if path.endswith('.ttc'):
                return ImageFont.truetype(path, size, index=0)
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def create_card_from_template(player_data, player_photo=None):
    """
    Create card using your exact Canva template as background
    Overlays text precisely on top
    """
    if not template_path.exists():
        print(f"✗ Template not found: {template_path}")
        return None
    
    # Load your exact template
    card = Image.open(template_path).convert('RGB')
    draw = ImageDraw.Draw(card)
    
    # If you have a player photo, you can overlay it on the photo area
    # This depends on where the photo area is in your template
    if player_photo:
        # Adjust these coordinates based on your template's photo area
        photo_x = 0
        photo_y = 0
        photo_width = card.width
        photo_height = int(card.height * 0.6)  # Adjust based on your template
        
        photo_resized = player_photo.resize((photo_width, photo_height), Image.Resampling.LANCZOS)
        
        # Create a mask for blending if needed
        # For now, just paste it
        card.paste(photo_resized, (photo_x, photo_y))
    
    # Now overlay text elements
    # These coordinates need to match your template exactly
    # You'll need to identify where each text element should go
    
    # Load position config if it exists
    config_file = Path(__file__).parent / "text_position_config.json"
    positions = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            positions = config.get('text_positions', {})
    
    # Format data
    rank = player_data.get('rank', 1)
    prop_text = player_data.get('prop_text', '')
    player_name = player_data.get('player_name', '')
    team_name = player_data.get('team_name', '')
    opponent = player_data.get('opponent', '')
    game_time = player_data.get('game_time', 'TBD')
    ai_rating = player_data.get('ai_rating', 2.3)
    rating_label = player_data.get('rating_label', 'STANDARD PLAY')
    season_avg = player_data.get('season_avg', 0)
    recent_avg = player_data.get('recent_avg', 0)
    clv_data = player_data.get('clv_data')
    ai_score = player_data.get('ai_score', 0)
    ev = player_data.get('ev')
    is_sharp = player_data.get('is_sharp', False)
    is_tracked = player_data.get('is_tracked', False)
    
    # Draw text elements using config positions
    # Rank + Prop
    if 'rank_prop' in positions:
        pos = positions['rank_prop']
        text = f"#{rank} • {prop_text}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Player name
    if 'player_name' in positions:
        pos = positions['player_name']
        font = get_font(pos['font_size'], pos['bold'])
        if pos['align'] == 'right':
            bbox = draw.textbbox((0, 0), player_name, font=font)
            text_width = bbox[2] - bbox[0]
            x = pos['x'] - text_width
        else:
            x = pos['x']
        draw.text((x, pos['y']), player_name, fill=tuple(pos['color']), font=font)
    
    # Player label
    if 'player_label' in positions:
        pos = positions['player_label']
        text = f"Player: {player_name}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Matchup
    if 'matchup' in positions:
        pos = positions['matchup']
        text = f"Matchup: {team_name} vs {opponent}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Game time
    if 'game_time' in positions:
        pos = positions['game_time']
        text = f"🕐 Game Time: {game_time}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # A.I. Rating
    if 'ai_rating' in positions:
        pos = positions['ai_rating']
        stars = '⭐' * min(int(ai_rating - 2.3), 3)
        text = f"A.I. Rating: {ai_rating:.1f} {stars} ({rating_label})"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Season Avg
    if 'season_avg' in positions:
        pos = positions['season_avg']
        text = f"Season Avg: {season_avg:.1f}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Recent Avg
    if 'recent_avg' in positions:
        pos = positions['recent_avg']
        text = f"Recent Avg: {recent_avg:.1f}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # CLV
    if 'clv' in positions and clv_data:
        pos = positions['clv']
        opening_str = f"{clv_data['opening']:+.0f}" if clv_data['opening'] > 0 else str(clv_data['opening'])
        latest_str = f"{clv_data['latest']:+.0f}" if clv_data['latest'] > 0 else str(clv_data['latest'])
        text = f"✅ CLV: Opening: {opening_str} → Latest: {latest_str}"
        color = tuple(pos['color']) if clv_data.get('positive') else (255, 113, 113)
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=color, font=font)
    
    # A.I. Score
    if 'ai_score' in positions:
        pos = positions['ai_score']
        text = f"A.I. Score: {ai_score:.2f}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # Recommendation
    if 'recommendation' in positions:
        pos = positions['recommendation']
        text = f"✅ {prop_text}"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # EV Badge
    if 'ev_badge' in positions and ev and ev > 0:
        pos = positions['ev_badge']
        text = f"+{ev:.1f}% EV"
        font = get_font(pos['font_size'], pos['bold'])
        if pos['align'] == 'right':
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = pos['x'] - text_width
        else:
            x = pos['x']
        draw.text((x, pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # SHARP tag
    if 'sharp_tag' in positions and is_sharp:
        pos = positions['sharp_tag']
        text = "SHARP"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    # TRACKED tag
    if 'tracked_tag' in positions and is_tracked:
        pos = positions['tracked_tag']
        text = "📊 TRACKED"
        font = get_font(pos['font_size'], pos['bold'])
        draw.text((pos['x'], pos['y']), text, fill=tuple(pos['color']), font=font)
    
    return card

if __name__ == "__main__":
    from player_photo_service import get_player_photo
    
    test_data = {
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
    
    player_photo = get_player_photo('Paolo Banchero')
    card = create_card_from_template(test_data, player_photo)
    
    if card:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Precise_Overlay_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card.save(filepath, 'PNG', quality=95)
        print(f"\n✓ Precise overlay saved: {filename}")
        print(f"  Location: {ICLOUD_CARDS_FOLDER}\n")
    else:
        print("✗ Failed to create card")
