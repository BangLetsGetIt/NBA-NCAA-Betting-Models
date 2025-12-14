#!/usr/bin/env python3
"""
Player Photo Service
Fetches and caches player headshots from NBA API or ESPN
"""

import os
import requests
from PIL import Image
from io import BytesIO
from nba_api.stats.static import players

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_CACHE_DIR = os.path.join(SCRIPT_DIR, "images", "player_photos")
os.makedirs(PHOTOS_CACHE_DIR, exist_ok=True)

def get_player_id(player_name):
    """Get NBA player ID from player name"""
    try:
        player_list = players.get_players()
        name_parts = player_name.lower().split()
        
        for player in player_list:
            p_name = player['full_name'].lower()
            p_parts = p_name.split()
            
            # Match first and last name
            if len(name_parts) >= 2 and len(p_parts) >= 2:
                if name_parts[0] in p_parts[0] and name_parts[-1] in p_parts[-1]:
                    return player['id']
        
        return None
    except Exception as e:
        print(f"Error getting player ID for {player_name}: {e}")
        return None

def fetch_player_photo(player_name, player_id=None):
    """
    Fetch player photo from NBA.com CDN
    Returns PIL Image or None
    """
    if player_id is None:
        player_id = get_player_id(player_name)
    
    if player_id is None:
        return None
    
    # Check cache first
    cache_path = os.path.join(PHOTOS_CACHE_DIR, f"{player_id}.png")
    if os.path.exists(cache_path):
        try:
            return Image.open(cache_path)
        except:
            pass
    
    # Try NBA.com CDN
    urls = [
        f"https://cdn.nba.com/headshots/nba/latest/260x190/{player_id}.png",
        f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{player_id}.png",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # Save to cache
                img.save(cache_path)
                return img
        except Exception as e:
            continue
    
    return None

def get_player_photo(player_name, create_placeholder=True):
    """
    Get player photo, with fallback to placeholder
    Returns PIL Image
    """
    player_id = get_player_id(player_name)
    photo = None
    
    if player_id:
        photo = fetch_player_photo(player_name, player_id)
    
    if photo:
        return photo
    
    # Create placeholder if requested
    if create_placeholder:
        return create_placeholder_image(player_name)
    
    return None

def create_placeholder_image(player_name):
    """Create a simple placeholder image"""
    img = Image.new('RGB', (260, 190), color=(40, 40, 40))
    from PIL import ImageDraw, ImageFont
    
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font = ImageFont.load_default()
    
    # Draw player initials
    initials = ''.join([name[0].upper() for name in player_name.split()[:2]])
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    position = ((260 - text_width) // 2, (190 - text_height) // 2)
    draw.text(position, initials, fill=(200, 200, 200), font=font)
    
    return img
