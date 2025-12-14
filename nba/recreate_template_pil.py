#!/usr/bin/env python3
"""
Recreate Canva Template with PIL
Attempts to match the template design exactly using programmatic generation
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

# Match your template dimensions
CARD_WIDTH = 1080
CARD_HEIGHT = 1350

# Color Palette - extract from your template
COLORS = {
    'background': (26, 35, 50),      # Dark blue background
    'card_bg': (42, 52, 65),         # Dark grey card
    'text_primary': (255, 255, 255),
    'text_secondary': (148, 163, 184),
    'accent_green': (74, 222, 128),
    'accent_red': (255, 113, 113),
    'accent_blue': (96, 165, 250),
    'star_yellow': (251, 191, 36),
}

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

def draw_rounded_rectangle(draw, xy, radius, fill=None, outline=None, width=1):
    """Draw rounded rectangle"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill, outline=outline, width=width)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill, outline=outline, width=width)

def create_template_recreation(player_data, player_photo=None):
    """
    Recreate the template design programmatically
    This should match your Canva template closely
    """
    # Create base with background color
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=COLORS['background'])
    draw = ImageDraw.Draw(img)
    
    # Photo area (top portion) - approximately 60% of height
    photo_height = int(CARD_HEIGHT * 0.6)
    
    # Draw player photo if available
    if player_photo:
        # Resize and position photo
        photo_resized = player_photo.resize((CARD_WIDTH, photo_height), Image.Resampling.LANCZOS)
        img.paste(photo_resized, (0, 0))
        
        # Add torn edge effect at bottom of photo
        # Create gradient mask for torn edge
        mask = Image.new('L', (CARD_WIDTH, 50), 0)
        mask_draw = ImageDraw.Draw(mask)
        for y in range(50):
            alpha = int(255 * (1 - y / 50))
            mask_draw.rectangle([0, y, CARD_WIDTH, y+1], fill=alpha)
        img.paste(photo_resized.crop((0, photo_height-50, CARD_WIDTH, photo_height)), 
                 (0, photo_height-50), mask)
    else:
        # Placeholder gradient for photo area
        for y in range(photo_height):
            intensity = int(40 + (y / photo_height) * 20)
            draw.rectangle([0, y, CARD_WIDTH, y+1], fill=(intensity, intensity, intensity))
    
    # Card section (bottom)
    card_y_start = photo_height - 20  # Overlap slightly
    card_height = CARD_HEIGHT - card_y_start
    
    # Draw card background with rounded top corners
    draw.rectangle([0, card_y_start, CARD_WIDTH, CARD_HEIGHT], fill=COLORS['card_bg'])
    
    # Rounded top corners for card
    corner_radius = 20
    # Top-left corner
    draw.ellipse([0, card_y_start, corner_radius*2, card_y_start + corner_radius*2], 
                fill=COLORS['card_bg'])
    # Top-right corner
    draw.ellipse([CARD_WIDTH - corner_radius*2, card_y_start, CARD_WIDTH, card_y_start + corner_radius*2], 
                fill=COLORS['card_bg'])
    
    # Now draw all text elements matching your template
    # Adjust these coordinates to match your actual template
    
    y_start = card_y_start + 30
    
    # Rank + Prop (top left, red/pink)
    font_prop = get_font(24, False)
    rank_prop = f"#{player_data.get('rank', 1)} • {player_data.get('prop_text', '')}"
    draw.text((40, y_start), rank_prop, fill=COLORS['accent_red'], font=font_prop)
    
    # Player name (top right, white, bold)
    font_name = get_font(32, True)
    player_name = player_data.get('player_name', '')
    name_bbox = draw.textbbox((0, 0), player_name, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((CARD_WIDTH - 40 - name_width, y_start - 5), player_name, 
             fill=COLORS['text_primary'], font=font_name)
    
    y_start += 60
    
    # Player label
    font_label = get_font(18, False)
    draw.text((40, y_start), f"Player: {player_name}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 35
    
    # Matchup
    matchup = f"{player_data.get('team_name', '')} vs {player_data.get('opponent', '')}"
    draw.text((40, y_start), f"Matchup: {matchup}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 35
    
    # Game time
    game_time = player_data.get('game_time', 'TBD')
    draw.text((40, y_start), f"🕐 Game Time: {game_time}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 50
    
    # A.I. Rating with stars
    ai_rating = player_data.get('ai_rating', 2.3)
    rating_label = player_data.get('rating_label', 'STANDARD PLAY')
    stars = '⭐' * min(int(ai_rating - 2.3), 3)
    rating_text = f"A.I. Rating: {ai_rating:.1f} {stars} ({rating_label})"
    draw.text((40, y_start), rating_text, 
             fill=COLORS['accent_green'], font=font_label)
    
    # Green outline box around rating
    draw.rectangle([35, y_start - 5, CARD_WIDTH - 35, y_start + 30], 
                 outline=COLORS['accent_green'], width=2)
    
    y_start += 60
    
    # Season Avg
    season_avg = player_data.get('season_avg', 0)
    draw.text((40, y_start), f"Season Avg: {season_avg:.1f}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 35
    
    # Recent Avg
    recent_avg = player_data.get('recent_avg', 0)
    draw.text((40, y_start), f"Recent Avg: {recent_avg:.1f}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 45
    
    # CLV
    clv_data = player_data.get('clv_data')
    if clv_data:
        opening_str = f"{clv_data['opening']:+.0f}" if clv_data['opening'] > 0 else str(clv_data['opening'])
        latest_str = f"{clv_data['latest']:+.0f}" if clv_data['latest'] > 0 else str(clv_data['latest'])
        clv_text = f"✅ CLV: Opening: {opening_str} → Latest: {latest_str}"
        clv_color = COLORS['accent_green'] if clv_data.get('positive') else COLORS['accent_red']
        draw.text((40, y_start), clv_text, fill=clv_color, font=font_label)
    
    y_start += 60
    
    # A.I. Score
    ai_score = player_data.get('ai_score', 0)
    draw.text((40, y_start), f"A.I. Score: {ai_score:.2f}", 
             fill=COLORS['text_secondary'], font=font_label)
    
    y_start += 80
    
    # Recommendation box (bottom)
    box_y = y_start
    box_height = 100
    box_radius = 12
    
    # Draw box with rounded corners
    draw_rounded_rectangle(draw, 
                          (40, box_y, CARD_WIDTH - 40, box_y + box_height),
                          box_radius,
                          fill=None,
                          outline=COLORS['accent_red'],
                          width=3)
    
    # Recommendation text
    prop_text = player_data.get('prop_text', '')
    font_rec = get_font(32, True)
    draw.text((60, box_y + 20), f"✅ {prop_text}", 
             fill=COLORS['text_primary'], font=font_rec)
    
    # EV badge (right side of box)
    ev = player_data.get('ev')
    if ev and ev > 0:
        ev_text = f"+{ev:.1f}% EV"
        font_ev = get_font(18, True)
        ev_bbox = draw.textbbox((0, 0), ev_text, font=font_ev)
        ev_width = ev_bbox[2] - ev_bbox[0] + 20
        ev_x = CARD_WIDTH - 60 - ev_width
        
        # Pill background for EV
        draw_rounded_rectangle(draw,
                              (ev_x, box_y + 20, ev_x + ev_width, box_y + 55),
                              17,
                              fill=COLORS['accent_green'],
                              outline=None)
        draw.text((ev_x + 10, box_y + 28), ev_text,
                 fill=COLORS['text_primary'], font=font_ev)
    
    # Tags row
    tag_y = box_y + 70
    tag_height = 30
    
    # SHARP tag
    if player_data.get('is_sharp'):
        sharp_text = "SHARP"
        font_tag = get_font(16, True)
        sharp_bbox = draw.textbbox((0, 0), sharp_text, font=font_tag)
        sharp_width = sharp_bbox[2] - sharp_bbox[0] + 16
        
        draw_rounded_rectangle(draw,
                              (60, tag_y, 60 + sharp_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=COLORS['accent_blue'],
                              outline=None)
        draw.text((60 + 8, tag_y + 6), sharp_text,
                 fill=COLORS['text_primary'], font=font_tag)
    
    # TRACKED tag
    if player_data.get('is_tracked'):
        tracked_text = "📊 TRACKED"
        font_tag = get_font(16, True)
        tracked_bbox = draw.textbbox((0, 0), tracked_text, font=font_tag)
        tracked_width = tracked_bbox[2] - tracked_bbox[0] + 16
        
        tracked_x = 60 + (sharp_width + 10 if player_data.get('is_sharp') else 0)
        draw_rounded_rectangle(draw,
                              (tracked_x, tag_y, tracked_x + tracked_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=COLORS['accent_red'],
                              outline=None)
        draw.text((tracked_x + 8, tag_y + 6), tracked_text,
                 fill=COLORS['text_primary'], font=font_tag)
    
    return img

if __name__ == "__main__":
    from player_photo_service import get_player_photo
    
    # Test with sample data
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
    card = create_template_recreation(test_data, player_photo)
    
    # Save test
    from datetime import datetime
    import os
    
    ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
    os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PIL_Recreation_{timestamp}.png"
    filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
    card.save(filepath, 'PNG', quality=95)
    
    print(f"\n✓ PIL recreation saved: {filename}")
    print(f"  Location: {ICLOUD_CARDS_FOLDER}\n")
