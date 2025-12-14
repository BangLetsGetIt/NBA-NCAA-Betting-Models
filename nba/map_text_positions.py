#!/usr/bin/env python3
"""
Interactive tool to map text positions on your Canva design
Helps identify where each text element should be placed
"""

import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

CANVA_BACKGROUND_DIR = Path(__file__).parent / "images" / "canva_backgrounds"
background_file = CANVA_BACKGROUND_DIR / "card_template.png"

if not background_file.exists():
    # Try alternative names
    bg_files = list(CANVA_BACKGROUND_DIR.glob("*.png")) + list(CANVA_BACKGROUND_DIR.glob("*.jpg"))
    if bg_files:
        background_file = bg_files[0]
        print(f"Using: {background_file.name}")
    else:
        print(f"✗ No background image found in {CANVA_BACKGROUND_DIR}")
        print("\nPlease save your Canva design as:")
        print(f"  {CANVA_BACKGROUND_DIR}/card_template.png")
        exit(1)

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

def create_preview_with_labels():
    """Create a preview image with labeled text areas"""
    print(f"\nLoading background: {background_file.name}")
    bg = Image.open(background_file).convert('RGB')
    width, height = bg.size
    
    print(f"Image size: {width} x {height}")
    
    # Create a copy with labels
    preview = bg.copy()
    draw = ImageDraw.Draw(preview)
    
    # Sample text to help identify positions
    sample_data = {
        'rank': '#1',
        'prop_text': 'UNDER 22.5 PTS',
        'player_name': 'Paolo Banchero',
        'team_name': 'Orlando Magic',
        'opponent': 'New York Knicks',
        'game_time': '12/13 05:30 PM ET',
        'ai_rating': '4.9',
        'rating_label': 'PREMIUM PLAY',
        'season_avg': '20.2',
        'recent_avg': '14.3',
        'clv': 'Opening: +100 → Latest: -104',
        'ai_score': '10.00',
        'ev': '+37.3% EV',
    }
    
    # Draw labeled boxes to help identify positions
    # These are starting positions - you'll adjust based on your design
    labels = [
        ('#1 • UNDER 22.5 PTS', (40, 1200), 24, True, (255, 113, 113)),  # Top left - red/pink
        ('Paolo Banchero', (width - 300, 1200), 32, True, (255, 255, 255)),  # Top right - white
        ('Player: Paolo Banchero', (40, 1280), 18, False, (148, 163, 184)),  # Light grey
        ('Matchup: Orlando Magic vs New York Knicks', (40, 1315), 18, False, (148, 163, 184)),
        ('🕐 Game Time: 12/13 05:30 PM ET', (40, 1350), 18, False, (148, 163, 184)),
        ('A.I. Rating: 4.9 ⭐⭐ (PREMIUM PLAY)', (40, 1400), 18, False, (74, 222, 128)),  # Green
        ('Season Avg: 20.2', (40, 1460), 18, False, (148, 163, 184)),
        ('Recent Avg: 14.3', (40, 1495), 18, False, (148, 163, 184)),
        ('✅ CLV: Opening: +100 → Latest: -104', (40, 1540), 18, False, (74, 222, 128)),
        ('A.I. Score: 10.00', (40, 1600), 18, False, (148, 163, 184)),
        ('✅ UNDER 22.5 PTS', (40, 1680), 32, True, (255, 255, 255)),  # Bottom box
        ('+37.3% EV', (width - 200, 1680), 18, True, (74, 222, 128)),
        ('SHARP', (40, 1750), 16, True, (96, 165, 250)),  # Blue
        ('📊 TRACKED', (150, 1750), 16, True, (255, 113, 113)),  # Red/pink
    ]
    
    print("\nDrawing sample text labels...")
    print("(These are approximate positions - adjust based on your design)\n")
    
    for text, (x, y), size, bold, color in labels:
        font = get_font(size, bold)
        # Draw text with slight background for visibility
        bbox = draw.textbbox((x, y), text, font=font)
        draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], 
                      fill=(0, 0, 0, 180))  # Semi-transparent black background
        draw.text((x, y), text, fill=color, font=font)
        print(f"  {text[:30]:30s} at ({x:4d}, {y:4d})")
    
    # Save preview
    preview_path = CANVA_BACKGROUND_DIR / "preview_with_labels.png"
    preview.save(preview_path, 'PNG', quality=95)
    
    print(f"\n✓ Preview saved: {preview_path.name}")
    print(f"\nOpen this preview to see where text is positioned.")
    print("Adjust coordinates in canva_hybrid_generator.py to match your design.\n")
    
    return preview_path

if __name__ == "__main__":
    create_preview_with_labels()
