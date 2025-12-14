#!/usr/bin/env python3
"""
Helper script to extract template ID from Canva URL
"""

import sys
import re

def extract_template_id(url):
    """Extract template ID from Canva URL"""
    # Pattern: /design/XXXXX/ or /design/XXXXX/view
    pattern = r'/design/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_template_id.py <canva_url>")
        print("\nExample:")
        print("  python3 get_template_id.py 'https://www.canva.com/design/DAF123456789/view'")
        print("\nOr paste your Canva design URL:")
        url = input("\nPaste your Canva design URL: ").strip()
    else:
        url = sys.argv[1]
    
    template_id = extract_template_id(url)
    
    if template_id:
        print(f"\n{'='*60}")
        print(f"Template ID: {template_id}")
        print(f"{'='*60}\n")
        print("Add this to your .env file or use it directly:")
        print(f"CANVA_TEMPLATE_ID={template_id}\n")
    else:
        print("\n✗ Could not extract template ID from URL")
        print("\nMake sure your URL looks like:")
        print("  https://www.canva.com/design/DAFxxxxx/view")
        print("\nOr:")
        print("  https://www.canva.com/design/DAFxxxxx/")
