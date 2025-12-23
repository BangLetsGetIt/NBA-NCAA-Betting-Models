#!/usr/bin/env python3
"""Create non-destructive, cleaned copies of tracking JSON files.
Writes cleaned files to `tools/reports/fixed/<relative_path>.fixed.json`.
Does NOT modify original files.

Fixes applied (conservative):
- Parse `odds_str` like '+105' or '-110' into `odds` int when `odds` missing.
- Convert string numeric `odds` and `profit_loss` to numbers where safe.
- If `opening_odds` missing but `odds` exists, set `opening_odds` = `odds`.
- If `profit_loss` missing but `profit` exists, copy `profit` -> `profit_loss`.
- Normalize `status`/`result` casing to canonical values (WIN/LOSS/PUSH/VOID/PENDING).

Backups: writes cleaned copies only; originals remain untouched.
"""
import json
import glob
import os
from pathlib import Path
import re

WORKDIR = Path(__file__).resolve().parents[1]
OUT_BASE = WORKDIR / 'tools' / 'reports' / 'fixed'
OUT_BASE.mkdir(parents=True, exist_ok=True)

TRACKING_FILES = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))

def parse_odds_str(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    m = re.match(r'^\+?(\d+)$', s)
    if m:
        return int(m.group(1))
    m = re.match(r'^-(\d+)$', s)
    if m:
        return -int(m.group(1))
    # try plain int
    try:
        return int(float(s))
    except Exception:
        return None


def canonical_result(s):
    if s is None:
        return None
    s = str(s).strip()
    low = s.lower()
    if low in ('win','won','w'):
        return 'WIN'
    if low in ('loss','lost','l'):
        return 'LOSS'
    if low in ('push','tie'):
        return 'PUSH'
    if low in ('void','dnp'):
        return 'VOID'
    if low in ('pending','pending_pick','open'):
        return 'PENDING'
    return s


def clean_pick(p):
    changed = False
    # odds fields
    # prefer numeric `odds` int; if missing, parse `odds_str` or `odds` string
    odds = p.get('odds')
    if odds is None:
        odds_str = p.get('odds_str') or p.get('odds_str')
        parsed = parse_odds_str(odds_str)
        if parsed is not None:
            p['odds'] = parsed
            changed = True
    else:
        # convert string numeric to int
        parsed = parse_odds_str(odds)
        if parsed is not None and parsed != odds:
            p['odds'] = parsed
            changed = True

    # opening_odds fallback
    if not p.get('opening_odds') and p.get('odds') is not None:
        p['opening_odds'] = p['odds']
        changed = True

    # profit_loss fallback from profit
    if 'profit_loss' not in p or p.get('profit_loss') is None:
        if 'profit' in p and p.get('profit') is not None:
            try:
                p['profit_loss'] = float(p['profit'])
                changed = True
            except Exception:
                pass

    # convert profit_loss string to number
    if 'profit_loss' in p and p.get('profit_loss') is not None:
        try:
            p['profit_loss'] = float(p['profit_loss'])
            changed = True
        except Exception:
            # leave as-is
            pass

    # normalize status/result
    st = p.get('status') or p.get('result')
    if st is not None:
        canon = canonical_result(st)
        if canon:
            p['result'] = canon
            p['status'] = canon.lower()
            changed = True

    return p, changed


def process_file(path):
    rel = Path(path).relative_to(WORKDIR)
    out_path = OUT_BASE / (str(rel).replace(os.sep, '__') + '.fixed.json')
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return (path, False, f'read_error: {e}')

    picks = None
    if isinstance(data, dict) and 'picks' in data and isinstance(data['picks'], list):
        picks = data['picks']
    elif isinstance(data, list):
        picks = data
    else:
        # search for first list
        for v in data.values() if isinstance(data, dict) else []:
            if isinstance(v, list):
                picks = v
                break
    if picks is None:
        picks = [data] if isinstance(data, dict) else []

    changed_any = False
    cleaned = []
    for p in picks:
        if not isinstance(p, dict):
            cleaned.append(p)
            continue
        p_clean, changed = clean_pick(p)
        cleaned.append(p_clean)
        changed_any = changed_any or changed

    # write cleaned copy
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out_path, 'w') as f:
            json.dump({'picks': cleaned}, f, indent=2)
    except Exception as e:
        return (path, False, f'write_error: {e}')

    return (path, True, str(out_path))


def main():
    results = []
    for t in TRACKING_FILES:
        res = process_file(t)
        results.append(res)
        print('Processed:', res)

    print('Fixed copies written to', OUT_BASE)


if __name__ == '__main__':
    main()
