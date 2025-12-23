#!/usr/bin/env python3
"""Perform basic bet-realism checks across tracking JSONs.

Outputs:
- `tools/reports/bet_realism_summary.csv` (per-file summary)
- per-model detail markdowns in `tools/reports/bet_realism_details/`

Checks performed:
- presence of placement timestamp and game start time
- lead time stats (seconds between placement and game start)
- fraction of picks placed <60s, <300s, <3600s before start
- picks placed after start (negative lead)
- presence of odds/opening_odds/closing_odds and avg absolute movement
- stake distribution (median, top 5)
"""
import json
import glob
import os
from pathlib import Path
from statistics import median
from datetime import datetime

WORKDIR = Path(__file__).resolve().parents[1]
OUT_DIR = WORKDIR / 'tools' / 'reports'
DETAIL_DIR = OUT_DIR / 'bet_realism_details'
OUT_DIR.mkdir(parents=True, exist_ok=True)
DETAIL_DIR.mkdir(parents=True, exist_ok=True)


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


def parse_time(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        # assume epoch seconds
        try:
            return datetime.utcfromtimestamp(float(s))
        except Exception:
            return None
    if isinstance(s, str):
        for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.fromisoformat(s)
            except Exception:
                pass
        try:
            # try numeric string
            return datetime.utcfromtimestamp(float(s))
        except Exception:
            return None
    return None


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def analyze_file(path):
    with open(path, 'r') as f:
        data = json.load(f)
    picks = normalize(data)
    total = len(picks)
    timestamps = []
    lead_secs = []
    late = 0
    short60 = 0
    short300 = 0
    short3600 = 0
    odds_present = 0
    opening_present = 0
    closing_present = 0
    odds_moves = []
    stakes = []

    for p in picks:
        # find placement timestamp
        placed_candidates = [p.get('placed_at'), p.get('timestamp'), p.get('created_at'), p.get('recorded_at')]
        placed = None
        for c in placed_candidates:
            t = parse_time(c)
            if t:
                placed = t
                break

        # find game time
        game_candidates = [p.get('game_time'), p.get('game_date'), p.get('start_time'), p.get('kickoff')]
        game = None
        for c in game_candidates:
            t = parse_time(c)
            if t:
                game = t
                break

        if placed:
            timestamps.append(placed.isoformat())

        if placed and game:
            sec = (game - placed).total_seconds()
            lead_secs.append(sec)
            if sec < 0:
                late += 1
            if sec < 60:
                short60 += 1
            if sec < 300:
                short300 += 1
            if sec < 3600:
                short3600 += 1

        # odds
        o = safe_float(p.get('odds') or p.get('opening_odds') or p.get('price') )
        co = safe_float(p.get('closing_odds') or p.get('settled_odds') )
        if o is not None:
            odds_present += 1
        if p.get('opening_odds') is not None:
            opening_present += 1
        if co is not None:
            closing_present += 1
        if o is not None and co is not None:
            try:
                odds_moves.append(abs(co - o))
            except Exception:
                pass

        # stake
        s = safe_float(p.get('stake') or p.get('amount') or p.get('wager') or p.get('unit_stake'))
        if s is not None:
            stakes.append(s)

    summary = {
        'file': str(path),
        'total_picks': total,
        'timestamps_count': len(timestamps),
        'lead_median_sec': median(lead_secs) if lead_secs else None,
        'late_count': late,
        'short60': short60,
        'short300': short300,
        'short3600': short3600,
        'odds_present': odds_present,
        'opening_present': opening_present,
        'closing_present': closing_present,
        'avg_abs_odds_move': (sum(odds_moves)/len(odds_moves)) if odds_moves else None,
        'median_stake': median(stakes) if stakes else None,
        'top5_stakes': sorted(stakes, reverse=True)[:5]
    }

    detail_lines = []
    detail_lines.append(f"File: {path}")
    detail_lines.append(f"Total picks: {total}")
    detail_lines.append(f"Timestamps present: {len(timestamps)}")
    detail_lines.append(f"Median lead seconds: {summary['lead_median_sec']}")
    detail_lines.append(f"Picks after start (late): {late}")
    detail_lines.append(f"<60s: {short60}, <300s: {short300}, <3600s: {short3600}")
    detail_lines.append(f"Odds present: {odds_present}, opening: {opening_present}, closing:{closing_present}")
    detail_lines.append(f"Avg abs odds move: {summary['avg_abs_odds_move']}")
    detail_lines.append(f"Median stake: {summary['median_stake']}")
    detail_lines.append(f"Top stakes: {summary['top5_stakes']}")

    return summary, '\n'.join(detail_lines)


def main():
    files = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))
    import csv
    outcsv = OUT_DIR / 'bet_realism_summary.csv'
    with open(outcsv, 'w', newline='') as cf:
        w = csv.writer(cf)
        w.writerow(['file','total_picks','timestamps_count','lead_median_sec','late_count','<60s','<300s','<3600s','odds_present','opening_present','closing_present','avg_abs_odds_move','median_stake','top5_stakes'])
        for f in files:
            s, detail = analyze_file(f)
            w.writerow([s['file'], s['total_picks'], s['timestamps_count'], s['lead_median_sec'], s['late_count'], s['short60'], s['short300'], s['short3600'], s['odds_present'], s['opening_present'], s['closing_present'], s['avg_abs_odds_move'], s['median_stake'], json.dumps(s['top5_stakes'])])
            mdname = DETAIL_DIR / (Path(f).relative_to(WORKDIR).as_posix().replace('/','__') + '.md')
            with open(mdname, 'w') as m:
                m.write(detail)

    print('Wrote', outcsv, 'and details in', DETAIL_DIR)


if __name__ == '__main__':
    main()
