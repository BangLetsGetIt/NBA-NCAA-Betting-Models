#!/usr/bin/env python3
"""Compute standardized metrics from model tracking JSON files.
Writes `audit_metrics_summary.csv` and per-model JSON summaries in `tools/metrics_out/`.
"""
import json
import glob
import os
from pathlib import Path
from statistics import mean

WORKDIR = Path(__file__).resolve().parents[1]
OUT_DIR = WORKDIR / "tools" / "metrics_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRACKING_FILES = sorted(glob.glob(str(WORKDIR / "**" / "*_tracking.json"), recursive=True))

def am_to_decimal(odds):
    try:
        o = int(odds)
    except:
        return None
    if o > 0:
        return o / 100.0 + 1.0
    else:
        return 100.0 / abs(o) + 1.0


def process_file(path):
    with open(path, 'r') as f:
        data = json.load(f)

    # Normalize different tracking file formats
    if isinstance(data, dict):
        if 'picks' in data and isinstance(data['picks'], list):
            picks = data['picks']
        else:
            # Try to find the first list value that looks like picks
            picks = None
            for v in data.values():
                if isinstance(v, list):
                    picks = v
                    break
            if picks is None:
                # Treat whole dict as single pick record
                picks = [data]
    elif isinstance(data, list):
        picks = data
    else:
        picks = []

    model_name = Path(path).parents[0].name + '/' + Path(path).name

    settled = []
    clv_list = []
    brier_samples = []

    net_profit = 0.0
    total_stake = 0.0
    wins = losses = pushes = voids = 0

    for p in picks:
        # p may be a non-dict if files are inconsistent
        if not isinstance(p, dict):
            continue
        status = (p.get('status') or '').lower()
        # normalize
        if status in ('win', 'won') or p.get('result') in ('WIN','Win'):
            wins += 1
            settled_flag = True
        elif status in ('loss', 'lost') or p.get('result') in ('LOSS','Loss'):
            losses += 1
            settled_flag = True
        elif status in ('push', 'void') or p.get('result') in ('VOID','DNP'):
            if status in ('push', 'void') or p.get('result') in ('VOID','DNP'):
                pushes += 1
            settled_flag = False
        else:
            settled_flag = False

        profit = p.get('profit_loss') if p.get('profit_loss') is not None else p.get('profit', 0)
        if profit is None:
            profit = 0
        try:
            profit = float(profit)
        except:
            profit = 0

        bet_units = float(p.get('bet_size_units', 1.0)) if p.get('bet_size_units') is not None else 1.0

        if settled_flag:
            net_profit += profit
            total_stake += bet_units * 100.0

        # CLV / implied prob
        model_prob = p.get('prob') or p.get('win_prob') or p.get('proj_prob') or p.get('model_prob')
        odds_field = p.get('latest_odds') or p.get('opening_odds') or p.get('odds')
        dec = None
        if odds_field is not None:
            dec = am_to_decimal(odds_field)
        if dec and model_prob is not None:
            try:
                implied = 1.0 / dec
                clv_list.append((float(model_prob) - implied) * 100.0)
            except:
                pass

        # brier
        if model_prob is not None and settled_flag:
            try:
                prob = float(model_prob)
                outcome = 1.0 if (p.get('result') in ('WIN','Win') or (p.get('status') or '').lower()=='win') else 0.0
                brier_samples.append((prob - outcome) ** 2)
            except:
                pass

    total_bets = wins + losses
    roi = (net_profit / total_stake * 100.0) if total_stake > 0 else None
    avg_clv = mean(clv_list) if clv_list else None
    brier = mean(brier_samples) if brier_samples else None
    avg_profit_per_bet = (net_profit / total_bets) if total_bets > 0 else None

    summary = {
        'model': model_name,
        'file': path,
        'total_picks': len(picks),
        'total_settled': total_bets,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'net_profit': net_profit,
        'total_stake': total_stake,
        'roi_pct': roi,
        'avg_profit_per_bet': avg_profit_per_bet,
        'avg_clv_pct_points': avg_clv,
        'brier_score': brier
    }

    # write per-model summary
    outp = OUT_DIR / (Path(path).stem + '_metrics.json')
    with open(outp, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    summaries = []
    for t in TRACKING_FILES:
        try:
            summaries.append(process_file(t))
        except Exception as e:
            print(f"Error processing {t}: {e}")

    # write consolidated CSV
    import csv
    with open(WORKDIR / 'audit_metrics_summary.csv', 'w', newline='') as csvf:
        writer = csv.DictWriter(csvf, fieldnames=['model','file','total_picks','total_settled','wins','losses','pushes','net_profit','total_stake','roi_pct','avg_profit_per_bet','avg_clv_pct_points','brier_score'])
        writer.writeheader()
        for s in summaries:
            writer.writerow(s)

    print(f"Processed {len(summaries)} tracking files. Output in {OUT_DIR} and audit_metrics_summary.csv")

if __name__ == '__main__':
    main()
