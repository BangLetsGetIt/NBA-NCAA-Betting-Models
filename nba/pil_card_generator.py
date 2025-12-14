#!/usr/bin/env python3
"""
PIL Card Generator - Full Template Recreation
Recreates the Canva template design entirely programmatically
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import math
import random

# Card dimensions - match your Canva template exactly
CARD_WIDTH = 1080
CARD_HEIGHT = 1350

# Color Palette - extracted from template
COLORS = {
    'background': (26, 35, 50),      # Dark blue background #1a2332
    'card_bg': (42, 52, 65),        # Dark grey card #2a3441
    'text_primary': (255, 255, 255), # White
    'text_secondary': (148, 163, 184), # Light grey #94a3b8
    'accent_green': (74, 222, 128),   # Green #4ade80
    'accent_red': (255, 113, 113),    # Red/pink #ff7171
    'accent_blue': (96, 165, 250),    # Blue #60a5fa
    'star_yellow': (251, 191, 36),    # Yellow #fbbf24
}

def get_font(size, bold=False):
    """Get font with fallbacks"""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Inter-Bold.otf" if bold else "/System/Library/Fonts/Supplemental/Inter-Regular.otf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
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
    # Fill main rectangle
    if fill:
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=None)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=None)
        # Fill corners
        draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill, outline=None)
        draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill, outline=None)
        draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill, outline=None)
        draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill, outline=None)
    
    # Draw outline
    if outline:
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=None, outline=outline, width=width)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=None, outline=outline, width=width)
        draw.arc([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=outline, width=width)
        draw.arc([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=outline, width=width)
        draw.arc([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=outline, width=width)
        draw.arc([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=outline, width=width)

def draw_star(draw, center_x, center_y, size, fill):
    """Draw a 5-pointed star"""
    points = []
    for i in range(10):
        angle = (i * 36 - 90) * math.pi / 180
        if i % 2 == 0:
            r = size
        else:
            r = size * 0.4
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=fill)

def create_torn_edge_mask(width, height, edge_y, roughness=25):
    """Create a mask for torn/ripped edge effect at bottom of photo"""
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    # Create jagged edge
    points = []
    for x in range(0, width, 4):
        y_offset = random.randint(-roughness, roughness)
        points.append((x, edge_y + y_offset))
    
    # Fill above the edge
    points = [(0, 0)] + points + [(width, 0), (0, 0)]
    draw.polygon(points, fill=255)
    
    # Apply blur for smoother edge
    mask = mask.filter(ImageFilter.GaussianBlur(radius=3))
    return mask

def draw_player_photo(img, player_photo, photo_height):
    """Draw player photo in top section with torn edge"""
    if not player_photo:
        # Create gradient placeholder
        for y in range(photo_height):
            intensity = int(30 + (y / photo_height) * 20)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, y, CARD_WIDTH, y+1], fill=(intensity, intensity, intensity))
        return
    
    # Resize photo to cover photo area
    photo_aspect = player_photo.width / player_photo.height
    target_aspect = CARD_WIDTH / photo_height
    
    if photo_aspect > target_aspect:
        # Photo is wider, fit height
        new_height = photo_height
        new_width = int(photo_height * photo_aspect)
        resized = player_photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop center
        left = (new_width - CARD_WIDTH) // 2
        resized = resized.crop((left, 0, left + CARD_WIDTH, photo_height))
    else:
        # Photo is taller, fit width
        new_width = CARD_WIDTH
        new_height = int(CARD_WIDTH / photo_aspect)
        resized = player_photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop center
        top = (new_height - photo_height) // 2
        resized = resized.crop((0, top, CARD_WIDTH, top + photo_height))
    
    # Create torn edge mask
    mask = create_torn_edge_mask(CARD_WIDTH, photo_height, photo_height - 1, roughness=25)
    
    # Paste photo with mask
    img.paste(resized, (0, 0), mask)

def create_card(player_data, player_photo=None):
    """
    Create complete player prop card matching the Canva template
    
    player_data should contain:
    - rank (int)
    - player_name
    - team_name
    - opponent
    - prop_text (e.g., "UNDER 22.5 PTS")
    - game_time (formatted string)
    - ai_rating (float, 2.3-4.9)
    - rating_label (e.g., "PREMIUM PLAY")
    - season_avg (float)
    - recent_avg (float)
    - clv_data (dict with opening, latest, positive) - optional
    - ai_score (float)
    - ev (float) - optional
    - is_sharp (bool) - optional
    - is_tracked (bool) - optional
    """
    # Create base image
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=COLORS['background'])
    draw = ImageDraw.Draw(img)
    
    # Photo area: top 60% (~810px)
    photo_height = int(CARD_HEIGHT * 0.6)
    
    # Draw player photo
    draw_player_photo(img, player_photo, photo_height)
    
    # Card section starts at ~790px (overlaps photo by ~20px)
    card_y_start = photo_height - 20
    card_height = CARD_HEIGHT - card_y_start
    
    # Draw card background with rounded top corners
    draw.rectangle([0, card_y_start, CARD_WIDTH, CARD_HEIGHT], fill=COLORS['card_bg'])
    
    # Rounded top corners
    corner_radius = 20
    # Top-left corner
    draw.ellipse([0, card_y_start, corner_radius*2, card_y_start + corner_radius*2], 
                fill=COLORS['card_bg'])
    # Top-right corner
    draw.ellipse([CARD_WIDTH - corner_radius*2, card_y_start, CARD_WIDTH, card_y_start + corner_radius*2], 
                fill=COLORS['card_bg'])
    
    # Padding
    padding = 40
    y = card_y_start + 30
    
    # Rank + Prop (top left, red/pink)
    rank = player_data.get('rank', 1)
    prop_text = player_data.get('prop_text', '')
    font_prop = get_font(24, False)
    rank_prop_text = f"#{rank} • {prop_text}"
    draw.text((padding, y), rank_prop_text, fill=COLORS['accent_red'], font=font_prop)
    
    # Player name (top right, white, bold)
    player_name = player_data.get('player_name', '')
    font_name = get_font(32, True)
    name_bbox = draw.textbbox((0, 0), player_name, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((CARD_WIDTH - padding - name_width, y - 5), player_name,
             fill=COLORS['text_primary'], font=font_name)
    
    y += 60
    
    # Player label
    font_label = get_font(18, False)
    draw.text((padding, y), f"Player: {player_name}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 35
    
    # Matchup
    team_name = player_data.get('team_name', '')
    opponent = player_data.get('opponent', '')
    matchup = f"{team_name} vs {opponent}"
    draw.text((padding, y), f"Matchup: {matchup}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 35
    
    # Game time
    game_time = player_data.get('game_time', 'TBD')
    draw.text((padding, y), f"🕐 Game Time: {game_time}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 50
    
    # A.I. Rating with stars
    ai_rating = player_data.get('ai_rating', 2.3)
    rating_label = player_data.get('rating_label', 'STANDARD PLAY')
    
    # Calculate stars (rating 2.3-4.9 maps to 0-3 stars)
    star_count = min(int(ai_rating - 2.3), 3)
    stars = '⭐' * star_count
    
    rating_text = f"A.I. Rating: {ai_rating:.1f} {stars} ({rating_label})"
    draw.text((padding, y), rating_text,
             fill=COLORS['accent_green'], font=font_label)
    
    # Green outline box around rating
    rating_bbox = draw.textbbox((padding, y), rating_text, font=font_label)
    draw.rectangle([padding - 5, y - 5, CARD_WIDTH - padding + 5, rating_bbox[3] + 5],
                 outline=COLORS['accent_green'], width=2)
    
    y += 60
    
    # Season Avg
    season_avg = player_data.get('season_avg', 0)
    draw.text((padding, y), f"Season Avg: {season_avg:.1f}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 35
    
    # Recent Avg
    recent_avg = player_data.get('recent_avg', 0)
    draw.text((padding, y), f"Recent Avg: {recent_avg:.1f}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 45
    
    # CLV
    clv_data = player_data.get('clv_data')
    if clv_data:
        opening_str = f"{clv_data['opening']:+.0f}" if clv_data['opening'] > 0 else str(clv_data['opening'])
        latest_str = f"{clv_data['latest']:+.0f}" if clv_data['latest'] > 0 else str(clv_data['latest'])
        clv_text = f"✅ CLV: Opening: {opening_str} → Latest: {latest_str}"
        clv_color = COLORS['accent_green'] if clv_data.get('positive') else COLORS['accent_red']
        draw.text((padding, y), clv_text, fill=clv_color, font=font_label)
        y += 60
    
    # A.I. Score
    ai_score = player_data.get('ai_score', 0)
    draw.text((padding, y), f"A.I. Score: {ai_score:.2f}",
             fill=COLORS['text_secondary'], font=font_label)
    
    y += 80
    
    # Recommendation box (bottom)
    box_y = y
    box_height = 100
    box_radius = 12
    
    # Draw box with rounded corners and red border
    draw_rounded_rectangle(draw,
                          (padding, box_y, CARD_WIDTH - padding, box_y + box_height),
                          box_radius,
                          fill=None,
                          outline=COLORS['accent_red'],
                          width=3)
    
    # Recommendation text
    font_rec = get_font(32, True)
    rec_text = f"✅ {prop_text}"
    draw.text((padding + 20, box_y + 20), rec_text,
             fill=COLORS['text_primary'], font=font_rec)
    
    # EV badge (right side of box)
    ev = player_data.get('ev')
    if ev and ev > 0:
        ev_text = f"+{ev:.1f}% EV"
        font_ev = get_font(18, True)
        ev_bbox = draw.textbbox((0, 0), ev_text, font=font_ev)
        ev_width = ev_bbox[2] - ev_bbox[0] + 20
        ev_height = 35
        ev_x = CARD_WIDTH - padding - ev_width - 20
        ev_y = box_y + 20
        
        # Pill background for EV
        draw_rounded_rectangle(draw,
                              (ev_x, ev_y, ev_x + ev_width, ev_y + ev_height),
                              ev_height // 2,
                              fill=COLORS['accent_green'],
                              outline=None)
        draw.text((ev_x + 10, ev_y + 8), ev_text,
                 fill=COLORS['text_primary'], font=font_ev)
    
    # Tags row
    tag_y = box_y + 70
    tag_height = 30
    tag_x = padding + 20
    
    # SHARP tag
    if player_data.get('is_sharp'):
        sharp_text = "SHARP"
        font_tag = get_font(16, True)
        sharp_bbox = draw.textbbox((0, 0), sharp_text, font=font_tag)
        sharp_width = sharp_bbox[2] - sharp_bbox[0] + 16
        
        draw_rounded_rectangle(draw,
                              (tag_x, tag_y, tag_x + sharp_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=COLORS['accent_blue'],
                              outline=None)
        draw.text((tag_x + 8, tag_y + 6), sharp_text,
                 fill=COLORS['text_primary'], font=font_tag)
        tag_x += sharp_width + 10
    
    # TRACKED tag
    if player_data.get('is_tracked'):
        tracked_text = "📊 TRACKED"
        font_tag = get_font(16, True)
        tracked_bbox = draw.textbbox((0, 0), tracked_text, font=font_tag)
        tracked_width = tracked_bbox[2] - tracked_bbox[0] + 16
        
        draw_rounded_rectangle(draw,
                              (tag_x, tag_y, tag_x + tracked_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=COLORS['accent_red'],
                              outline=None)
        draw.text((tag_x + 8, tag_y + 6), tracked_text,
                 fill=COLORS['text_primary'], font=font_tag)
    
    return img
