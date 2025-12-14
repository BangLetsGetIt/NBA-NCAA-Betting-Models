#!/usr/bin/env python3
"""
Generate Player Prop Cards using Canva API
Creates cards programmatically using Canva's design API
"""

import os
import json
from datetime import datetime
from canva_api_client import CanvaAPIClient
from card_design import create_player_card  # Fallback to PIL if Canva fails

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

def create_card_via_canva(player_data, player_photo=None):
    """
    Create player prop card using Canva API
    Falls back to PIL if Canva API is unavailable
    """
    client = CanvaAPIClient()
    
    # Test connection first
    if not client.test_connection():
        print("⚠  Canva API unavailable, falling back to PIL/Pillow")
        from player_photo_service import get_player_photo
        if not player_photo:
            player_photo = get_player_photo(player_data.get('player_name', ''))
        return create_player_card(player_data, player_photo)
    
    # TODO: Implement Canva template-based card creation
    # For now, we'll use the PIL approach as Canva API for creating designs
    # from scratch requires more setup (templates, etc.)
    
    print("ℹ  Canva API connected, but using PIL for card generation")
    print("   (Canva template integration coming soon)")
    
    from player_photo_service import get_player_photo
    if not player_photo:
        player_photo = get_player_photo(player_data.get('player_name', ''))
    return create_player_card(player_data, player_photo)

def generate_cards_from_plays(plays, use_canva=False):
    """
    Generate cards for a list of plays
    plays: List of play dictionaries from props models
    use_canva: Whether to use Canva API (if available)
    """
    print(f"\n{'='*60}")
    print("Generating Player Prop Cards")
    print(f"{'='*60}\n")
    print(f"Output folder: {ICLOUD_CARDS_FOLDER}\n")
    
    generated = []
    
    for i, play in enumerate(plays, 1):
        player_name = play.get('player', play.get('player_name', 'Unknown'))
        print(f"[{i}/{len(plays)}] Creating card for {player_name}...")
        
        # Prepare card data
        card_data = {
            'rank': play.get('rank', i),
            'player_name': player_name,
            'team_name': play.get('team', play.get('team_name', '')),
            'opponent': play.get('opponent', ''),
            'prop_text': play.get('prop', play.get('prop_text', '')),
            'game_time': play.get('game_time', 'TBD'),
            'ai_rating': play.get('ai_rating', 2.3),
            'rating_label': play.get('rating_label', 'STANDARD PLAY'),
            'season_avg': play.get('season_avg', 0),
            'recent_avg': play.get('recent_avg', 0),
            'clv_data': play.get('clv_data'),
            'ai_score': play.get('ai_score', 0),
            'ev': play.get('ev'),
            'is_sharp': play.get('is_sharp', False),
            'is_tracked': play.get('is_tracked', False),
        }
        
        # Create card
        if use_canva:
            card_img = create_card_via_canva(card_data)
        else:
            from player_photo_service import get_player_photo
            player_photo = get_player_photo(player_name)
            card_img = create_player_card(card_data, player_photo)
        
        # Save to iCloud
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = player_name.replace(' ', '_').replace("'", "")
        prop_type = play.get('prop_type', 'Prop')
        filename = f"{safe_name}_{prop_type}_{timestamp}.png"
        filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
        card_img.save(filepath, 'PNG', quality=95)
        
        generated.append(filepath)
        print(f"  ✓ Saved: {filename}\n")
    
    print(f"{'='*60}")
    print(f"✓ Generated {len(generated)} cards")
    print(f"  Location: {ICLOUD_CARDS_FOLDER}")
    print(f"{'='*60}\n")
    
    return generated

if __name__ == "__main__":
    # Test with sample data
    from test_player_cards import create_test_cards
    create_test_cards()
