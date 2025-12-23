#!/usr/bin/env python3
"""Compare schema validation results between original tracking files and cleaned fixed copies.
Writes `tools/reports/schema_validation_comparison.csv` and a short markdown summary.
"""
import json
import glob
import os
from pathlib import Path
import csv

WORKDIR = Path(__file__).resolve().parents[1]
OUT_DIR = WORKDIR / 'tools' / 'reports'
OUT_DIR.mkdir(parents=True, exist_ok=True)

ORIG_FILES = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))
FIXED_DIR = OUT_DIR / 'fixed'

required_sets = [
    ("pick_id_or_id", ["pick_id", "id"]),
    ("game_time_or_game_date", ["game_time", "game_date"]),
    ("odds_or_opening_odds", ["opening_odds", "odds"]),
    ("profit_loss_or_profit", ["profit_loss", "profit"]),
    ("status_or_result", ["status", "result"]),
]


def normalize(data):
    if isinstance(data, dict):
        if 'picks' in data and isinstance(data['picks'], list):
            picks = data['picks']
        else:
            picks = []
            for v in data.values():
                if isinstance(v, list):
                    picks = v
                    break
            if not picks:
                picks = [data]
    elif isinstance(data, list):
        picks = data
    else:
        picks = []
    return [p for p in picks if isinstance(p, dict)]


def check_data(picks):
    total = len(picks)
    picks_with_all_required = 0
    missing_required_summary = {}
    picks_missing_prob = 0

    for p in picks:
        missing = []
        for keyname, options in required_sets:
            if not any(k in p and p[k] is not None for k in options):
                missing.append(keyname)
                missing_required_summary.setdefault(keyname, 0)
                missing_required_summary[keyname] += 1
        if not missing:
            picks_with_all_required += 1
        if 'prob' not in p and 'win_prob' not in p and 'proj_prob' not in p:
            picks_missing_prob += 1

    return {
        'total_picks': total,
        'picks_with_all_required': picks_with_all_required,
        'missing_required_summary': missing_required_summary,
        'picks_missing_prob': picks_missing_prob
    }


def find_fixed_for(orig_path):
    rel = Path(orig_path).relative_to(WORKDIR)
    fixed_name = str(rel).replace(os.sep, '__') + '.fixed.json'
    fixed_path = FIXED_DIR / fixed_name
    return fixed_path if fixed_path.exists() else None


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def main():
    rows = []
    for orig in ORIG_FILES:
        try:
            od = load_json(orig)
            orig_picks = normalize(od)
            orig_stats = check_data(orig_picks)
        except Exception:
            orig_stats = {'total_picks': 'ERR', 'picks_with_all_required': 0, 'missing_required_summary': {}, 'picks_missing_prob': 0}

        fixed_path = find_fixed_for(orig)
        if fixed_path:
            try:
                fd = load_json(fixed_path)
                fixed_picks = normalize(fd)
                fixed_stats = check_data(fixed_picks)
            except Exception:
                fixed_stats = {'total_picks': 'ERR', 'picks_with_all_required': 0, 'missing_required_summary': {}, 'picks_missing_prob': 0}
        else:
            fixed_stats = None

        rows.append((orig, fixed_path, orig_stats, fixed_stats))

    csv_out = OUT_DIR / 'schema_validation_comparison.csv'
    with open(csv_out, 'w', newline='') as cf:
        writer = csv.writer(cf)
        writer.writerow(['file','orig_total','orig_with_required','fixed_total','fixed_with_required','orig_missing','fixed_missing','notes'])
        for orig, fixed, o, f in rows:
            orig_missing = json_safe(o.get('missing_required_summary'))
            fixed_missing = json_safe(f.get('missing_required_summary')) if f else ''
            writer.writerow([orig, o.get('total_picks'), o.get('picks_with_all_required'), f.get('total_picks') if f else '', f.get('picks_with_all_required') if f else '', orig_missing, fixed_missing, '' ] )

    md = ['# Schema Validation Comparison','']
    md.append(f'Generated comparison for {len(rows)} files.')
    md_out = OUT_DIR / 'schema_validation_comparison.md'
    with open(md_out, 'w') as f:
        f.write('\n'.join(md))

    print('Wrote', csv_out, 'and', md_out)


def json_safe(d):
    try:
        import json
        return json.dumps(d)
    except Exception:
        return str(d)


if __name__ == '__main__':
    main()
