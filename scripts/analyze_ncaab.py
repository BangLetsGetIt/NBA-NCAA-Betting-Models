#!/usr/bin/env python3
import json, os, datetime
p = 'ncaa/ncaab_picks_tracking.json'
if not os.path.exists(p):
    print('NO_FILE')
    raise SystemExit
with open(p, 'r') as f:
    data = json.load(f)

picks = [x for x in data.get('picks', []) if x.get('status','').lower() in ('win','loss','push')]

def is_dog(p):
    return '+' in (p.get('pick_text','') or '')

def profit_unit(p):
    pr = p.get('profit', 0)
    if pr == 0:
        s = p.get('status','').lower()
        if s == 'win': pr = 91.0
        elif s == 'loss': pr = -100.0
    return float(pr) / 100.0

summary = {'total_picks': len(picks), 'total_units': 0.0, 'wins': 0, 'losses': 0, 'pushes': 0}
by_type = {}
by_bucket = {}
by_dog = {'dog': {'count':0,'units':0.0}, 'fav': {'count':0,'units':0.0}}
by_home = {'home_bet': {'count':0,'units':0.0}, 'away_bet': {'count':0,'units':0.0}}

buckets = [(-999,-10),(-10,-5),(-5,-1),(-1,1),(1,5),(5,10),(10,999)]
labels = ['<=-10','-10..-5','-5..-1','-1..1','1..5','5..10','>10']
for b in buckets:
    by_bucket[b] = {'count':0,'units':0.0}

now = datetime.datetime.utcnow()
recent_cut = now - datetime.timedelta(days=90)
recent = {'count':0,'units':0.0}

for p in picks:
    u = profit_unit(p)
    summary['total_units'] += u
    st = p.get('status','').lower()
    if st == 'win': summary['wins'] += 1
    elif st == 'loss': summary['losses'] += 1
    elif st == 'push': summary['pushes'] += 1

    t = p.get('pick_type','unknown')
    bt = by_type.setdefault(t, {'count':0,'units':0.0})
    bt['count'] += 1
    bt['units'] += u

    edge = p.get('edge', 0) or 0
    for lb,ub in buckets:
        if edge > lb and edge <= ub:
            by_bucket[(lb,ub)]['count'] += 1
            by_bucket[(lb,ub)]['units'] += u
            break

    if is_dog(p):
        by_dog['dog']['count'] += 1
        by_dog['dog']['units'] += u
    else:
        by_dog['fav']['count'] += 1
        by_dog['fav']['units'] += u

    pt = (p.get('pick_text') or '').upper()
    home = (p.get('home_team') or '').upper()
    away = (p.get('away_team') or '').upper()
    if home and home in pt:
        by_home['home_bet']['count'] += 1
        by_home['home_bet']['units'] += u
    elif away and away in pt:
        by_home['away_bet']['count'] += 1
        by_home['away_bet']['units'] += u

    gt = p.get('game_time')
    try:
        gdt = datetime.datetime.fromisoformat(gt.replace('Z', '+00:00'))
        if gdt >= recent_cut:
            recent['count'] += 1
            recent['units'] += u
    except:
        pass

# Output
print('TOTAL PICKS:', summary['total_picks'])
print('TOTAL UNITS:', round(summary['total_units'],2))
wr = summary['wins'] / (summary['wins'] + summary['losses']) if (summary['wins'] + summary['losses'])>0 else 0
print('WINRATE:', f"{wr:.3f}", '(wins,losses)', summary['wins'], summary['losses'])
print('\nBY PICK TYPE:')
for k,v in sorted(by_type.items(), key=lambda x: -x[1]['units']):
    avg = v['units']/v['count'] if v['count'] else 0
    print(f"{k}: count={v['count']} units={v['units']:.2f} avg_units={avg:.3f}")

print('\nBY EDGE BUCKET:')
for lbl,(lb,ub) in zip(labels,buckets):
    val = by_bucket[(lb,ub)]
    print(f"{lbl}: count={val['count']} units={val['units']:.2f}")

print('\nDOG vs FAV:')
for k,v in by_dog.items():
    print(f"{k}: count={v['count']} units={v['units']:.2f}")

print('\nHOME vs AWAY (bet on):')
for k,v in by_home.items():
    print(f"{k}: count={v['count']} units={v['units']:.2f}")

print('\nRECENT 90d:', recent['count'], round(recent['units'],2))
