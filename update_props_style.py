#!/usr/bin/env python3
"""
Script to update all props models to match NBA points props style
Updates colors, rgba values, and spacing to match the reference style
"""

import os
import re

# Files to update
FILES_TO_UPDATE = [
    'nba/nba_3pt_props_model.py',
    'nba/nba_assists_props_model.py',
    'nba/nba_rebounds_props_model.py',
    'nfl/nfl_passing_yards_props_model.py',
    'nfl/nfl_receptions_props_model.py',
    'nfl/nfl_rushing_yards_props_model.py',
]

# Replacement patterns
REPLACEMENTS = [
    # Color codes - must be done in order to avoid double replacements
    (r'#4ade80', '#10b981'),  # Green
    (r'#f87171', '#ef4444'),  # Red
    (r'#fbbf24', '#f59e0b'),  # Yellow/Orange
    
    # RGBA colors - green (for EV badges, pick-yes, etc.)
    (r'rgba\(74, 222, 128, 0\.2\)', 'rgba(16, 185, 129, 0.15)'),
    (r'rgba\(74, 222, 128, 0\.15\)', 'rgba(16, 185, 129, 0.15)'),
    (r'rgba\(74, 222, 128, 0\.12\)', 'rgba(16, 185, 129, 0.15)'),
    (r'rgba\(74, 222, 128, 0\.10\)', 'rgba(16, 185, 129, 0.12)'),
    
    # RGBA colors - red (for pick-no)
    (r'rgba\(248, 113, 113, 0\.2\)', 'rgba(239, 68, 68, 0.15)'),
    (r'rgba\(248, 113, 113, 0\.15\)', 'rgba(239, 68, 68, 0.15)'),
    
    # RGBA colors - yellow/orange (for AI rating standard/marginal)
    (r'rgba\(251, 191, 36, 0\.10\)', 'rgba(245, 158, 11, 0.12)'),
    (r'rgba\(251, 191, 36, 0\.08\)', 'rgba(245, 158, 11, 0.08)'),
    
    # Spacing - tracking section first grid
    (r'gap: 1rem; margin-bottom: 1\.5rem;', 'gap: 1.5rem; margin-bottom: 2rem;'),
    
    # Spacing - tracking section second grid
    (r'gap: 1rem; margin-top: 1\.5rem; padding-top: 1\.5rem;', 'gap: 1.5rem; margin-top: 2rem; padding-top: 2rem;'),
    
    # Spacing - card sections (OVER/UNDER headers) - need to be careful with context
    (r'margin-bottom: 1\.5rem; color: #10b981', 'margin-bottom: 2rem; color: #10b981'),
    (r'margin-bottom: 1\.5rem; color: #ef4444', 'margin-bottom: 2rem; color: #ef4444'),
    
    # Spacing - card grid gaps (only in card sections, not tracking)
    (r'gap: 1\.5rem;">\s*"""', 'gap: 2rem;">"""'),
    (r'gap: 1\.5rem;">\s*$', 'gap: 2rem;">'),
    
    # Body padding
    (r'padding: 1\.5rem;', 'padding: 2rem;'),
    
    # Card styling
    (r'border-radius: 1\.25rem;', 'border-radius: 1.5rem;'),
    (r'padding: 2rem;.*?margin-bottom: 1\.5rem;', 'padding: 2.5rem;\n            margin-bottom: 2rem;'),
]

def update_file(filepath):
    """Update a single file with style replacements"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # Apply all replacements
        for pattern, replacement in REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                updated = True
        
        # Additional specific replacements for tracked badges
        # Tracked badge should always use blue (matching points props style)
        # Pattern: background: rgba(XX, XX, XX, 0.X); color: #XXXXXX; ... TRACKED
        content = re.sub(
            r"background: rgba\(74, 222, 128, 0\.2\); color: #4ade80;.*?TRACKED",
            'background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED',
            content
        )
        content = re.sub(
            r"background: rgba\(16, 185, 129, 0\.15\); color: #10b981;.*?TRACKED",
            'background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED',
            content
        )
        content = re.sub(
            r"background: rgba\(248, 113, 113, 0\.2\); color: #f87171;.*?TRACKED",
            'background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED',
            content
        )
        content = re.sub(
            r"background: rgba\(239, 68, 68, 0\.15\); color: #ef4444;.*?TRACKED",
            'background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED',
            content
        )
        
        # Fix the tracked badge pattern more precisely
        tracked_pattern_old = r"<span style=\"display: inline-block; padding: 0\.25rem 0\.5rem; background: rgba\([^)]+\); color: #[^;]+; border-radius: 0\.5rem; font-size: 0\.75rem; font-weight: 600; margin-left: 0\.5rem;\">📊 TRACKED</span>"
        tracked_pattern_new = '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(59, 130, 246, 0.15); color: #3b82f6; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED</span>'
        content = re.sub(tracked_pattern_old, tracked_pattern_new, content)
        
        # Update CSS for AI rating classes
        # Premium and strong should use new green
        content = re.sub(
            r'\.ai-rating-premium \{\s+background: rgba\(74, 222, 128, 0\.12\);',
            '.ai-rating-premium {\n            background: rgba(16, 185, 129, 0.15);',
            content
        )
        content = re.sub(
            r'\.ai-rating-strong \{\s+background: rgba\(74, 222, 128, 0\.10\);',
            '.ai-rating-strong {\n            background: rgba(16, 185, 129, 0.12);',
            content
        )
        # Standard and marginal should use new yellow/orange
        content = re.sub(
            r'\.ai-rating-standard \{\s+background: rgba\(251, 191, 36, 0\.10\);',
            '.ai-rating-standard {\n            background: rgba(245, 158, 11, 0.12);',
            content
        )
        content = re.sub(
            r'\.ai-rating-marginal \{\s+background: rgba\(251, 191, 36, 0\.08\);',
            '.ai-rating-marginal {\n            background: rgba(245, 158, 11, 0.08);',
            content
        )
        
        # Update confidence-pct color in CSS (there are duplicate definitions)
        content = re.sub(
            r'\.confidence-pct \{\s+font-weight: 700;\s+color: #4ade80;',
            '.confidence-pct {\n            font-weight: 700;\n            color: #10b981;',
            content
        )
        
        # Update confidence-fill background in CSS
        content = re.sub(
            r'\.confidence-fill \{\s+height: 100%;\s+background: #4ade80;',
            '.confidence-fill {\n            height: 100%;\n            background: linear-gradient(90deg, #10b981 0%, #059669 100%);',
            content
        )
        
        # Update pick-yes and pick-no CSS
        content = re.sub(
            r'\.pick-yes \{\{ background: rgba\(74, 222, 128, 0\.15\); color: #4ade80; border: 2px solid #4ade80; \}\}',
            '.pick-yes { background: rgba(16, 185, 129, 0.15); color: #10b981; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2); }',
            content
        )
        content = re.sub(
            r'\.pick-no \{\{ background: rgba\(248, 113, 113, 0\.15\); color: #f87171; border: 2px solid #f87171; \}\}',
            '.pick-no { background: rgba(239, 68, 68, 0.15); color: #ef4444; box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2); }',
            content
        )
        
        # Update badge CSS
        content = re.sub(
            r'background: rgba\(74, 222, 128, 0\.2\);',
            'background: rgba(59, 130, 246, 0.15);',
            content
        )
        
        # Update card styling to match points props
        # Add backdrop-filter and border if missing
        if 'backdrop-filter: blur(10px)' not in content or 'border: 1px solid rgba(255, 255, 255, 0.1)' not in content:
            content = re.sub(
                r'\.card \{\s+background: #1a1a1a;',
                '.card {\n            background: #1a1a1a;\n            backdrop-filter: blur(10px);\n            -webkit-backdrop-filter: blur(10px);\n            border: 1px solid rgba(255, 255, 255, 0.1);',
                content
            )
        
        # Update bet-box styling
        content = re.sub(
            r'border: 1px solid rgba\(255, 255, 255, 0\.08\);',
            'border: 1px solid rgba(255, 255, 255, 0.08);',
            content
        )
        
        # Ensure pick styling has box-shadow (not border)
        content = re.sub(
            r'\.pick-yes.*?border: 2px solid #10b981;',
            '.pick-yes { background: rgba(16, 185, 129, 0.15); color: #10b981; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2); }',
            content
        )
        content = re.sub(
            r'\.pick-no.*?border: 2px solid #ef4444;',
            '.pick-no { background: rgba(239, 68, 68, 0.15); color: #ef4444; box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2); }',
            content
        )
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {filepath}")
            return True
        else:
            print(f"ℹ️  No changes needed: {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")
        return False

def main():
    """Main execution"""
    print("=" * 80)
    print("Updating Props Models to Match NBA Points Props Style")
    print("=" * 80)
    print()
    
    updated_count = 0
    for filepath in FILES_TO_UPDATE:
        if update_file(filepath):
            updated_count += 1
    
    print()
    print("=" * 80)
    print(f"✅ Updated {updated_count} out of {len(FILES_TO_UPDATE)} files")
    print("=" * 80)

if __name__ == "__main__":
    main()
