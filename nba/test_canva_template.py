#!/usr/bin/env python3
"""
Test Canva template access
"""

from canva_api_client import CanvaAPIClient
import requests
import urllib.parse
import json

template_id = "DAG2S09j-P4/ac8Jsl-ZR2XukcfgpfZmhA"

client = CanvaAPIClient()

if not client.is_authenticated():
    print("✗ Not authenticated")
    exit(1)

print(f"\nTesting template ID: {template_id}\n")

# Try different URL formats
from canva_api_client import CANVA_API_BASE

# Method 1: Direct access
encoded_id = urllib.parse.quote(template_id, safe='')
url1 = f"{CANVA_API_BASE}/designs/{encoded_id}"
print(f"Trying: {url1}")

headers = client.get_headers()
try:
    response = requests.get(url1, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Success!")
        data = response.json()
        print(f"\nDesign Info:")
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Method 2: Try creating from template
print(f"\n\nTrying to create design from template...")
try:
    result = client.create_design(template_id=template_id)
    if result:
        print("✓ Successfully created design from template!")
        print(json.dumps(result, indent=2))
    else:
        print("✗ Failed to create design")
except Exception as e:
    print(f"Error: {e}")
