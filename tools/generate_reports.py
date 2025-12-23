#!/usr/bin/env python3
"""Generate per-model reports (P&L curve, CLV histogram, calibration) and markdown summary.
Writes outputs to `tools/reports/` with images in `tools/reports/images/`.
"""
import json
import glob
import os
from pathlib import Path
from statistics import mean
import math

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

WORKDIR = Path(__file__).resolve().parents[1]
OUT_DIR = WORKDIR / "tools" / "reports"
IMG_DIR = OUT_DIR / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)

METRICS_DIR = WORKDIR / "tools" / "metrics_out"
METRICS_FILES = sorted(glob.glob(str(METRICS_DIR / "*_metrics.json")))


def am_to_decimal(o):
    try:
        o = int(o)
    except:
        return None
    if o > 0:
        return o / 100.0 + 1.0
    else:
        return 100.0 / abs(o) + 1.0


def load_tracking(path):
    with open(path, 'r') as f:
        data = json.load(f)
    # Normalize
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
    # keep only dict picks
    picks = [p for p in picks if isinstance(p, dict)]
    return picks


def make_plots(model_key, tracking_file, picks):
    # Prepare DataFrame of settled picks sorted by updated_at or tracked_at
    df = pd.DataFrame(picks)
    if df.empty:
        return None

    # Normalize time column
    time_cols = [c for c in ['updated_at', 'last_updated', 'tracked_at', 'date_placed', 'created_at'] if c in df.columns]
    if time_cols:
        df['time'] = pd.to_datetime(df[time_cols[0]], errors='coerce')
    else:
        df['time'] = pd.NaT

    # Profit column
    if 'profit_loss' in df.columns:
        df['profit'] = pd.to_numeric(df['profit_loss'], errors='coerce').fillna(0)
    else:
        col = df.get('profit', None)
        if isinstance(col, (int, float)):
            df['profit'] = float(col)
        else:
            # col may be a Series or None
            try:
                df['profit'] = pd.to_numeric(col, errors='coerce').fillna(0)
            except Exception:
                df['profit'] = 0.0

    # Ensure profit is numeric
    df['profit'] = pd.to_numeric(df['profit'], errors='coerce').fillna(0.0)

    # settlement filter
    settled_mask = df.apply(lambda r: (str(r.get('status') or '').lower() in ('win','loss','won','lost') or r.get('result') in ('WIN','LOSS','Win','Loss')), axis=1)
    settled = df[settled_mask].copy()
    if settled.empty:
        settled = df[df['profit'] != 0].copy()

    # Sort by time if available, else by index
    if 'time' in settled.columns and settled['time'].notna().any():
        settled = settled.sort_values('time')
    else:
        settled = settled.sort_index()

    settled['cum_profit'] = settled['profit'].cumsum()

    plots = {}

    # P&L curve
    try:
        plt.figure(figsize=(8,3))
        plt.plot(settled['cum_profit'].values, marker='o', linewidth=1)
        plt.title(f"P&L Curve — {model_key}")
        plt.xlabel('Settled Bets')
        plt.ylabel('Cumulative Profit ($)')
        plt.grid(alpha=0.3)
        img_pl = IMG_DIR / f"{model_key.replace('/','_')}_pnl.png"
        plt.tight_layout()
        plt.savefig(img_pl)
        plt.close()
        plots['pnl'] = img_pl
    except Exception:
        plots['pnl'] = None

    # CLV histogram
    clv_vals = []
    for _, row in settled.iterrows():
        model_prob = row.get('prob') or row.get('win_prob') or row.get('proj_prob') or row.get('model_prob')
        odds_field = row.get('latest_odds') or row.get('opening_odds') or row.get('odds')
        dec = None
        if odds_field is not None:
            dec = am_to_decimal(odds_field)
        if dec and model_prob is not None:
            try:
                implied = 1.0 / dec
                clv_vals.append((float(model_prob) - implied) * 100.0)
            except:
                pass

    if clv_vals:
        try:
            plt.figure(figsize=(6,3))
            plt.hist(clv_vals, bins=25, color='#2d7fb8')
            plt.title(f"CLV Distribution (pct points) — {model_key}")
            plt.xlabel('Model Prob - Implied Prob (pct points)')
            plt.grid(axis='y', alpha=0.2)
            img_clv = IMG_DIR / f"{model_key.replace('/','_')}_clv.png"
            plt.tight_layout()
            plt.savefig(img_clv)
            plt.close()
            plots['clv'] = img_clv
        except Exception:
            plots['clv'] = None
    else:
        plots['clv'] = None

    # Calibration plot (bin probs -> observed frequency)
    probs = []
    outcomes = []
    for _, row in settled.iterrows():
        model_prob = row.get('prob') or row.get('win_prob') or row.get('proj_prob') or row.get('model_prob')
        if model_prob is None:
            continue
        probs.append(float(model_prob))
        outcome = 1.0 if (str(row.get('result')) in ('WIN','Win') or str(row.get('status')).lower()=='win') else 0.0
        outcomes.append(outcome)

    if probs:
        try:
            probs = np.array(probs)
            outcomes = np.array(outcomes)
            bins = np.linspace(0,1,11)
            inds = np.digitize(probs, bins) - 1
            bin_centers = (bins[:-1] + bins[1:]) / 2
            obs = []
            cnts = []
            for i in range(len(bins)-1):
                sel = outcomes[inds==i]
                if len(sel) == 0:
                    obs.append(np.nan)
                else:
                    obs.append(np.nanmean(sel))
                cnts.append(len(sel))

            plt.figure(figsize=(6,4))
            plt.plot(bin_centers, obs, marker='o', linestyle='-', label='Observed')
            plt.plot([0,1],[0,1], linestyle='--', color='gray', label='Perfect')
            plt.title(f"Calibration — {model_key}")
            plt.xlabel('Predicted Probability')
            plt.ylabel('Observed Frequency')
            plt.legend()
            plt.grid(alpha=0.2)
            img_cal = IMG_DIR / f"{model_key.replace('/','_')}_calibration.png"
            plt.tight_layout()
            plt.savefig(img_cal)
            plt.close()
            plots['calibration'] = img_cal
        except Exception:
            plots['calibration'] = None
    else:
        plots['calibration'] = None

    return plots, settled


def generate_report(metric_file):
    with open(metric_file, 'r') as f:
        meta = json.load(f)
    model = meta.get('model') or Path(metric_file).stem
    tracking_path = meta.get('file')
    if not tracking_path or not os.path.exists(tracking_path):
        # try to guess path from metrics filename
        tracking_candidates = list(glob.glob(str(WORKDIR / "**" / (Path(metric_file).stem.replace('_metrics','') + "*.json")), recursive=True))
        tracking_path = tracking_candidates[0] if tracking_candidates else None

    picks = []
    if tracking_path and os.path.exists(tracking_path):
        picks = load_tracking(tracking_path)

    model_key = Path(tracking_path).parent.name + '/' + Path(tracking_path).name if tracking_path else Path(metric_file).stem

    plots, settled = make_plots(model_key, tracking_path, picks)

    # Write markdown
    md = []
    md.append(f"# Model Report — {model_key}\n")
    md.append(f"**Tracking file:** {tracking_path}\n")
    md.append(f"**Total picks:** {meta.get('total_picks')} — **Settled:** {meta.get('total_settled')}\n")
    md.append(f"- **Net profit:** ${meta.get('net_profit')}\n")
    md.append(f"- **ROI:** {meta.get('roi_pct')}%\n")
    md.append(f"- **Avg profit per bet:** ${meta.get('avg_profit_per_bet')}\n")
    md.append(f"- **Avg CLV (pct points):** {meta.get('avg_clv_pct_points')}\n")
    md.append(f"- **Brier score:** {meta.get('brier_score')}\n")

    if plots and plots.get('pnl'):
        md.append(f"## P&L Curve\n![pnl]({plots['pnl'].relative_to(WORKDIR)})\n")
    if plots and plots.get('clv'):
        md.append(f"## CLV Distribution\n![clv]({plots['clv'].relative_to(WORKDIR)})\n")
    if plots and plots.get('calibration'):
        md.append(f"## Calibration Plot\n![cal]({plots['calibration'].relative_to(WORKDIR)})\n")

    # Quick suggestions (automated, basic)
    suggestions = []
    if meta.get('avg_clv_pct_points') is None:
        suggestions.append('- Add model probability field (`prob` / `win_prob`) to enable CLV calculation.')
    if meta.get('roi_pct') is None:
        suggestions.append('- Ensure `profit_loss` or `profit` is populated for settled picks.')
    if not suggestions:
        suggestions.append('- No immediate data gaps detected for basic metrics.')

    md.append('## Quick Suggestions\n')
    for s in suggestions:
        md.append(f"- {s}\n")

    out_md = OUT_DIR / (Path(metric_file).stem.replace('_metrics','') + '.md')
    with open(out_md, 'w') as f:
        f.writelines('\n'.join(md))

    return out_md


def main():
    generated = []
    for mf in METRICS_FILES:
        try:
            out = generate_report(mf)
            generated.append(out)
        except Exception as e:
            print(f"Error generating report for {mf}: {e}")

    print(f"Generated {len(generated)} reports in {OUT_DIR}")


if __name__ == '__main__':
    main()
