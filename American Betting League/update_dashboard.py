#!/usr/bin/env python3
"""
American Betting League Dashboard Updater
Automatically calculates biggest gainers from the last two days of data
"""

import csv
import sys
import os
from datetime import datetime
import glob

def read_csv_data(filepath):
    """Read CSV and return dict of bettor -> units"""
    data = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bettor = row['BETTOR']
            try:
                units = float(row['UNIT'])
                data[bettor] = units
            except (ValueError, KeyError):
                continue
    return data

def find_biggest_gainers(old_data, new_data, top_n=5):
    """Calculate unit changes and return top gainers"""
    changes = []
    for bettor in new_data:
        if bettor in old_data:
            change = new_data[bettor] - old_data[bettor]
            if change > 0:  # Only positive changes
                changes.append({
                    'bettor': bettor,
                    'change': change,
                    'old_units': old_data[bettor],
                    'new_units': new_data[bettor]
                })
    
    # Sort by change (descending)
    changes.sort(key=lambda x: x['change'], reverse=True)
    return changes[:top_n]

def generate_risers_html(gainers):
    """Generate HTML for the biggest risers section"""
    if not gainers:
        return '<p class="text-gray-400">No positive unit changes detected.</p>'
    
    html = '<div class="space-y-3">\n'
    
    for i, gainer in enumerate(gainers, 1):
        border_class = ' border-b border-gray-700 pb-2' if i < len(gainers) else ' pb-2'
        html += f'''<div class="{border_class}">
<p class="font-semibold text-white">{i}. {gainer['bettor']}</p>
<p class="text-sm text-green-400">+{gainer['change']:.2f} units</p>
<p class="text-xs text-gray-400">{gainer['old_units']:.2f} → {gainer['new_units']:.2f}</p>
</div>
'''
    
    html += '</div>'
    return html

def update_dashboard(dashboard_path, old_csv, new_csv, output_path=None):
    """Update the dashboard HTML with biggest gainers"""
    
    # Read CSV data
    print(f"Reading old data from: {old_csv}")
    old_data = read_csv_data(old_csv)
    
    print(f"Reading new data from: {new_csv}")
    new_data = read_csv_data(new_csv)
    
    # Find biggest gainers
    print("\nCalculating biggest gainers...")
    gainers = find_biggest_gainers(old_data, new_data)
    
    if gainers:
        print(f"\nTop {len(gainers)} Biggest Gainers:")
        print("=" * 60)
        for i, g in enumerate(gainers, 1):
            print(f"{i}. {g['bettor']}: +{g['change']:.2f} units ({g['old_units']:.2f} → {g['new_units']:.2f})")
    else:
        print("\nNo positive unit changes detected.")
    
    # Generate HTML
    risers_html = generate_risers_html(gainers)
    
    # Read dashboard template
    with open(dashboard_path, 'r') as f:
        html_content = f.read()
    
    # Find and replace the Biggest Risers section
    start_marker = '<div class="box border-green-600 shadow-2xl">\n<h2 class="text-2xl font-bold text-green-400 mb-4">📈 Biggest Risers</h2>'
    end_marker = '\n</div>\n\n<div class="box">'
    
    start_idx = html_content.find(start_marker)
    end_idx = html_content.find(end_marker, start_idx)
    
    if start_idx == -1 or end_idx == -1:
        print("\nError: Could not find Biggest Risers section in dashboard")
        return False
    
    # Replace the section
    new_section = f'''{start_marker}

{risers_html}

</div>'''
    
    updated_html = html_content[:start_idx] + new_section + html_content[end_idx:]
    
    # Write output
    if output_path is None:
        output_path = dashboard_path
    
    with open(output_path, 'w') as f:
        f.write(updated_html)
    
    print(f"\n✅ Dashboard updated successfully: {output_path}")
    return True

def find_latest_csv_files(directory, pattern="*.csv"):
    """Find the two most recent CSV files"""
    csv_files = glob.glob(os.path.join(directory, pattern))
    if len(csv_files) < 2:
        return None, None
    
    # Sort by modification time (newest first)
    csv_files.sort(key=os.path.getmtime, reverse=True)
    return csv_files[1], csv_files[0]  # Return (older, newer)

def main():
    print("American Betting League Dashboard Updater")
    print("=" * 60)
    
    # Check if specific files are provided
    if len(sys.argv) >= 4:
        dashboard_path = sys.argv[1]
        old_csv = sys.argv[2]
        new_csv = sys.argv[3]
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        # Auto-detect files
        print("\nAuto-detecting files...")
        
        # Find dashboard
        if os.path.exists('/mnt/user-data/uploads/dashboard.html'):
            dashboard_path = '/mnt/user-data/uploads/dashboard.html'
        else:
            print("Error: dashboard.html not found in uploads")
            return 1
        
        # Find two most recent CSV files
        old_csv, new_csv = find_latest_csv_files('/mnt/user-data/uploads')
        
        if old_csv is None or new_csv is None:
            print("Error: Could not find two CSV files in uploads directory")
            return 1
        
        output_path = '/mnt/user-data/outputs/dashboard.html'
    
    print(f"\nDashboard: {dashboard_path}")
    print(f"Old CSV: {old_csv}")
    print(f"New CSV: {new_csv}")
    print(f"Output: {output_path or dashboard_path}")
    
    # Update the dashboard
    success = update_dashboard(dashboard_path, old_csv, new_csv, output_path)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
