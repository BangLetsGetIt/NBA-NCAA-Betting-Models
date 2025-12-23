#!/usr/bin/env python3
"""Normalize tracking JSON dicts to a canonical schema.

Provides `normalize_tracking(obj)` to be imported by model writers.
Also includes a CLI to run in dry-run or write-back mode.

Canonical fields ensured per-pick:
- `pick_id` (string)
- `game_time` (ISO8601 string)
- `odds` (float) and `opening_odds` (float if available)
- `profit_loss` (float)
- `placed_at` (ISO8601 string)
- `stake` (float)

The normalizer is conservative: it will not invent results, only coerce/rename existing fields.
"""
from datetime import datetime
from pathlib import Path
import json
import uuid
from typing import Any, Dict


def to_iso(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def ensure_pick_id(p: Dict[str, Any]):
    for k in ('pick_id', 'id'):
        if k in p and p[k] is not None:
            return str(p[k])
    # generate deterministic-ish id from uuid4
    return str(uuid.uuid4())


def normalize_pick(p: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(p)  # shallow copy
    # pick id
    out['pick_id'] = ensure_pick_id(p)

    # game time
    for gk in ('game_time', 'game_date', 'start_time'):
        if gk in p and p[gk]:
            out['game_time'] = to_iso(p[gk])
            break

    # placed at / timestamp
    for tk in ('placed_at', 'timestamp', 'created_at', 'recorded_at'):
        if tk in p and p[tk]:
            out['placed_at'] = to_iso(p[tk])
            break

    # odds
    o = p.get('odds') if 'odds' in p else p.get('opening_odds') if 'opening_odds' in p else p.get('price')
    o_f = safe_float(o)
    if o_f is not None:
        out['odds'] = o_f
    if 'opening_odds' in p and p.get('opening_odds') is not None:
        out['opening_odds'] = safe_float(p.get('opening_odds'))

    # closing odds -> keep if exists
    if 'closing_odds' in p and p.get('closing_odds') is not None:
        out['closing_odds'] = safe_float(p.get('closing_odds'))

    # profit_loss
    for pk in ('profit_loss', 'profit', 'pnl'):
        if pk in p and p[pk] is not None:
            out['profit_loss'] = safe_float(p[pk])
            break

    # stake
    for sk in ('stake', 'amount', 'wager', 'unit_stake'):
        if sk in p and p[sk] is not None:
            out['stake'] = safe_float(p[sk])
            break

    return out


def normalize_tracking(obj: Any) -> Any:
    # If top-level dict with 'picks' list, normalize each element
    if isinstance(obj, dict):
        if 'picks' in obj and isinstance(obj['picks'], list):
            obj2 = dict(obj)
            obj2['picks'] = [normalize_pick(p) for p in obj['picks'] if isinstance(p, dict)]
            return obj2
        # else try to find a list value
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                obj2 = dict(obj)
                obj2[k] = [normalize_pick(p) for p in v]
                return obj2
        # single-pick dict
        return normalize_pick(obj)
    elif isinstance(obj, list):
        return [normalize_pick(p) for p in obj if isinstance(p, dict)]
    else:
        return obj


def _cli_process_folder(folder: Path, write_back: bool = False):
    files = list(folder.glob('**/*_tracking.json'))
    changed = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            norm = normalize_tracking(data)
            if json.dumps(norm, sort_keys=True) != json.dumps(data, sort_keys=True):
                changed.append(str(f))
                if write_back:
                    f.write_text(json.dumps(norm, indent=2, ensure_ascii=False))
        except Exception:
            continue
    return changed


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--path', default='.', help='workspace root or folder')
    p.add_argument('--write', action='store_true', help='write normalized files in place')
    args = p.parse_args()
    root = Path(args.path).resolve()
    changed = _cli_process_folder(root, write_back=args.write)
    print('Files that would change:' if not args.write else 'Files changed:')
    for c in changed:
        print(c)
