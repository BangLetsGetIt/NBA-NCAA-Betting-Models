#!/usr/bin/env python3
"""
Hybrid Canva + PIL Card Generator
Uses your Canva design as a background image, overlays data with PIL
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

# Local folder for Canva background
CANVA_BACKGROUND_DIR = Path(__file__).parent / "images" / "canva_backgrounds"
CANVA_BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)

def find_background_image():
    """Find the Canva background image"""
    # Try common names
    possible_names = [
        "CourtSide Template.png",
        "card_template.png",
        "template.png",
        "background.png"
    ]
    
    for name in possible_names:
        path = CANVA_BACKGROUND_DIR / name
        if path.exists():
            return str(path)
    
    # Try any PNG/JPG in the folder
    bg_files = list(CANVA_BACKGROUND_DIR.glob("*.png")) + list(CANVA_BACKGROUND_DIR.glob("*.jpg"))
    if bg_files:
        return str(bg_files[0])
    
    return None

class CanvaHybridGenerator:
    def __init__(self, background_image_path=None):
        """
        Initialize with Canva design as background
        background_image_path: Path to exported Canva design image
        """
        if background_image_path and os.path.exists(background_image_path):
            self.background_path = background_image_path
        else:
            # Auto-find background
            self.background_path = find_background_image()
            if not self.background_path:
                print("⚠  No background image found. Using solid color background.")
    
    def load_background(self):
        """Load the Canva design as background"""
        if self.background_path:
            try:
                return Image.open(self.background_path).convert('RGB')
            except Exception as e:
                print(f"⚠  Could not load background: {e}")
                return None
        return None
    
    def create_card(self, player_data):
        """
        Create card using Canva background + PIL overlays
        """
        # Load background
        bg = self.load_background()
        
        if bg:
            # Use Canva design as background
            card = bg.copy()
            card_width, card_height = card.size
        else:
            # Fallback: Create solid background
            card_width, card_height = 1080, 1920
            card = Image.new('RGB', (card_width, card_height), color=(26, 35, 50))
        
        draw = ImageDraw.Draw(card)
        
        # Overlay player data
        # You'll need to adjust coordinates based on your Canva design layout
        self.overlay_text(draw, player_data, card_width, card_height)
        
        return card
    
    def load_text_config(self):
        """Load text position configuration"""
        config_file = Path(__file__).parent / "text_position_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return None
    
    def overlay_text(self, draw, player_data, width, height):
        """Overlay text on the card based on your Canva design layout"""
        import json
        
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
        
        # Load position config
        config = self.load_text_config()
        if not config:
            print("⚠  No text position config found. Using defaults.")
            return
        
        positions = config.get('text_positions', {})
        
        # Format game time
        def format_game_time(game_time_str):
            try:
                if not game_time_str or game_time_str == 'TBD':
                    return 'TBD'
                from datetime import datetime as dt
                import pytz
                dt_obj = dt.fromisoformat(game_time_str.replace('Z', '+00:00'))
                et_tz = pytz.timezone('US/Eastern')
                dt_et = dt_obj.astimezone(et_tz)
                return dt_et.strftime('%m/%d %I:%M %p ET')
            except:
                return game_time_str if game_time_str else 'TBD'
        
        # Get rating label
        def get_rating_label(ai_rating):
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
        
        # Draw each text element
        rank = player_data.get('rank', 1)
        prop_text = player_data.get('prop_text', '')
        player_name = player_data.get('player_name', '')
        team_name = player_data.get('team_name', '')
        opponent = player_data.get('opponent', '')
        game_time = format_game_time(player_data.get('game_time', ''))
        ai_rating = player_data.get('ai_rating', 2.3)
        rating_label = get_rating_label(ai_rating)
        season_avg = player_data.get('season_avg', 0)
        recent_avg = player_data.get('recent_avg', 0)
        clv_data = player_data.get('clv_data')
        ai_score = player_data.get('ai_score', 0)
        ev = player_data.get('ev')
        is_sharp = player_data.get('is_sharp', False)
        is_tracked = player_data.get('is_tracked', False)
        
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

def setup_canva_background():
    """Instructions for setting up Canva background"""
    print("\n" + "="*60)
    print("Setting Up Canva Background")
    print("="*60 + "\n")
    print("To use your Canva design as a background:")
    print("\n1. Open your design in Canva")
    print("2. Click 'Share' → 'Download'")
    print("3. Choose 'PNG' format")
    print("4. Save the image to:")
    print(f"   {CANVA_BACKGROUND_DIR}/card_template.png")
    print("\n5. Then run the generator to create cards!")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        setup_canva_background()
    else:
        # Test generation
        generator = CanvaHybridGenerator()
        
        test_data = {
            'player_name': 'Stephen Curry',
            'prop_text': 'OVER 24.5 PTS',
            'team_name': 'Golden State Warriors',
            'opponent': 'Minnesota Timberwolves',
            'ai_rating': 4.7,
            'season_avg': 28.5,
            'recent_avg': 30.2,
        }
        
        print("Generating test card...")
        card = generator.create_card(test_data)
        
        # Save test card
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_card_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card.save(filepath, 'PNG', quality=95)
        print(f"\n✓ Test card saved: {filename}")
        print(f"  Location: {ICLOUD_CARDS_FOLDER}\n")
