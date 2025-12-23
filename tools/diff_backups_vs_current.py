#!/usr/bin/env python3
"""Compare backed-up originals to current files and write a summary CSV of JSON key-level differences.

Outputs:
- `tools/reports/backups_vs_current_diff.csv` with per-file counts of keys added/removed/changed.
- small JSON samples of changed keys in `tools/reports/backups_diffs/`.
"""
import json
import glob
import os
from pathlib import Path

WORKDIR = Path(__file__).resolve().parents[1]
BACKUPS_ROOT = WORKDIR / 'tools' / 'reports' / 'backups'
OUT_DIR = WORKDIR / 'tools' / 'reports'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def find_latest_backup_dir():
    if not BACKUPS_ROOT.exists():
        return None
    dirs = [d for d in BACKUPS_ROOT.iterdir() if d.is_dir()]
    if not dirs:
        return None
    return sorted(dirs)[-1]


def load_json(p):
    with open(p, 'r') as f:
        return json.load(f)


def main():
    latest = find_latest_backup_dir()
    if not latest:
        print('No backups found under', BACKUPS_ROOT)
        return

    rows = []
    diffs_dir = OUT_DIR / 'backups_diffs'
    diffs_dir.mkdir(parents=True, exist_ok=True)

    for orig in sorted(glob.glob(str(latest / '**' / '*_tracking.json'), recursive=True)):
        rel = Path(orig).relative_to(latest)
        current = WORKDIR / rel
        if not current.exists():
            rows.append((str(rel), 'MISSING_CURRENT', '', '', ''))
            continue
        try:
            a = load_json(orig)
            b = load_json(current)
            fa = flatten_json(a)
            fb = flatten_json(b)
            keys_a = set(fa.keys())
            keys_b = set(fb.keys())
            added = len(keys_b - keys_a)
            removed = len(keys_a - keys_b)
            common = keys_a & keys_b
            changed = sum(1 for k in common if not values_equal(fa[k], fb[k]))
            note = ''
            rows.append((str(rel), added, removed, changed, note))
            if added or removed or changed:
                dd = {'added_keys': list(keys_b - keys_a), 'removed_keys': list(keys_a - keys_b), 'changed_keys_sample': [k for k in list(common)[:10]]}
                with open(diffs_dir / (str(rel).replace(os.sep,'__') + '.diff.json'), 'w') as f:
                    json.dump(dd, f, indent=2, default=str)
        except Exception as e:
            rows.append((str(rel), 'ERROR', '', '', str(e)))

    import csv
    out = OUT_DIR / 'backups_vs_current_diff.csv'
    with open(out, 'w', newline='') as cf:
        w = csv.writer(cf)
        w.writerow(['relative_path','keys_added','keys_removed','keys_changed','note'])
        for r in rows:
            w.writerow(r)

    print('Wrote', out, 'and diffs in', diffs_dir)


def json_snippet(dd):
    try:
        return json.dumps(dd, default=str)[:200]
    except Exception:
        return ''


def flatten_json(obj, prefix=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            out.update(flatten_json(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            path = f"{prefix}[{i}]"
            out.update(flatten_json(v, path))
    else:
        out[prefix] = obj
    return out


def values_equal(a, b):
    try:
        return a == b
    except Exception:
        return str(a) == str(b)


if __name__ == '__main__':
    main()
