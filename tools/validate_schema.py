#!/usr/bin/env python3
"""Validate tracking JSON files against a minimal schema and produce a CSV summary.
Outputs:
 - tools/reports/schema_validation.csv
 - tools/reports/schema_validation_summary.md
"""
import json
import glob
import os
from pathlib import Path
import csv

WORKDIR = Path(__file__).resolve().parents[1]
OUT_DIR = WORKDIR / "tools" / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRACKING_FILES = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))

required_sets = [
    ("pick_id_or_id", ["pick_id", "id"]),
    ("game_time_or_game_date", ["game_time", "game_date"]),
    ("odds_or_opening_odds", ["opening_odds", "odds"]),
    ("profit_loss_or_profit", ["profit_loss", "profit"]),
    ("status_or_result", ["status", "result"]),
]

recommended = ["prob", "latest_odds", "bet_size_units", "updated_at", "tracked_at"]


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


def check_file(path):
    with open(path, 'r') as f:
        data = json.load(f)
    picks = normalize(data)
    total = len(picks)
    picks_with_all_required = 0
    missing_required_summary = {}
    picks_missing_prob = 0
    invalid_type_examples = []

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

        # Type checks
        # odds should be int-like
        for odds_key in ['opening_odds', 'odds', 'latest_odds']:
            if odds_key in p and p[odds_key] is not None:
                v = p[odds_key]
                if not isinstance(v, (int, float)):
                    invalid_type_examples.append((odds_key, type(v).__name__))
                    break
        # profit should be numeric
        for prof_key in ['profit_loss', 'profit']:
            if prof_key in p and p[prof_key] is not None:
                v = p[prof_key]
                if not isinstance(v, (int, float)):
                    invalid_type_examples.append((prof_key, type(v).__name__))
                    break

    notes = []
    if total == 0:
        notes.append('no_picks')
    if missing_required_summary:
        notes.append('missing_required')

    return {
        'file': path,
        'total_picks': total,
        'picks_with_all_required': picks_with_all_required,
        'missing_required_summary': json.dumps(missing_required_summary),
        'picks_missing_prob': picks_missing_prob,
        'invalid_type_examples': json.dumps(invalid_type_examples[:5]),
        'notes': ';'.join(notes)
    }


def main():
    rows = []
    for t in TRACKING_FILES:
        try:
            rows.append(check_file(t))
        except Exception as e:
            rows.append({'file': t, 'total_picks': 'ERROR', 'picks_with_all_required': 0, 'missing_required_summary': '', 'picks_missing_prob': 0, 'invalid_type_examples': str(e), 'notes': 'error'})

    csv_out = OUT_DIR / 'schema_validation.csv'
    with open(csv_out, 'w', newline='') as cf:
        writer = csv.DictWriter(cf, fieldnames=['file','total_picks','picks_with_all_required','missing_required_summary','picks_missing_prob','invalid_type_examples','notes'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Summary MD
    md = []
    md.append('# Schema Validation Summary')
    md.append('Processed files: %d' % len(rows))
    md.append('')
    # Top missing fields overall
    agg_missing = {}
    for r in rows:
        try:
            m = json.loads(r['missing_required_summary']) if r['missing_required_summary'] else {}
            for k,v in m.items():
                agg_missing[k] = agg_missing.get(k,0) + v
        except Exception:
            pass

    if agg_missing:
        md.append('## Missing required fields (by count)')
        for k,v in sorted(agg_missing.items(), key=lambda x:-x[1]):
            md.append(f'- {k}: {v}')
    else:
        md.append('No missing required fields detected in picks.')

    md_out = OUT_DIR / 'schema_validation_summary.md'
    with open(md_out, 'w') as f:
        f.write('\n'.join(md))

    print('Wrote', csv_out, 'and', md_out)


if __name__ == '__main__':
    main()
