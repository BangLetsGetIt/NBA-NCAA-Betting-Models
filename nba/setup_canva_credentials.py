#!/usr/bin/env python3
"""
Helper script to add Canva credentials to .env file
"""

import os
from pathlib import Path

def setup_canva_credentials():
    """Add Canva credentials to .env file"""
    
    # Find .env file (check project root)
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    
    print(f"\n{'='*60}")
    print("Canva API Credentials Setup")
    print(f"{'='*60}\n")
    
    # Get credentials from user
    client_id = input("Enter your Canva Client ID: ").strip()
    client_secret = input("Enter your Canva Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("✗ Error: Both Client ID and Client Secret are required")
        return False
    
    # Read existing .env if it exists
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Check if credentials already exist
    if 'CANVA_CLIENT_ID' in env_content:
        print("\n⚠  Canva credentials already exist in .env file")
        overwrite = input("Do you want to overwrite them? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Cancelled.")
            return False
        
        # Remove old credentials
        lines = env_content.split('\n')
        lines = [line for line in lines if not line.startswith('CANVA_CLIENT_ID') and not line.startswith('CANVA_CLIENT_SECRET')]
        env_content = '\n'.join(lines)
    
    # Add new credentials
    if env_content and not env_content.endswith('\n'):
        env_content += '\n'
    
    env_content += f"\n# Canva API Credentials\n"
    env_content += f"CANVA_CLIENT_ID={client_id}\n"
    env_content += f"CANVA_CLIENT_SECRET={client_secret}\n"
    
    # Write to .env file
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"\n✓ Credentials saved to: {env_file}")
        print("✓ Canva API integration ready!")
        return True
    except Exception as e:
        print(f"\n✗ Error writing to .env file: {e}")
        return False

if __name__ == "__main__":
    setup_canva_credentials()
