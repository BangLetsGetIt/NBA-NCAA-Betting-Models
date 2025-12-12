#!/usr/bin/env python3
"""
Simple script to update the unified dashboard
Call this from any of your models after they finish running
"""

import subprocess
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def update_dashboard():
    """Run the unified dashboard generator"""
    try:
        result = subprocess.run(
            ['python3', 'unified_dashboard_interactive.py'],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✓ Dashboard updated successfully")
            return True
        else:
            print(f"✗ Dashboard update failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error updating dashboard: {e}")
        return False

if __name__ == "__main__":
    update_dashboard()
