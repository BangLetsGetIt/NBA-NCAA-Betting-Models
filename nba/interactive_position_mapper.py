#!/usr/bin/env python3
"""
Interactive Position Mapper
Helps you identify exact text positions by comparing template with overlay
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json

CANVA_BACKGROUND_DIR = Path(__file__).parent / "images" / "canva_backgrounds"
template_path = CANVA_BACKGROUND_DIR / "CourtSide Template.png"
config_file = Path(__file__).parent / "text_position_config.json"

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

def create_comparison_image():
    """
    Create a side-by-side comparison:
    Left: Your template
    Right: Template with text overlays at current positions
    """
    if not template_path.exists():
        print(f"✗ Template not found: {template_path}")
        return None
    
    template = Image.open(template_path).convert('RGB')
    width, height = template.size
    
    # Create comparison image (side by side)
    comparison = Image.new('RGB', (width * 2 + 20, height), color=(0, 0, 0))
    
    # Left side: Original template
    comparison.paste(template, (0, 0))
    
    # Right side: Template with text overlays
    overlay = template.copy()
    draw = ImageDraw.Draw(overlay)
    
    # Load current positions
    positions = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            positions = config.get('text_positions', {})
    
    # Sample data for positioning
    sample_texts = {
        'rank_prop': '#1 • UNDER 22.5 PTS',
        'player_name': 'Paolo Banchero',
        'player_label': 'Player: Paolo Banchero',
        'matchup': 'Matchup: Orlando Magic vs New York Knicks',
        'game_time': '🕐 Game Time: 12/13 05:30 PM ET',
        'ai_rating': 'A.I. Rating: 4.9 ⭐⭐ (PREMIUM PLAY)',
        'season_avg': 'Season Avg: 20.2',
        'recent_avg': 'Recent Avg: 14.3',
        'clv': '✅ CLV: Opening: +100 → Latest: -104',
        'ai_score': 'A.I. Score: 10.00',
        'recommendation': '✅ UNDER 22.5 PTS',
        'ev_badge': '+37.3% EV',
        'sharp_tag': 'SHARP',
        'tracked_tag': '📊 TRACKED',
    }
    
    # Draw each text element
    for key, text in sample_texts.items():
        if key in positions:
            pos = positions[key]
            font = get_font(pos['font_size'], pos['bold'])
            
            # Draw with semi-transparent background for visibility
            bbox = draw.textbbox((pos['x'], pos['y']), text, font=font)
            # Draw background rectangle
            draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], 
                          fill=(0, 0, 0, 180))
            draw.text((pos['x'], pos['y']), text, 
                     fill=tuple(pos['color']), font=font)
    
    # Paste overlay on right side
    comparison.paste(overlay, (width + 20, 0))
    
    # Add labels
    label_draw = ImageDraw.Draw(comparison)
    font_label = get_font(24, True)
    label_draw.text((width // 2 - 100, 20), "YOUR TEMPLATE", 
                   fill=(255, 255, 255), font=font_label)
    label_draw.text((width + 20 + width // 2 - 150, 20), "WITH TEXT OVERLAYS", 
                   fill=(255, 255, 255), font=font_label)
    
    return comparison

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Creating Comparison Image")
    print("="*60 + "\n")
    
    comparison = create_comparison_image()
    
    if comparison:
        output_path = CANVA_BACKGROUND_DIR / "template_comparison.png"
        comparison.save(output_path, 'PNG', quality=95)
        
        print(f"✓ Comparison saved: {output_path.name}")
        print(f"\nOpen this image to see:")
        print("  Left: Your original Canva template")
        print("  Right: Template with text at current positions")
        print("\nAdjust coordinates in text_position_config.json to match your template.")
        print("="*60 + "\n")
    else:
        print("✗ Failed to create comparison")
