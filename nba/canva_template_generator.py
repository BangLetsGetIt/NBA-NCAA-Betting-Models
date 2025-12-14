#!/usr/bin/env python3
"""
Canva Template Generator
Generates player prop cards using a Canva template
"""

import os
import json
import requests
from datetime import datetime
from canva_api_client import CanvaAPIClient
from pathlib import Path

# iCloud folder path
ICLOUD_BASE = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
if not os.path.exists(ICLOUD_BASE):
    ICLOUD_BASE = os.path.expanduser("~/iCloud Drive")

ICLOUD_CARDS_FOLDER = os.path.join(ICLOUD_BASE, "Player Prop Cards")
os.makedirs(ICLOUD_CARDS_FOLDER, exist_ok=True)

class CanvaTemplateGenerator:
    def __init__(self, template_id):
        self.client = CanvaAPIClient()
        self.template_id = template_id
        
        if not self.client.is_authenticated():
            raise ValueError("Canva API not authenticated. Run: python3 authorize_canva.py")
    
    def get_template_info(self):
        """Get information about the template"""
        from canva_api_client import CANVA_API_BASE
        import urllib.parse
        headers = self.client.get_headers()
        encoded_template_id = urllib.parse.quote(self.template_id, safe='')
        url = f"{CANVA_API_BASE}/designs/{encoded_template_id}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"✗ Error getting template info: {e}")
            return None
    
    def create_design_from_template(self, player_data):
        """
        Create a new design from template and populate with player data
        player_data: Dictionary with player information
        """
        # Create a copy of the template
        design_result = self.client.create_design(template_id=self.template_id)
        
        if not design_result:
            return None
        
        design_id = design_result.get('id')
        if not design_id:
            print("✗ Failed to create design from template")
            return None
        
        # Update design with player data
        # This will depend on your template structure
        updates = self.prepare_template_updates(player_data)
        
        if updates:
            updated = self.client.update_design(design_id, updates)
            if not updated:
                print("⚠  Design created but update failed")
        
        return design_id
    
    def prepare_template_updates(self, player_data):
        """
        Prepare updates for template based on player data
        This needs to match your template's element IDs
        """
        # TODO: Map player_data to template elements
        # You'll need to identify the element IDs in your template
        # Example structure:
        updates = {
            'elements': [
                # {
                #     'id': 'element_id_1',
                #     'content': player_data.get('player_name', '')
                # },
                # {
                #     'id': 'element_id_2', 
                #     'content': player_data.get('prop_text', '')
                # },
            ]
        }
        
        return updates
    
    def export_design(self, design_id, format='png'):
        """Export design as image"""
        result = self.client.export_design(design_id, format)
        return result
    
    def generate_card(self, player_data, save_to_icloud=True):
        """
        Generate a complete card: create design, update it, export it
        """
        print(f"  Creating design from template...")
        
        # Create design from template
        design_id = self.create_design_from_template(player_data)
        if not design_id:
            return None
        
        print(f"  Design created: {design_id}")
        print(f"  View/edit: {self.client.get_design_url(design_id)}")
        
        # Export design
        print(f"  Exporting as PNG...")
        export_result = self.export_design(design_id)
        
        if not export_result:
            print("  ⚠  Export failed, but design is available in Canva")
            return design_id
        
        # Download the exported image
        download_url = export_result.get('url')
        if download_url and save_to_icloud:
            return self.download_and_save(download_url, player_data)
        
        return design_id
    
    def download_and_save(self, download_url, player_data):
        """Download exported image and save to iCloud"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Save to iCloud
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

def get_template_elements(template_id):
    """Helper function to inspect template and get element IDs"""
    client = CanvaAPIClient()
    if not client.is_authenticated():
        print("✗ Not authenticated. Run: python3 authorize_canva.py")
        return None
    
    import requests
    from canva_api_client import CANVA_API_BASE
    import urllib.parse
    headers = client.get_headers()
    # URL encode the template ID to handle special characters
    encoded_template_id = urllib.parse.quote(template_id, safe='')
    url = f"{CANVA_API_BASE}/designs/{encoded_template_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        design_data = response.json()
        
        print("\nTemplate Elements:")
        print("="*60)
        # Print structure to help identify elements
        print(json.dumps(design_data, indent=2))
        return design_data
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 canva_template_generator.py <template_id>")
        print("\nTo find your template ID:")
        print("1. Open your design in Canva")
        print("2. Look at the URL: https://www.canva.com/design/XXXXX/...")
        print("3. The XXXXX part is your template ID")
        sys.exit(1)
    
    template_id = sys.argv[1]
    
    if sys.argv[1] == 'inspect':
        # Inspect template structure
        if len(sys.argv) < 3:
            print("Usage: python3 canva_template_generator.py inspect <template_id>")
            sys.exit(1)
        get_template_elements(sys.argv[2])
    else:
        # Test generation
        generator = CanvaTemplateGenerator(template_id)
        
        # Sample player data
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
