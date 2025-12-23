#!/usr/bin/env python3
"""Safely overwrite original tracking JSONs with cleaned fixed copies.

Behavior:
- Creates timestamped backups under `tools/reports/backups/` preserving relative paths.
- For each original `*_tracking.json` with a corresponding fixed file in
  `tools/reports/fixed/` (naming convention: relative_path with os.sep -> '__' + '.fixed.json'),
  copy original to backup then overwrite original with fixed content.
- Writes a CSV log `tools/reports/overwrite_log.csv` listing actions performed.

Run only after reviewing backups and fixed copies.
"""
import json
import glob
import os
import shutil
from pathlib import Path
import csv
from datetime import datetime

WORKDIR = Path(__file__).resolve().parents[1]
FIXED_DIR = WORKDIR / 'tools' / 'reports' / 'fixed'
OUT_DIR = WORKDIR / 'tools' / 'reports'
TIMESTAMP = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
BACKUP_DIR = OUT_DIR / 'backups' / TIMESTAMP
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

ORIG_FILES = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))


def find_fixed_for(orig_path: str):
    rel = Path(orig_path).relative_to(WORKDIR)
    fixed_name = str(rel).replace(os.sep, '__') + '.fixed.json'
    fixed_path = FIXED_DIR / fixed_name
    return fixed_path if fixed_path.exists() else None


def backup_file(orig: str, backup_base: Path):
    rel = Path(orig).relative_to(WORKDIR)
    dest = backup_base / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(orig, dest)
    return dest


def overwrite(orig: str, fixed: Path):
    # Read fixed JSON and write to orig path atomically
    with open(fixed, 'r') as f:
        data = json.load(f)
    tmp = Path(orig).with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, orig)


def main():
    log_rows = []
    for orig in ORIG_FILES:
        fixed = find_fixed_for(orig)
        if not fixed:
            log_rows.append((orig, '', '', 'no-fixed', ''))
            continue
        try:
            backup_path = backup_file(orig, BACKUP_DIR)
            overwrite(orig, fixed)
            log_rows.append((orig, str(fixed), str(backup_path), 'overwritten', ''))
        except Exception as e:
            log_rows.append((orig, str(fixed), '', 'error', str(e)))

    csv_out = OUT_DIR / 'overwrite_log.csv'
    with open(csv_out, 'w', newline='') as cf:
        writer = csv.writer(cf)
        writer.writerow(['original','fixed','backup','status','notes'])
        for r in log_rows:
            writer.writerow(r)

    print('Backups written to', BACKUP_DIR)
    print('Overwrite log:', csv_out)


if __name__ == '__main__':
    main()
