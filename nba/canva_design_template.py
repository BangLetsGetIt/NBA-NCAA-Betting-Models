#!/usr/bin/env python3
"""
Canva Design Template Generator
Uses your created design as a template to generate player prop cards
"""

import os
import json
import requests
import urllib.parse
from datetime import datetime
from canva_api_client import CanvaAPIClient
from pathlib import Path

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

class CanvaDesignTemplate:
    def __init__(self, design_id):
        self.client = CanvaAPIClient()
        self.design_id = design_id
        
        if not self.client.is_authenticated():
            raise ValueError("Canva API not authenticated. Run: python3 authorize_canva.py")
    
    def get_design_info(self):
        """Get information about the design"""
        from canva_api_client import CANVA_API_BASE
        headers = self.client.get_headers()
        
        # Try to get design info
        encoded_id = urllib.parse.quote(self.design_id, safe='')
        url = f"{CANVA_API_BASE}/designs/{encoded_id}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠  Could not access design directly: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"✗ Error getting design info: {e}")
            return None
    
    def clone_design(self):
        """
        Clone/copy the design to create a new one
        This creates a copy we can modify
        """
        from canva_api_client import CANVA_API_BASE
        headers = self.client.get_headers()
        url = f"{CANVA_API_BASE}/designs"
        
        # Try to create a new design based on the existing one
        # Note: Canva API might require different approach
        payload = {
            'title': 'Player Prop Card',
            # Some APIs allow 'source_design_id' or 'clone_from'
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            else:
                print(f"⚠  Clone attempt: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return None
        except Exception as e:
            print(f"✗ Error cloning design: {e}")
            return None
    
    def update_design_elements(self, design_id, player_data):
        """
        Update text/elements in the design
        This requires knowing the element IDs in your design
        """
        # First, we need to get the design structure to find element IDs
        from canva_api_client import CANVA_API_BASE
        headers = self.client.get_headers()
        encoded_id = urllib.parse.quote(design_id, safe='')
        url = f"{CANVA_API_BASE}/designs/{encoded_id}"
        
        try:
            # Get current design
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"✗ Could not get design: {response.status_code}")
                return False
            
            design_data = response.json()
            
            # TODO: Parse design_data to find text elements
            # Then update them with player_data
            # This depends on Canva's design structure format
            
            # For now, try a simple update
            updates = {
                # 'elements': [...] # Need to map player_data to element IDs
            }
            
            update_url = f"{CANVA_API_BASE}/designs/{encoded_id}"
            update_response = requests.patch(update_url, headers=headers, json=updates)
            
            if update_response.status_code == 200:
                return True
            else:
                print(f"⚠  Update response: {update_response.status_code}")
                print(f"   {update_response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"✗ Error updating design: {e}")
            return False
    
    def export_design(self, design_id, format='png'):
        """Export design as image"""
        result = self.client.export_design(design_id, format)
        return result
    
    def generate_card(self, player_data):
        """
        Generate a card by cloning the design and updating it
        """
        print(f"\nGenerating card for {player_data.get('player_name', 'Unknown')}...")
        
        # Step 1: Try to clone the design
        print("  Step 1: Cloning design...")
        cloned = self.clone_design()
        
        if not cloned:
            print("  ⚠  Could not clone design via API")
            print("  Alternative: We can update the original design directly")
            print("  Or use PIL/Pillow approach for full control")
            return None
        
        new_design_id = cloned.get('id')
        print(f"  ✓ Design cloned: {new_design_id}")
        
        # Step 2: Update with player data
        print("  Step 2: Updating with player data...")
        # This requires knowing your design's element structure
        updated = self.update_design_elements(new_design_id, player_data)
        
        if updated:
            print("  ✓ Design updated")
        else:
            print("  ⚠  Design created but update may have failed")
            print(f"  You can manually edit: {self.client.get_design_url(new_design_id)}")
        
        # Step 3: Export
        print("  Step 3: Exporting...")
        export_result = self.export_design(new_design_id)
        
        if export_result:
            download_url = export_result.get('url')
            if download_url:
                return self.download_and_save(download_url, player_data)
        
        return new_design_id
    
    def download_and_save(self, download_url, player_data):
        """Download exported image and save to iCloud"""
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            player_name = player_data.get('player_name', 'Unknown').replace(' ', '_')
            filename = f"{player_name}_Canva_{timestamp}.png"
            filepath = os.path.join(ICLOUD_CARDS_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✓ Saved: {filename}")
            return filepath
            
        except Exception as e:
            print(f"  ✗ Error downloading: {e}")
            return None

def inspect_design(design_id):
    """Inspect design structure to find element IDs"""
    client = CanvaAPIClient()
    if not client.is_authenticated():
        print("✗ Not authenticated. Run: python3 authorize_canva.py")
        return None
    
    from canva_api_client import CANVA_API_BASE
    headers = client.get_headers()
    encoded_id = urllib.parse.quote(design_id, safe='')
    url = f"{CANVA_API_BASE}/designs/{encoded_id}"
    
    print(f"\nInspecting design: {design_id}\n")
    print("="*60)
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            design_data = response.json()
            print("Design Structure:")
            print(json.dumps(design_data, indent=2))
            return design_data
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            print("\n⚠  Note: The Canva Connect API may have limitations")
            print("   on accessing designs directly.")
            print("\n   Alternative options:")
            print("   1. Use PIL/Pillow for full programmatic control")
            print("   2. Export your design as an image and use as background")
            print("   3. Check Canva API docs for design access permissions")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    design_id = "DAG2S09j-P4/ac8Jsl-ZR2XukcfgpfZmhA"
    
    if len(sys.argv) > 1 and sys.argv[1] == 'inspect':
        inspect_design(design_id)
    else:
        # Test with sample data
        generator = CanvaDesignTemplate(design_id)
        
        test_data = {
            'player_name': 'Stephen Curry',
            'prop_text': 'OVER 24.5 PTS',
            'team_name': 'Golden State Warriors',
            'opponent': 'Minnesota Timberwolves',
            'ai_rating': 4.7,
            'season_avg': 28.5,
            'recent_avg': 30.2,
        }
        
        generator.generate_card(test_data)
