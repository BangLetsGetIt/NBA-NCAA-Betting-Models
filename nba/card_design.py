#!/usr/bin/env python3
"""
Card Design Module
Handles layout, styling, and rendering of player prop cards
Matches the modern design with action photo and card layout
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import math
import random

# Color Palette
COLORS = {
    'background': '#1a2332',  # Dark blue background
    'card_bg': '#2a3441',     # Dark grey card background
    'text_primary': '#ffffff',
    'text_secondary': '#94a3b8',  # Light grey
    'accent_green': '#4ade80',    # Green for positive indicators
    'accent_red': '#f87171',   # Red/pink for recommendations
    'accent_blue': '#60a5fa',   # Blue for SHARP tag
    'star_yellow': '#fbbf24',   # Yellow for stars
}

# Card dimensions - match your Canva template
CARD_WIDTH = 1080
CARD_HEIGHT = 1350  # Match your template size

def get_font(size, bold=False):
    """Get font, with fallbacks"""
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

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_torn_edge_mask(width, height, edge_y, roughness=20):
    """Create a mask for torn/ripped edge effect"""
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    # Create jagged edge
    points = []
    for x in range(0, width, 5):
        y_offset = random.randint(-roughness, roughness)
        points.append((x, edge_y + y_offset))
    
    # Fill above the edge
    points = [(0, 0)] + points + [(width, 0), (0, 0)]
    draw.polygon(points, fill=255)
    
    # Apply blur for smoother edge
    mask = mask.filter(ImageFilter.GaussianBlur(radius=2))
    return mask

def draw_rounded_rectangle(draw, xy, radius, fill=None, outline=None, width=1):
    """Draw rounded rectangle"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill, outline=outline, width=width)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill, outline=outline, width=width)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill, outline=outline, width=width)

def draw_star(draw, center_x, center_y, size, fill):
    """Draw a star"""
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

def create_card_base():
    """Create base card with dark blue background"""
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), color=hex_to_rgb(COLORS['background']))
    return img, ImageDraw.Draw(img)

def draw_action_photo(img, draw, player_photo, photo_y_end):
    """Draw action photo at top with torn edge effect"""
    if not player_photo:
        return
    
    # Resize photo to cover top portion
    photo_width = CARD_WIDTH
    photo_height = photo_y_end
    
    # Resize maintaining aspect ratio, crop if needed
    photo_aspect = player_photo.width / player_photo.height
    target_aspect = photo_width / photo_height
    
    if photo_aspect > target_aspect:
        # Photo is wider, fit height
        new_height = photo_height
        new_width = int(photo_height * photo_aspect)
        resized = player_photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop center
        left = (new_width - photo_width) // 2
        resized = resized.crop((left, 0, left + photo_width, photo_height))
    else:
        # Photo is taller, fit width
        new_width = photo_width
        new_height = int(photo_width / photo_aspect)
        resized = player_photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # Crop center
        top = (new_height - photo_height) // 2
        resized = resized.crop((0, top, photo_width, top + photo_height))
    
    # Create torn edge mask
    mask = create_torn_edge_mask(photo_width, photo_height, photo_height - 1, roughness=25)
    
    # Paste photo with mask
    img.paste(resized, (0, 0), mask)

def draw_card_header(img, draw, rank, prop_text, player_name):
    """Draw card header: #1 • UNDER 22.5 PTS (left) and Player Name (right)"""
    y_start = 1200  # Card starts here
    padding = 40
    
    # Left side: Rank and prop
    font_prop = get_font(24, bold=False)
    prop_color = hex_to_rgb(COLORS['accent_red'])
    draw.text((padding, y_start + 20), f"#{rank} • {prop_text}", 
              fill=prop_color, font=font_prop)
    
    # Right side: Player name
    font_name = get_font(32, bold=True)
    name_bbox = draw.textbbox((0, 0), player_name, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((CARD_WIDTH - padding - name_width, y_start + 15), player_name,
              fill=hex_to_rgb(COLORS['text_primary']), font=font_name)

def draw_player_details(img, draw, player_name, matchup, game_time):
    """Draw Player, Matchup, Game Time details"""
    y_start = 1280
    padding = 40
    line_height = 35
    
    font_label = get_font(18)
    font_value = get_font(18, bold=True)
    
    # Player
    draw.text((padding, y_start), "Player:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 100, y_start), player_name,
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)
    
    # Matchup
    y_start += line_height
    draw.text((padding, y_start), "Matchup:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 100, y_start), matchup,
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)
    
    # Game Time (with clock icon)
    y_start += line_height
    clock_icon = "🕐"
    draw.text((padding, y_start), f"{clock_icon} Game Time:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 140, y_start), game_time,
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)

def draw_ai_rating(img, draw, ai_rating, rating_label):
    """Draw A.I. Rating with stars"""
    y_start = 1400
    padding = 40
    
    font_label = get_font(18)
    font_value = get_font(28, bold=True)
    
    # A.I. Rating label
    draw.text((padding, y_start), "A.I. Rating:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    
    # Rating value
    rating_text = f"{ai_rating:.1f}"
    draw.text((padding + 130, y_start - 5), rating_text,
              fill=hex_to_rgb(COLORS['accent_green']), font=font_value)
    
    # Stars
    star_size = 20
    star_spacing = 25
    star_x = padding + 130 + 80
    star_y = y_start + 5
    
    # Calculate number of full and half stars
    full_stars = int(ai_rating - 2.3)  # Assuming 2.3-4.9 range
    has_half = (ai_rating - 2.3) % 1 >= 0.5
    
    for i in range(3):  # Max 3 stars
        if i < full_stars:
            draw_star(draw, star_x + i * star_spacing, star_y, star_size // 2, 
                     hex_to_rgb(COLORS['star_yellow']))
        elif i == full_stars and has_half:
            # Half star (simplified - just draw smaller)
            draw_star(draw, star_x + i * star_spacing, star_y, star_size // 3, 
                     hex_to_rgb(COLORS['star_yellow']))
    
    # Premium Play badge
    font_badge = get_font(16)
    badge_text = f"({rating_label})"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_width = badge_bbox[2] - badge_bbox[0]
    draw.text((CARD_WIDTH - padding - badge_width, y_start), badge_text,
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_badge)
    
    # Green outline around rating section
    draw.rectangle([padding - 5, y_start - 5, CARD_WIDTH - padding + 5, y_start + 35],
                   outline=hex_to_rgb(COLORS['accent_green']), width=2)

def draw_stats(img, draw, season_avg, recent_avg):
    """Draw Season Avg and Recent Avg"""
    y_start = 1460
    padding = 40
    line_height = 35
    
    font_label = get_font(18)
    font_value = get_font(18, bold=True)
    
    # Season Avg
    draw.text((padding, y_start), "Season Avg:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 140, y_start), f"{season_avg:.1f}",
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)
    
    # Recent Avg
    y_start += line_height
    draw.text((padding, y_start), "Recent Avg:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 140, y_start), f"{recent_avg:.1f}",
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)

def draw_clv(img, draw, clv_data):
    """Draw CLV section with opening/latest odds"""
    if not clv_data:
        return
    
    y_start = 1540
    padding = 40
    
    font_label = get_font(18)
    font_value = get_font(18, bold=True)
    
    # Checkmark and CLV label
    checkmark = "✅"
    clv_color = hex_to_rgb(COLORS['accent_green']) if clv_data.get('positive') else hex_to_rgb(COLORS['accent_red'])
    
    draw.text((padding, y_start), f"{checkmark} CLV:", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    
    # Opening → Latest
    opening_str = f"{clv_data['opening']:+.0f}" if clv_data['opening'] > 0 else str(clv_data['opening'])
    latest_str = f"{clv_data['latest']:+.0f}" if clv_data['latest'] > 0 else str(clv_data['latest'])
    clv_text = f"Opening: {opening_str} → Latest: {latest_str}"
    
    draw.text((padding + 80, y_start), clv_text,
              fill=clv_color, font=font_value)

def draw_ai_score(img, draw, ai_score):
    """Draw A.I. Score"""
    y_start = 1600
    padding = 40
    
    font_label = get_font(18)
    font_value = get_font(18, bold=True)
    
    draw.text((padding, y_start), "A.I. Score", 
              fill=hex_to_rgb(COLORS['text_secondary']), font=font_label)
    draw.text((padding + 140, y_start), f"{ai_score:.2f}",
              fill=hex_to_rgb(COLORS['text_primary']), font=font_value)

def draw_recommendation_box(img, draw, prop_text, ev, is_sharp, is_tracked):
    """Draw bottom recommendation box with prop, EV badge, and tags"""
    y_start = 1680
    padding = 40
    box_height = 180
    radius = 12
    
    # Recommendation box
    box_y = y_start
    box_x = padding
    box_width = CARD_WIDTH - 2 * padding
    
    draw_rounded_rectangle(draw, 
                          (box_x, box_y, box_x + box_width, box_y + box_height),
                          radius,
                          fill=None,
                          outline=hex_to_rgb(COLORS['accent_red']),
                          width=3)
    
    # Main recommendation with checkmark
    font_prop = get_font(32, bold=True)
    checkmark = "✅"
    prop_display = f"{checkmark} {prop_text}"
    
    prop_bbox = draw.textbbox((0, 0), prop_display, font=font_prop)
    prop_width = prop_bbox[2] - prop_bbox[0]
    draw.text((box_x + 20, box_y + 20), prop_display,
              fill=hex_to_rgb(COLORS['text_primary']), font=font_prop)
    
    # EV badge (pill-shaped)
    if ev and ev > 0:
        ev_text = f"+{ev:.1f}% EV"
        font_ev = get_font(18, bold=True)
        ev_bbox = draw.textbbox((0, 0), ev_text, font=font_ev)
        ev_width = ev_bbox[2] - ev_bbox[0] + 20
        ev_height = 35
        
        # Draw pill background
        ev_x = box_x + box_width - ev_width - 20
        ev_y = box_y + 20
        draw_rounded_rectangle(draw,
                              (ev_x, ev_y, ev_x + ev_width, ev_y + ev_height),
                              ev_height // 2,
                              fill=hex_to_rgb(COLORS['accent_green']),
                              outline=None)
        
        draw.text((ev_x + 10, ev_y + 8), ev_text,
                  fill=hex_to_rgb(COLORS['text_primary']), font=font_ev)
    
    # Tags row
    tag_y = box_y + 70
    tag_height = 30
    tag_spacing = 10
    
    # SHARP tag
    if is_sharp:
        sharp_text = "SHARP"
        font_tag = get_font(16, bold=True)
        sharp_bbox = draw.textbbox((0, 0), sharp_text, font=font_tag)
        sharp_width = sharp_bbox[2] - sharp_bbox[0] + 16
        
        sharp_x = box_x + 20
        draw_rounded_rectangle(draw,
                              (sharp_x, tag_y, sharp_x + sharp_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=hex_to_rgb(COLORS['accent_blue']),
                              outline=None)
        draw.text((sharp_x + 8, tag_y + 6), sharp_text,
                  fill=hex_to_rgb(COLORS['text_primary']), font=font_tag)
    
    # TRACKED tag
    if is_tracked:
        tracked_text = "📊 TRACKED"
        font_tag = get_font(16, bold=True)
        tracked_bbox = draw.textbbox((0, 0), tracked_text, font=font_tag)
        tracked_width = tracked_bbox[2] - tracked_bbox[0] + 16
        
        tracked_x = box_x + 20 + (sharp_width + tag_spacing if is_sharp else 0)
        draw_rounded_rectangle(draw,
                              (tracked_x, tag_y, tracked_x + tracked_width, tag_y + tag_height),
                              tag_height // 2,
                              fill=hex_to_rgb(COLORS['accent_red']),
                              outline=None)
        draw.text((tracked_x + 8, tag_y + 6), tracked_text,
                  fill=hex_to_rgb(COLORS['text_primary']), font=font_tag)

def create_player_card(player_data, player_photo=None):
    """
    Create complete player prop card matching the example design
    player_data should contain:
    - rank (int, e.g., 1)
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
    img, draw = create_card_base()
    
    # Photo takes up top 60% of card
    photo_y_end = int(CARD_HEIGHT * 0.6)
    
    # Draw action photo with torn edge
    draw_action_photo(img, draw, player_photo, photo_y_end)
    
    # Card starts at photo_y_end
    card_y_start = photo_y_end
    
    # Draw card background
    card_height = CARD_HEIGHT - card_y_start
    draw.rectangle([0, card_y_start, CARD_WIDTH, CARD_HEIGHT],
                   fill=hex_to_rgb(COLORS['card_bg']))
    
    # Draw all card sections
    draw_card_header(img, draw,
                     player_data.get('rank', 1),
                     player_data.get('prop_text', ''),
                     player_data.get('player_name', ''))
    
    matchup = f"{player_data.get('team_name', '')} vs {player_data.get('opponent', '')}"
    draw_player_details(img, draw,
                       player_data.get('player_name', ''),
                       matchup,
                       player_data.get('game_time', 'TBD'))
    
    draw_ai_rating(img, draw,
                  player_data.get('ai_rating', 2.3),
                  player_data.get('rating_label', 'STANDARD PLAY'))
    
    draw_stats(img, draw,
              player_data.get('season_avg', 0),
              player_data.get('recent_avg', 0))
    
    if player_data.get('clv_data'):
        draw_clv(img, draw, player_data['clv_data'])
    
    draw_ai_score(img, draw,
                 player_data.get('ai_score', 0))
    
    draw_recommendation_box(img, draw,
                           player_data.get('prop_text', ''),
                           player_data.get('ev'),
                           player_data.get('is_sharp', False),
                           player_data.get('is_tracked', False))
    
    return img
