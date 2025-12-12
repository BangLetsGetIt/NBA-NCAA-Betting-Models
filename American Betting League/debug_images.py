#!/usr/bin/env python3
"""
Debug script to check images folder
Run this to see what's going on with your images
"""

import os

IMAGES_FOLDER = 'images'

print("=" * 60)
print("IMAGE FOLDER DEBUG")
print("=" * 60)

# Check if folder exists
if os.path.exists(IMAGES_FOLDER):
    print(f"✅ '{IMAGES_FOLDER}' folder EXISTS")
    print(f"   Location: {os.path.abspath(IMAGES_FOLDER)}")
else:
    print(f"❌ '{IMAGES_FOLDER}' folder DOES NOT EXIST")
    print(f"   Expected location: {os.path.abspath(IMAGES_FOLDER)}")
    print("\nCreate it with: mkdir images")
    exit(1)

print("\n" + "-" * 60)
print("CONTENTS OF IMAGES FOLDER:")
print("-" * 60)

# List everything in the folder
all_files = os.listdir(IMAGES_FOLDER)
if not all_files:
    print("❌ Folder is EMPTY")
    print("\nAdd your screenshots (.png, .jpg, .jpeg) to the images folder")
else:
    print(f"Found {len(all_files)} item(s):\n")
    for f in all_files:
        full_path = os.path.join(IMAGES_FOLDER, f)
        if os.path.isfile(full_path):
            file_ext = os.path.splitext(f)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                print(f"  ✅ {f} (valid image)")
            else:
                print(f"  ⚠️  {f} (NOT a valid image format - use .png, .jpg, or .jpeg)")
        else:
            print(f"  ⚠️  {f} (this is a folder, not a file)")

print("\n" + "-" * 60)
print("WHAT THE SCRIPT WILL USE:")
print("-" * 60)

# This is what the actual script does
images = [os.path.join(IMAGES_FOLDER, f) for f in os.listdir(IMAGES_FOLDER)
          if os.path.isfile(os.path.join(IMAGES_FOLDER, f)) 
          and f.lower().endswith(('.png', '.jpg', '.jpeg'))]

if images:
    print(f"✅ Found {len(images)} valid image(s):\n")
    for img in images:
        print(f"  - {img}")
else:
    print("❌ NO valid images found")
    print("\nMake sure your files:")
    print("  1. Are in the 'images' folder")
    print("  2. Have .png, .jpg, or .jpeg extensions")
    print("  3. Are actual files (not folders)")

print("\n" + "=" * 60)
