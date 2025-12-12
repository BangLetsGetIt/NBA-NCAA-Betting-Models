#!/usr/bin/env python3
"""
ABL Dashboard Monitor
Checks Google Sheet for updates and automatically regenerates dashboard
"""

import pandas as pd
import ssl
import hashlib
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
BASE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1n_fAOu2dbT9DavwD7Kq12QJ8an7X4LBdP6o3-2_A2pA/export?format=csv'
CHECK_INTERVAL = 900  # Check every 15 minutes (900 seconds)
SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / '.abl_last_state'
LOG_FILE = SCRIPT_DIR / 'abl_monitor.log'
RECAP_SCRIPT = SCRIPT_DIR / 'abl_recap.py'

def log(message):
    """Write to log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}\n"
    print(log_message.strip())

    with open(LOG_FILE, 'a') as f:
        f.write(log_message)

def get_sheet_hash():
    """Fetch sheet data and return hash to detect changes"""
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        # Add timestamp to bypass cache
        url = f"{BASE_SHEET_URL}&_={int(datetime.now().timestamp())}"
        data = pd.read_csv(url)

        # Create hash of the data
        data_string = data.to_csv(index=False)
        data_hash = hashlib.md5(data_string.encode()).hexdigest()

        return data_hash, None
    except Exception as e:
        return None, str(e)

def get_last_hash():
    """Get the last known hash from state file"""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    return None

def save_hash(data_hash):
    """Save current hash to state file"""
    STATE_FILE.write_text(data_hash)

def run_dashboard_generation():
    """Run the dashboard generation script"""
    try:
        log("Running dashboard generation...")
        result = subprocess.run(
            ['python3', str(RECAP_SCRIPT)],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            log("✅ Dashboard generated successfully")
            # Log last few lines of output
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-5:]:
                log(f"  {line}")
            return True
        else:
            log(f"❌ Dashboard generation failed with code {result.returncode}")
            log(f"  Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log("❌ Dashboard generation timed out")
        return False
    except Exception as e:
        log(f"❌ Error running dashboard: {e}")
        return False

def monitor_once():
    """Single check cycle"""
    log("Checking for spreadsheet updates...")

    current_hash, error = get_sheet_hash()

    if error:
        log(f"⚠️  Error fetching spreadsheet: {error}")
        return False

    last_hash = get_last_hash()

    if last_hash is None:
        log("First run - initializing state and generating dashboard")
        save_hash(current_hash)
        run_dashboard_generation()
        return True

    if current_hash != last_hash:
        log("📊 Spreadsheet updated! Change detected.")
        save_hash(current_hash)
        run_dashboard_generation()
        return True
    else:
        log("No changes detected")
        return False

def monitor_continuous():
    """Run monitoring loop continuously"""
    log("="*60)
    log("ABL Dashboard Monitor Started")
    log(f"Checking every {CHECK_INTERVAL} seconds ({CHECK_INTERVAL/60:.0f} minutes)")
    log(f"Script directory: {SCRIPT_DIR}")
    log("="*60)

    while True:
        try:
            monitor_once()
        except KeyboardInterrupt:
            log("\n👋 Monitor stopped by user")
            break
        except Exception as e:
            log(f"❌ Unexpected error: {e}")

        # Wait for next check
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Single check mode (for testing or cron)
        monitor_once()
    else:
        # Continuous monitoring mode (for LaunchAgent)
        monitor_continuous()
