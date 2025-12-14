#!/usr/bin/env python3
"""
Analyze the Canva template to understand its structure
"""

from PIL import Image, ImageDraw
from pathlib import Path

template_path = Path(__file__).parent / "images" / "canva_backgrounds" / "CourtSide Template.png"

if not template_path.exists():
    print("✗ Template not found")
    exit(1)

img = Image.open(template_path)
width, height = img.size

print(f"\n{'='*60}")
print("Template Analysis")
print(f"{'='*60}\n")
print(f"Dimensions: {width} x {height}")
print(f"Mode: {img.mode}\n")

# Sample some pixels to understand the color scheme
print("Color Analysis:")
print("-" * 60)

# Sample corners and center
corners = [
    ("Top-left", (10, 10)),
    ("Top-right", (width-10, 10)),
    ("Bottom-left", (10, height-10)),
    ("Bottom-right", (width-10, height-10)),
    ("Center", (width//2, height//2)),
]

for label, (x, y) in corners:
    pixel = img.getpixel((x, y))
    print(f"{label:15s} ({x:4d}, {y:4d}): RGB{pixel}")

# Check if there's a photo area (top portion)
print(f"\nChecking for photo area (top portion):")
top_center = img.getpixel((width//2, height//4))
print(f"Top center (1/4 down): RGB{top_center}")

# Check card area (bottom portion)
bottom_center = img.getpixel((width//2, height*3//4))
print(f"Bottom center (3/4 down): RGB{bottom_center}")

print(f"\n{'='*60}")
print("Template loaded successfully!")
print("="*60)
