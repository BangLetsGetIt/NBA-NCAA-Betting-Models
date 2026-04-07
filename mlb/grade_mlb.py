#!/usr/bin/env python3
"""Standalone MLB grader - grades all pending picks and pushes to GitHub."""

import json, requests, re, os, subprocess
from datetime import datetime, timedelta
import pytz

TRACKING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mlb_master_model_tracking.json')
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ABBR_MAP = {'AZ': 'ARI', 'CWS': 'CHW'}
REV_MAP = {v: k for k, v in ABBR_MAP.items()}

with open(TRACKING_FILE) as f:
    tracking = json.load(f)

picks = tracking.get('picks', [])
pending = [p for p in picks if p.get('status', '').lower() == 'pending']
print(f"Found {len(pending)} pending picks to grade.\n")

# Fetch completed games last 4 days
et_tz = pytz.timezone('US/Eastern')
completed_events = {}

for i in range(4):
    date_compact = (datetime.now(et_tz) - timedelta(days=i)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_compact}"
    resp = requests.get(url, timeout=15)
    for event in resp.json().get('events', []):
        if event.get('status', {}).get('type', {}).get('completed', False):
            completed_events[event['id']] = event
    count = sum(1 for e in resp.json().get('events', []) if e.get('status', {}).get('type', {}).get('completed', False))
    print(f"  {date_compact}: {count} completed games")

print(f"\nTotal completed events: {len(completed_events)}\n")

# Build game lookup
game_lookup = {}
for event_id, event in completed_events.items():
    comp = event.get('competitions', [{}])[0]
    competitors = comp.get('competitors', [])
    away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
    home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
    if away and home:
        away_espn = away.get('team', {}).get('abbreviation', '')
        home_espn = home.get('team', {}).get('abbreviation', '')
        away_track = REV_MAP.get(away_espn, away_espn)
        home_track = REV_MAP.get(home_espn, home_espn)
        entry = {'event_id': event_id, 'away_abbr': away_track, 'home_abbr': home_track}
        game_lookup[f"{away_espn} @ {home_espn}"] = entry
        game_lookup[f"{away_track} @ {home_track}"] = entry

graded = 0

for pick in picks:
    if pick.get('status', '').lower() != 'pending':
        continue

    matchup   = pick.get('matchup', '')
    pick_type = pick.get('type', '')
    pick_line = pick.get('line', '')
    pick_sel  = pick.get('selection', '')

    game = game_lookup.get(matchup)
    if not game:
        continue

    sdata = requests.get(
        f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game['event_id']}",
        timeout=15
    ).json()

    away_abbr = game['away_abbr']
    home_abbr = game['home_abbr']

    # --- F5 ML ---
    if 'First 5' in pick_type:
        header_comp = sdata.get('header', {}).get('competitions', [{}])[0]
        competitors = header_comp.get('competitors', [])
        away_c = next((c for c in competitors if c.get('homeAway') == 'away'), None)
        home_c = next((c for c in competitors if c.get('homeAway') == 'home'), None)
        if not away_c or not home_c:
            continue
        away_ls = away_c.get('linescores', [])
        home_ls = home_c.get('linescores', [])
        if len(away_ls) < 5 or len(home_ls) < 5:
            continue
        away_f5 = sum(int(inn.get('displayValue', 0) or 0) for inn in away_ls[:5])
        home_f5 = sum(int(inn.get('displayValue', 0) or 0) for inn in home_ls[:5])
        selected = away_abbr if away_abbr in pick_sel else home_abbr
        sel_runs = away_f5 if selected == away_abbr else home_f5
        opp_runs = home_f5 if selected == away_abbr else away_f5
        result_str = f"{away_abbr} {away_f5} - {home_abbr} {home_f5} (F5)"
        if sel_runs > opp_runs:
            pick['status'] = 'Win'; pick['profit'] = round(pick.get('odds_dec', 1.91) - 1, 4)
        elif sel_runs < opp_runs:
            pick['status'] = 'Loss'; pick['profit'] = -1.0
        else:
            pick['status'] = 'Push'; pick['profit'] = 0.0
        pick['result'] = f"{pick['status']} ({result_str})"
        graded += 1
        print(f"  ✓ F5  {matchup}: {pick['status']} | {result_str}")

    # --- K Props ---
    elif 'Strikeout' in pick_type:
        m = re.search(r'(Over|Under)\s+([\d.]+)', pick_line)
        if not m:
            continue
        direction, line_val = m.group(1), float(m.group(2))
        pitcher_ks = None
        for team_data in sdata.get('boxscore', {}).get('players', []):
            for cat in team_data.get('statistics', []):
                labels = cat.get('labels', [])
                if 'K' not in labels:
                    continue
                k_idx = labels.index('K')
                for ath in cat.get('athletes', []):
                    if pick_sel.split()[-1].lower() in ath.get('athlete', {}).get('displayName', '').lower():
                        try:
                            pitcher_ks = int(ath.get('stats', [])[k_idx])
                        except:
                            pass
                        break
                if pitcher_ks is not None:
                    break
        if pitcher_ks is None:
            print(f"  ? K stats not found: {pick_sel}")
            continue
        result_str = f"{pick_sel}: {pitcher_ks} Ks (line {line_val})"
        if (direction == 'Over' and pitcher_ks > line_val) or (direction == 'Under' and pitcher_ks < line_val):
            pick['status'] = 'Win'; pick['profit'] = round(pick.get('odds_dec', 1.91) - 1, 4)
        elif pitcher_ks == line_val:
            pick['status'] = 'Push'; pick['profit'] = 0.0
        else:
            pick['status'] = 'Loss'; pick['profit'] = -1.0
        pick['result'] = f"{pick['status']} ({result_str})"
        graded += 1
        print(f"  ✓ K   {pick_sel}: {pick['status']} | {result_str}")

    # --- H+R+RBI Props ---
    elif 'H+R+RBI' in pick_type or 'HRBI' in pick_type:
        m = re.search(r'(Over|Under)\s+([\d.]+)', pick_line)
        if not m:
            continue
        direction, line_val = m.group(1), float(m.group(2))
        batter_stat = None
        for team_data in sdata.get('boxscore', {}).get('players', []):
            for cat in team_data.get('statistics', []):
                labels = cat.get('labels', [])
                if 'H' not in labels or 'R' not in labels or 'RBI' not in labels:
                    continue
                h_idx, r_idx, rbi_idx = labels.index('H'), labels.index('R'), labels.index('RBI')
                for ath in cat.get('athletes', []):
                    if pick_sel.split()[-1].lower() in ath.get('athlete', {}).get('displayName', '').lower():
                        try:
                            stats = ath.get('stats', [])
                            batter_stat = int(stats[h_idx]) + int(stats[r_idx]) + int(stats[rbi_idx])
                        except:
                            pass
                        break
                if batter_stat is not None:
                    break
        if batter_stat is None:
            print(f"  ? H+R+RBI stats not found: {pick_sel}")
            continue
        result_str = f"{pick_sel}: {batter_stat} H+R+RBI (line {line_val})"
        if (direction == 'Over' and batter_stat > line_val) or (direction == 'Under' and batter_stat < line_val):
            pick['status'] = 'Win'; pick['profit'] = round(pick.get('odds_dec', 1.91) - 1, 4)
        elif batter_stat == line_val:
            pick['status'] = 'Push'; pick['profit'] = 0.0
        else:
            pick['status'] = 'Loss'; pick['profit'] = -1.0
        pick['result'] = f"{pick['status']} ({result_str})"
        graded += 1
        print(f"  ✓ HRR {pick_sel}: {pick['status']} | {result_str}")

    # --- HR Props ---
    elif 'Home Run' in pick_type:
        hr_hit = None
        for team_data in sdata.get('boxscore', {}).get('players', []):
            for cat in team_data.get('statistics', []):
                labels = cat.get('labels', [])
                if 'HR' not in labels:
                    continue
                hr_idx = labels.index('HR')
                for ath in cat.get('athletes', []):
                    if pick_sel.split()[-1].lower() in ath.get('athlete', {}).get('displayName', '').lower():
                        try:
                            hr_hit = int(ath.get('stats', [])[hr_idx]) > 0
                        except:
                            pass
                        break
                if hr_hit is not None:
                    break
        if hr_hit is None:
            print(f"  ? HR stats not found: {pick_sel}")
            continue
        result_str = f"{pick_sel}: {'Hit HR' if hr_hit else 'No HR'}"
        if hr_hit:
            pick['status'] = 'Win'; pick['profit'] = round(pick.get('odds_dec', 3.5) - 1, 4)
        else:
            pick['status'] = 'Loss'; pick['profit'] = -1.0
        pick['result'] = f"{pick['status']} ({result_str})"
        graded += 1
        print(f"  ✓ HR  {pick_sel}: {pick['status']} | {result_str}")

# Save
tracking['picks'] = picks
with open(TRACKING_FILE, 'w') as f:
    json.dump(tracking, f, indent=2)

wins   = len([p for p in picks if p.get('status') == 'Win'])
losses = len([p for p in picks if p.get('status') == 'Loss'])
pushes = len([p for p in picks if p.get('status') == 'Push'])
still  = len([p for p in picks if p.get('status', '').lower() == 'pending'])

print(f"\n{'='*50}")
print(f"Graded {graded} picks.")
print(f"Record: {wins}-{losses}-{pushes} | Still pending: {still}")
print(f"{'='*50}\n")

# Regenerate HTML
print("Regenerating HTML...")
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location('mlb_master_model', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mlb_master_model.py'))
mlb_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlb_mod)
stats = mlb_mod.calculate_tracking_stats()
# Pass today's pending picks so they still show on the page
today_str = __import__('datetime').datetime.now().strftime('%Y%m%d')
active_picks = [p for p in picks if p.get('status','').lower() == 'pending' and today_str in p.get('id','')]
html = mlb_mod.generate_html(active_picks, stats)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mlb_master_model.html'), 'w') as f:
    f.write(html)
print("HTML updated.")

# Push to GitHub
print("Pushing to GitHub...")
subprocess.run(['bash', os.path.join(SCRIPT_DIR, 'auto_push.sh')], cwd=SCRIPT_DIR)
print("Done.")
