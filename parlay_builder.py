#!/usr/bin/env python3
"""
Parlay Builder - 3-Pick Entry Generator for DaBble & Hard Rock
--------------------------------------------------------------
Reads model outputs and best plays data to build optimal 3-leg parlays.
Generates styled HTML matching CourtSide Analytics aesthetic.
Auto-pushes to GitHub Pages.

Strategy: Correlated Edge Stacking
- Prioritizes HIGH confidence plays with large edges
- Mixes spread + total bets for diversification
- Looks for same-game correlations (e.g., blowout + under)
- Cross-references historical model performance per bet type

Run: python3 parlay_builder.py
"""

import json
import os
import csv
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ET = pytz.timezone('US/Eastern')
OUTPUT_HTML = os.path.join(SCRIPT_DIR, 'todays_parlay.html')

# Tracking sources for historical performance
TRACKING_SOURCES = [
    ('NBA Points Props', 'nba/nba_points_props_tracking.json', 'NBA', 'Props'),
    ('NBA Assists Props', 'nba/nba_assists_props_tracking.json', 'NBA', 'Props'),
    ('NBA Rebounds Props', 'nba/nba_rebounds_props_tracking.json', 'NBA', 'Props'),
    ('NBA 3PT Props', 'nba/nba_3pt_props_tracking.json', 'NBA', 'Props'),
    ('NBA PRA Props', 'nba/nba_pra_props_tracking.json', 'NBA', 'Props'),
    ('NBA P+R Props', 'nba/nba_points_rebounds_props_tracking.json', 'NBA', 'Props'),
    ('NBA P+A Props', 'nba/nba_points_assists_props_tracking.json', 'NBA', 'Props'),
    ('NBA R+A Props', 'nba/nba_rebounds_assists_props_tracking.json', 'NBA', 'Props'),
    ('NBA Main', 'nba/nba_picks_tracking.json', 'NBA', 'Spread/Total'),
    ('NCAAB', 'ncaa/ncaab_picks_tracking.json', 'NCAAB', 'Spread/Total'),
    ('CBB Points Props', 'ncaa/cbb_points_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB Assists Props', 'ncaa/cbb_assists_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB Rebounds Props', 'ncaa/cbb_rebounds_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB 3PT Props', 'ncaa/cbb_threes_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB PRA Props', 'ncaa/cbb_pra_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB P+R Props', 'ncaa/cbb_points_rebounds_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB P+A Props', 'ncaa/cbb_points_assists_props_tracking.json', 'NCAAB', 'Props'),
    ('CBB R+A Props', 'ncaa/cbb_rebounds_assists_props_tracking.json', 'NCAAB', 'Props'),
]


def now_et():
    return datetime.now(ET)


def load_json(filepath):
    full_path = os.path.join(SCRIPT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
        return data.get('picks', []) if isinstance(data, dict) else data
    except Exception:
        return []


def load_csv(filepath):
    full_path = os.path.join(SCRIPT_DIR, filepath)
    if not os.path.exists(full_path):
        return []
    try:
        with open(full_path, 'r') as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def get_model_win_rate(tracking_file):
    picks = load_json(tracking_file)
    graded = [p for p in picks if p.get('status', '').lower() in ['win', 'won', 'loss', 'lost']]
    wins = sum(1 for p in graded if p.get('status', '').lower() in ['win', 'won'])
    total = len(graded)
    return (wins / total * 100) if total > 0 else 50.0, f"{wins}-{total - wins}"


def parse_game_time(game_time_str):
    if not game_time_str:
        return None
    try:
        if 'Z' in game_time_str:
            dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(game_time_str)
        return dt.astimezone(ET)
    except Exception:
        return None


def get_nba_plays():
    """Get NBA spread/total plays from CSV."""
    rows = load_csv('nba/nba_model_output.csv')
    plays = []
    now = now_et()

    for row in rows:
        game_time = parse_game_time(row.get('commence_time', ''))
        if not game_time or game_time < now:
            continue

        # Spread play
        ats_pick = row.get('ATS Pick', '')
        spread_edge = abs(float(row.get('spread_edge', 0)))
        if 'BET' in ats_pick and 'NO BET' not in ats_pick and spread_edge >= 5:
            ai_rating = row.get('ai_rating', '')
            plays.append({
                'sport': 'NBA',
                'type': 'Spread',
                'pick': ats_pick.replace('✅ BET: ', ''),
                'edge': spread_edge,
                'explanation': row.get('ATS Explanation', ''),
                'matchup': row.get('Matchup', ''),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p'),
                'predicted_score': row.get('Predicted Score', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'is_auto_bet': row.get('is_auto_bet', '') == 'True',
                'is_fade': row.get('is_fade_team', '') == 'True',
                'ai_rating': ai_rating,
                'market_line': row.get('Market Spread', ''),
            })

        # Total play
        total_pick = row.get('Total Pick', '')
        total_edge = abs(float(row.get('total_edge', 0)))
        if 'BET' in total_pick and 'NO BET' not in total_pick and total_edge >= 5:
            plays.append({
                'sport': 'NBA',
                'type': 'Total',
                'pick': total_pick.replace('✅ BET: ', ''),
                'edge': total_edge,
                'explanation': row.get('Total Explanation', ''),
                'matchup': row.get('Matchup', ''),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p'),
                'predicted_score': row.get('Predicted Score', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'market_line': row.get('Market Total', ''),
            })

    return plays


def get_ncaab_plays():
    """Get NCAAB spread/total plays from CSV."""
    rows = load_csv('ncaa/ncaab_model_output.csv')
    plays = []
    now = now_et()

    for row in rows:
        game_time = parse_game_time(row.get('commence_time', ''))
        if not game_time or game_time < now:
            continue

        # Spread play
        ats_pick = row.get('ATS Pick', '')
        spread_edge = abs(float(row.get('spread_edge', 0)))
        if 'BET' in ats_pick and 'NO BET' not in ats_pick and spread_edge >= 5:
            plays.append({
                'sport': 'NCAAB',
                'type': 'Spread',
                'pick': ats_pick.replace('✅ BET: ', ''),
                'edge': spread_edge,
                'explanation': row.get('ATS Explanation', ''),
                'matchup': row.get('Matchup', ''),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p'),
                'predicted_score': row.get('Predicted Score', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'market_line': row.get('Market Spread', ''),
            })

        # Total play
        total_pick = row.get('Total Pick', '')
        total_edge = abs(float(row.get('total_edge', 0)))
        if 'BET' in total_pick and 'NO BET' not in total_pick and total_edge >= 5:
            plays.append({
                'sport': 'NCAAB',
                'type': 'Total',
                'pick': total_pick.replace('✅ BET: ', ''),
                'edge': total_edge,
                'explanation': row.get('Total Explanation', ''),
                'matchup': row.get('Matchup', ''),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p'),
                'predicted_score': row.get('Predicted Score', ''),
                'home_team': row.get('home_team', ''),
                'away_team': row.get('away_team', ''),
                'market_line': row.get('Market Total', ''),
            })

    return plays


def get_props_plays():
    """Get player prop plays from tracking JSON files (pending picks)."""
    plays = []
    now = now_et()

    props_sources = [
        ('NBA Points Props', 'nba/nba_points_props_tracking.json', 'NBA'),
        ('NBA Assists Props', 'nba/nba_assists_props_tracking.json', 'NBA'),
        ('NBA Rebounds Props', 'nba/nba_rebounds_props_tracking.json', 'NBA'),
        ('NBA 3PT Props', 'nba/nba_3pt_props_tracking.json', 'NBA'),
        ('NBA PRA Props', 'nba/nba_pra_props_tracking.json', 'NBA'),
        ('NBA P+R Props', 'nba/nba_points_rebounds_props_tracking.json', 'NBA'),
        ('NBA P+A Props', 'nba/nba_points_assists_props_tracking.json', 'NBA'),
        ('NBA R+A Props', 'nba/nba_rebounds_assists_props_tracking.json', 'NBA'),
        ('CBB Points Props', 'ncaa/cbb_points_props_tracking.json', 'NCAAB'),
        ('CBB Assists Props', 'ncaa/cbb_assists_props_tracking.json', 'NCAAB'),
        ('CBB Rebounds Props', 'ncaa/cbb_rebounds_props_tracking.json', 'NCAAB'),
        ('CBB 3PT Props', 'ncaa/cbb_threes_props_tracking.json', 'NCAAB'),
        ('CBB PRA Props', 'ncaa/cbb_pra_props_tracking.json', 'NCAAB'),
        ('CBB P+R Props', 'ncaa/cbb_points_rebounds_props_tracking.json', 'NCAAB'),
        ('CBB P+A Props', 'ncaa/cbb_points_assists_props_tracking.json', 'NCAAB'),
        ('CBB R+A Props', 'ncaa/cbb_rebounds_assists_props_tracking.json', 'NCAAB'),
    ]

    for model_name, filepath, sport in props_sources:
        picks = load_json(filepath)
        win_rate, record = get_model_win_rate(filepath)

        for p in picks:
            if p.get('status', 'pending').lower() != 'pending':
                continue

            game_time = parse_game_time(p.get('game_time') or p.get('game_date'))
            if not game_time or game_time < now:
                continue

            edge = abs(p.get('edge', 0))
            ai_score = p.get('ai_score', 0)
            if edge < 3 or ai_score < 7:
                continue

            plays.append({
                'sport': sport,
                'type': 'Prop',
                'pick': f"{p.get('player', 'Unknown')} {p.get('bet_type', '')} {p.get('prop_line', p.get('line', ''))}",
                'edge': edge,
                'explanation': f"{model_name} | Record: {record} ({win_rate:.0f}%) | AI Score: {ai_score}",
                'matchup': p.get('matchup', p.get('opponent', '')),
                'game_time': game_time,
                'game_time_str': game_time.strftime('%a %I:%M %p'),
                'predicted_score': '',
                'home_team': '',
                'away_team': '',
                'market_line': p.get('prop_line', p.get('line', '')),
                'player': p.get('player', ''),
                'model': model_name,
                'model_win_rate': win_rate,
                'model_record': record,
                'ai_score': ai_score,
                'season_avg': p.get('season_avg', 0),
                'recent_avg': p.get('recent_avg', 0),
            })

    return plays


def get_mlb_plays():
    """Get MLB player prop plays from tracking JSON."""
    picks = load_json('mlb/mlb_master_model_tracking.json')
    win_rate, record = get_model_win_rate('mlb/mlb_master_model_tracking.json')
    plays = []
    now = now_et()
    today_date = now.strftime('%Y%m%d')
    tomorrow_date = (now + timedelta(days=1)).strftime('%Y%m%d')

    for p in picks:
        if p.get('status', 'pending').lower() != 'pending':
            continue

        # MLB picks have no game_time — extract date from pick ID (e.g. K_Name_20260516)
        pick_id = p.get('id', '')
        id_date = pick_id.split('_')[-1] if pick_id else ''
        if id_date not in (today_date, tomorrow_date):
            continue

        # MLB edge is stored as a fraction (0.09 = 9%), scale to match NBA's percent units
        edge = abs(p.get('edge', 0)) * 100
        if edge < 3:
            continue

        selection = p.get('selection', 'Unknown')
        line = p.get('line', '')
        pick_str = f"{selection} {line}" if line else selection
        bet_type = p.get('type', '').replace('Player Props - ', '').replace('First 5 Innings ', 'F5 ')
        game_date_str = f"{id_date[:4]}-{id_date[4:6]}-{id_date[6:]}" if len(id_date) == 8 else ''

        plays.append({
            'sport': 'MLB',
            'type': 'Prop',
            'pick': pick_str,
            'edge': edge,
            'explanation': f"MLB Master | {record} ({win_rate:.0f}%) | {bet_type} | {p.get('prob', 0):.1%} prob",
            'matchup': p.get('matchup', ''),
            'game_time': None,
            'game_time_str': game_date_str,
            'predicted_score': '',
            'home_team': '',
            'away_team': '',
            'market_line': line,
            'player': selection,
            'model': 'MLB Master',
            'model_win_rate': win_rate,
            'model_record': record,
            'ai_score': p.get('score', 0),
            'season_avg': 0,
            'recent_avg': 0,
        })

    return plays


def find_correlations(plays):
    """Find correlated plays from the same game (e.g., team covers + under)."""
    by_game = defaultdict(list)
    for p in plays:
        key = p['matchup']
        by_game[key].append(p)

    correlated = []
    for matchup, game_plays in by_game.items():
        if len(game_plays) >= 2:
            spreads = [p for p in game_plays if p['type'] == 'Spread']
            totals = [p for p in game_plays if p['type'] == 'Total']
            if spreads and totals:
                best_spread = max(spreads, key=lambda x: x['edge'])
                best_total = max(totals, key=lambda x: x['edge'])
                combined_edge = best_spread['edge'] + best_total['edge']
                correlated.append({
                    'matchup': matchup,
                    'spread': best_spread,
                    'total': best_total,
                    'combined_edge': combined_edge,
                })

    return sorted(correlated, key=lambda x: x['combined_edge'], reverse=True)


def build_parlays(all_plays, correlations, max_entries=5):
    """Build up to max_entries distinct 3-pick parlay entries using different strategies."""
    if len(all_plays) < 3:
        return []

    ranked = sorted(all_plays, key=lambda x: x['edge'], reverse=True)
    entries = []
    used_combos = set()  # Track pick combos to avoid duplicates

    def picks_key(picks):
        return tuple(sorted(f"{p['matchup']}_{p['type']}_{p['pick']}" for p in picks))

    def add_entry(picks, strategy):
        key = picks_key(picks)
        if key not in used_combos and len(picks) == 3:
            used_combos.add(key)
            entries.append({'picks': list(picks), 'strategy': strategy})

    # Entry 1: Correlated Edge Stack (spread + total from same game + best standalone)
    if correlations:
        best_corr = correlations[0]
        parlay = [best_corr['spread'], best_corr['total']]
        for p in ranked:
            if p['matchup'] != best_corr['matchup']:
                parlay.append(p)
                break
        add_entry(parlay, "Correlated Edge Stack")

    # Entry 2: Diversified Top Edge (top 3 from different games)
    parlay = []
    used_matchups = set()
    for p in ranked:
        if p['matchup'] not in used_matchups:
            parlay.append(p)
            used_matchups.add(p['matchup'])
            if len(parlay) == 3:
                break
    add_entry(parlay, "Diversified Top Edge")

    # Entry 3: Props-Heavy (top 3 props by edge)
    props_only = [p for p in ranked if p['type'] == 'Prop']
    if len(props_only) >= 3:
        parlay = []
        used_players = set()
        for p in props_only:
            player_key = p.get('player', p['pick'])
            if player_key not in used_players:
                parlay.append(p)
                used_players.add(player_key)
                if len(parlay) == 3:
                    break
        add_entry(parlay, "Props Power Play")

    # Entry 4: Mixed (1 spread/total + 2 props, or 2 spread/total + 1 prop)
    spreads_totals = [p for p in ranked if p['type'] in ('Spread', 'Total')]
    if spreads_totals and len(props_only) >= 2:
        parlay = [spreads_totals[0]]
        used_players = set()
        for p in props_only:
            player_key = p.get('player', p['pick'])
            if player_key not in used_players:
                parlay.append(p)
                used_players.add(player_key)
                if len(parlay) == 3:
                    break
        add_entry(parlay, "Spread + Props Mix")
    elif len(spreads_totals) >= 2 and props_only:
        parlay = spreads_totals[:2] + [props_only[0]]
        add_entry(parlay, "Lines + Prop Mix")

    # Entry 5: Second-best correlated or AI Score weighted
    if len(correlations) >= 2:
        corr = correlations[1]
        parlay = [corr['spread'], corr['total']]
        for p in ranked:
            if p['matchup'] != corr['matchup']:
                parlay.append(p)
                break
        add_entry(parlay, "Correlated Edge Stack #2")

    # Entry 5 alt: High AI Score picks (props with best ai_score)
    if len(entries) < max_entries:
        ai_ranked = sorted(
            [p for p in all_plays if p.get('ai_score', 0) > 0],
            key=lambda x: x.get('ai_score', 0), reverse=True
        )
        if len(ai_ranked) >= 3:
            parlay = []
            used_players = set()
            for p in ai_ranked:
                player_key = p.get('player', p['pick'])
                if player_key not in used_players:
                    parlay.append(p)
                    used_players.add(player_key)
                    if len(parlay) == 3:
                        break
            add_entry(parlay, "AI Confidence Play")

    # Entry fallback: Next-best diversified (skip plays already heavily used)
    if len(entries) < 3 and len(ranked) >= 6:
        parlay = []
        used_matchups = set()
        for p in ranked[3:]:  # Skip top 3
            if p['matchup'] not in used_matchups:
                parlay.append(p)
                used_matchups.add(p['matchup'])
                if len(parlay) == 3:
                    break
        add_entry(parlay, "Value Picks")

    return entries[:max_entries]


def get_sport_badge_color(sport):
    if sport == 'NBA':
        return '#60a5fa'
    elif sport == 'NCAAB':
        return '#f59e0b'
    elif sport == 'MLB':
        return '#4ade80'
    else:
        return '#a78bfa'


def get_type_icon(bet_type):
    if bet_type == 'Spread':
        return '📐'
    elif bet_type == 'Total':
        return '📊'
    elif bet_type == 'Prop':
        return '🎯'
    return '📋'


def get_strategy_style(strategy):
    """Get color and icon for a strategy."""
    if 'Correlated' in strategy:
        return '#ff6b35', '🔗'
    elif 'Diversified' in strategy:
        return '#4ade80', '🎲'
    elif 'Props' in strategy:
        return '#a78bfa', '🎯'
    elif 'Mix' in strategy:
        return '#f59e0b', '🔀'
    elif 'AI' in strategy:
        return '#22d3ee', '🤖'
    elif 'Value' in strategy:
        return '#f87171', '💎'
    else:
        return '#60a5fa', '📈'


def build_entry_html(entry_num, parlay, strategy):
    """Build HTML for a single parlay entry card."""
    strat_color, strat_icon = get_strategy_style(strategy)
    total_edge = sum(leg['edge'] for leg in parlay)

    leg_cards = ""
    for i, leg in enumerate(parlay, 1):
        sport_color = get_sport_badge_color(leg['sport'])
        type_icon = get_type_icon(leg['type'])
        pick_color = '#4ade80' if 'OVER' in leg['pick'].upper() else '#f87171' if 'UNDER' in leg['pick'].upper() else '#ffffff'

        max_edge = max(l['edge'] for l in parlay)
        edge_pct = min((leg['edge'] / max_edge) * 100, 100) if max_edge > 0 else 50

        predicted_html = ""
        if leg.get('predicted_score'):
            predicted_html = f'<div class="leg-predicted">Model: {leg["predicted_score"]}</div>'

        explanation_html = ""
        if leg.get('explanation'):
            explanation_html = f'<div class="leg-explanation">{leg["explanation"][:100]}</div>'

        corr_tag = ""
        if i <= 2 and 'Correlated' in strategy:
            corr_tag = '<span class="tag tag-correlated">🔗 CORRELATED</span>'

        leg_cards += f'''
            <div class="leg-card">
                <div class="leg-number">LEG {i}</div>
                <div class="leg-body">
                    <div class="leg-top-row">
                        <span class="sport-badge" style="background: {sport_color}20; color: {sport_color}; border: 1px solid {sport_color}40;">{leg['sport']}</span>
                        <span class="type-badge">{type_icon} {leg['type'].upper()}</span>
                        {corr_tag}
                    </div>
                    <div class="leg-pick" style="color: {pick_color};">{leg['pick']}</div>
                    <div class="leg-matchup">{leg['matchup']}</div>
                    <div class="leg-time">{leg['game_time_str']}</div>
                    {predicted_html}
                    {explanation_html}
                    <div class="edge-section">
                        <div class="edge-label">EDGE</div>
                        <div class="edge-bar-container">
                            <div class="edge-bar" style="width: {edge_pct}%;"></div>
                        </div>
                        <div class="edge-value">+{leg['edge']:.1f}</div>
                    </div>
                </div>
            </div>'''

    return f'''
        <div class="entry-section">
            <div class="entry-header">
                <div class="entry-number">ENTRY {entry_num}</div>
                <span class="strategy-badge" style="background: {strat_color}15; color: {strat_color}; border: 1px solid {strat_color}40;">{strat_icon} {strategy}</span>
                <span class="entry-edge">Combined Edge: +{total_edge:.1f}</span>
            </div>
            <div class="legs-container">
                {leg_cards}
            </div>
        </div>'''


def generate_html(entries, all_plays, all_plays_count):
    """Generate styled HTML matching CourtSide Analytics aesthetic."""
    now = now_et()
    timestamp = now.strftime('%Y-%m-%d %I:%M %p ET')
    date_display = now.strftime('%A, %B %d')

    # Stats
    all_sports = set()
    for entry in entries:
        for leg in entry['picks']:
            all_sports.add(leg['sport'])

    # Build all entry cards
    entries_html = ""
    if entries:
        for idx, entry in enumerate(entries, 1):
            entries_html += build_entry_html(idx, entry['picks'], entry['strategy'])
    else:
        entries_html = '''
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <div class="empty-text">Not enough qualifying plays today</div>
            <div class="empty-sub">Check back when the slate is bigger</div>
        </div>
        '''

    # Runner-up plays (picks not used in any entry)
    runner_up_html = ""
    if entries and all_plays:
        used_picks = set()
        for entry in entries:
            for leg in entry['picks']:
                used_picks.add(f"{leg['matchup']}_{leg['type']}_{leg['pick']}")
        runners = [p for p in sorted(all_plays, key=lambda x: x['edge'], reverse=True)
                    if f"{p['matchup']}_{p['type']}_{p['pick']}" not in used_picks][:5]

        if runners:
            rows = ""
            for r in runners:
                sport_color = get_sport_badge_color(r['sport'])
                rows += f'''
                <tr>
                    <td><span class="sport-badge-sm" style="background: {sport_color}20; color: {sport_color};">{r['sport']}</span></td>
                    <td class="runner-pick">{r['pick']}</td>
                    <td class="runner-matchup">{r['matchup']}</td>
                    <td class="runner-type">{r['type']}</td>
                    <td class="runner-edge">+{r['edge']:.1f}</td>
                </tr>
                '''

            runner_up_html = f'''
            <div class="runners-section">
                <div class="section-title">📋 Other Notable Plays</div>
                <table class="runners-table">
                    <thead>
                        <tr>
                            <th>Sport</th>
                            <th>Pick</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Edge</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
            '''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Parlay Builder &bull; CourtSide Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --accent-orange: #ff6b35;
            --border-color: #333333;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-main);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            flex-wrap: wrap;
            gap: 15px;
        }}

        .header-left {{
            display: flex;
            flex-direction: column;
        }}

        h1 {{
            font-size: 24px;
            font-weight: 800;
            margin: 0 0 5px 0;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 14px;
        }}

        .timestamp {{
            background: var(--bg-card-secondary);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }}

        /* Stats Banner */
        .stats-banner {{
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
            justify-content: center;
        }}

        .stat-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px 25px;
            text-align: center;
            min-width: 160px;
            flex: 1;
        }}

        .stat-box-label {{
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
            font-weight: 600;
        }}

        .stat-box-value {{
            font-size: 22px;
            font-weight: 800;
        }}

        .stat-box-sub {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }}

        /* Entry Section */
        .entry-section {{
            margin-bottom: 30px;
        }}

        .entry-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }}

        .entry-number {{
            font-size: 18px;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: 1px;
        }}

        .strategy-badge {{
            font-size: 12px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 8px;
            letter-spacing: 0.3px;
        }}

        .entry-edge {{
            font-size: 13px;
            font-weight: 700;
            color: var(--accent-green);
            margin-left: auto;
        }}

        /* Leg Cards */
        .legs-container {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .leg-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .leg-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
            border-color: #444;
        }}

        .leg-number {{
            background: var(--bg-card-secondary);
            padding: 20px 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 800;
            color: var(--text-secondary);
            letter-spacing: 1px;
            writing-mode: vertical-lr;
            text-orientation: mixed;
            min-width: 50px;
        }}

        .leg-body {{
            padding: 18px 22px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .leg-top-row {{
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }}

        .sport-badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }}

        .sport-badge-sm {{
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .type-badge {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            background: var(--bg-card-secondary);
            padding: 3px 10px;
            border-radius: 6px;
        }}

        .tag-correlated {{
            font-size: 10px;
            font-weight: 700;
            color: var(--accent-orange);
            background: rgba(255, 107, 53, 0.15);
            padding: 3px 8px;
            border-radius: 6px;
        }}

        .leg-pick {{
            font-size: 20px;
            font-weight: 800;
            line-height: 1.2;
        }}

        .leg-matchup {{
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .leg-time {{
            font-size: 12px;
            color: var(--text-secondary);
            background: var(--bg-card-secondary);
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            width: fit-content;
        }}

        .leg-predicted {{
            font-size: 13px;
            color: var(--accent-blue);
            font-weight: 500;
        }}

        .leg-explanation {{
            font-size: 12px;
            color: var(--text-secondary);
            font-style: italic;
        }}

        .edge-section {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 6px;
        }}

        .edge-label {{
            font-size: 10px;
            font-weight: 700;
            color: var(--text-secondary);
            letter-spacing: 1px;
            min-width: 35px;
        }}

        .edge-bar-container {{
            flex: 1;
            height: 8px;
            background: var(--bg-card-secondary);
            border-radius: 4px;
            overflow: hidden;
        }}

        .edge-bar {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-green), #22d3ee);
            border-radius: 4px;
            transition: width 0.5s ease;
        }}

        .edge-value {{
            font-size: 14px;
            font-weight: 800;
            color: var(--accent-green);
            min-width: 50px;
            text-align: right;
        }}

        /* Instructions */
        .instructions {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px 25px;
            margin-bottom: 25px;
        }}

        .instructions-title {{
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 12px;
            color: var(--accent-blue);
        }}

        .instructions ol {{
            list-style: none;
            counter-reset: steps;
            padding: 0;
        }}

        .instructions li {{
            counter-increment: steps;
            font-size: 14px;
            color: var(--text-secondary);
            padding: 6px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .instructions li::before {{
            content: counter(steps);
            background: var(--bg-card-secondary);
            color: var(--text-primary);
            font-weight: 700;
            font-size: 12px;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        /* Runners */
        .runners-section {{
            margin-bottom: 25px;
        }}

        .section-title {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 12px;
        }}

        .runners-table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }}

        .runners-table th {{
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 10px 12px;
            text-align: left;
            background: var(--bg-card-secondary);
            font-weight: 600;
        }}

        .runners-table td {{
            padding: 10px 12px;
            font-size: 13px;
            border-top: 1px solid var(--border-color);
        }}

        .runner-pick {{
            font-weight: 600;
            color: var(--text-primary);
        }}

        .runner-matchup {{
            color: var(--text-secondary);
        }}

        .runner-type {{
            color: var(--text-secondary);
        }}

        .runner-edge {{
            font-weight: 700;
            color: var(--accent-green);
        }}

        /* Empty State */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border-color);
        }}

        .empty-icon {{ font-size: 48px; margin-bottom: 15px; }}
        .empty-text {{ font-size: 18px; font-weight: 700; margin-bottom: 5px; }}
        .empty-sub {{ font-size: 14px; color: var(--text-secondary); }}

        /* Divider */
        .entry-divider {{
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 10px 0 25px 0;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 12px;
            padding: 20px 0;
            border-top: 1px solid var(--border-color);
        }}

        .footer a {{
            color: var(--accent-blue);
            text-decoration: none;
        }}

        /* Mobile */
        @media (max-width: 600px) {{
            .leg-card {{ flex-direction: column; }}
            .leg-number {{
                writing-mode: horizontal-tb;
                padding: 10px;
                min-width: unset;
            }}
            .stats-banner {{ flex-direction: column; }}
            .stat-box {{ min-width: unset; }}
            header {{ flex-direction: column; align-items: center; text-align: center; }}
            .runners-table {{ font-size: 12px; }}
            .runners-table th, .runners-table td {{ padding: 8px 6px; }}
            .entry-header {{ flex-direction: column; align-items: flex-start; }}
            .entry-edge {{ margin-left: 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-left">
                <h1>🎰 Parlay Builder</h1>
                <div class="subtitle">{date_display} &bull; 3-Pick Entries for DaBble &amp; Hard Rock</div>
            </div>
            <div class="timestamp">Generated: {timestamp}</div>
        </header>

        <div class="stats-banner">
            <div class="stat-box">
                <div class="stat-box-label">Entries</div>
                <div class="stat-box-value">{len(entries)}</div>
                <div class="stat-box-sub">3-pick parlays</div>
            </div>
            <div class="stat-box">
                <div class="stat-box-label">Plays Analyzed</div>
                <div class="stat-box-value">{all_plays_count}</div>
                <div class="stat-box-sub">{', '.join(sorted(all_sports)) if all_sports else 'N/A'}</div>
            </div>
            <div class="stat-box">
                <div class="stat-box-label">Best Combined Edge</div>
                <div class="stat-box-value" style="color: var(--accent-green);">+{max((sum(l['edge'] for l in e['picks']) for e in entries), default=0):.1f}</div>
            </div>
        </div>

        {entries_html}

        {'<div class="instructions"><div class="instructions-title">How to Enter</div><ol><li>Open DaBble or Hard Rock Bet</li><li>Choose an entry above and add its 3 legs to your bet slip</li><li>Select 3-Pick Parlay entry type</li><li>Set your unit size and confirm</li></ol></div>' if entries else ''}

        {runner_up_html}

        <div class="footer">
            CourtSide Analytics &bull; <a href="https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/best_plays.html">Best Plays</a> &bull; <a href="https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/dashboard.html">Dashboard</a> &bull; <a href="https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/analytics_dashboard.html">Analytics</a>
        </div>
    </div>
</body>
</html>'''

    return html


def format_console_output(entries, all_plays_count):
    """Format all parlay entries as clean console output."""
    now = now_et()
    date_str = now.strftime('%A, %B %d %Y')

    output = []
    output.append("")
    output.append("=" * 60)
    output.append(f"  PARLAY BUILDER - {date_str}")
    output.append(f"  {len(entries)} entries | {all_plays_count} plays analyzed")
    output.append("=" * 60)

    if not entries:
        output.append("")
        output.append("  Not enough qualifying plays today.")
        output.append("  Wait for a bigger slate!")
        output.append("")
        return "\n".join(output)

    for entry_num, entry in enumerate(entries, 1):
        parlay = entry['picks']
        strategy = entry['strategy']
        total_edge = sum(leg['edge'] for leg in parlay)

        output.append("")
        output.append(f"  ┌─ ENTRY {entry_num}: {strategy.upper()}")
        output.append(f"  │")

        for i, leg in enumerate(parlay, 1):
            output.append(f"  │  LEG {i}: {leg['sport']} {leg['type'].upper()}")
            output.append(f"  │  Pick:  {leg['pick']}")
            output.append(f"  │  Game:  {leg['matchup']} | {leg['game_time_str']}")
            output.append(f"  │  Edge:  +{leg['edge']:.1f}")
            if i < len(parlay):
                output.append(f"  │")

        output.append(f"  │")
        output.append(f"  └─ COMBINED EDGE: +{total_edge:.1f}")

    output.append("")
    output.append("=" * 60)
    output.append("")

    return "\n".join(output)


def push_to_git():
    """Push todays_parlay.html to git."""
    try:
        print("\n🚀 Pushing parlay to GitHub...")
        timestamp = now_et().strftime('%Y-%m-%d %H:%M')

        subprocess.run(['git', 'add', 'todays_parlay.html'],
                       cwd=SCRIPT_DIR, check=True, capture_output=True)

        result = subprocess.run(
            ['git', 'commit', '-m', f'Update parlay - {timestamp}'],
            cwd=SCRIPT_DIR, capture_output=True, text=True
        )

        if result.returncode == 0:
            subprocess.run(['git', 'push', 'origin', 'main'],
                           cwd=SCRIPT_DIR, check=True, capture_output=True)
            print("✅ Pushed to GitHub!")
        elif 'nothing to commit' in (result.stdout + result.stderr):
            print("ℹ️  No changes to push")
        else:
            print(f"⚠️  Git commit issue: {result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git push failed: {e}")
    except Exception as e:
        print(f"⚠️  Git error: {e}")


def main():
    print("\n🎰 Parlay Builder")
    print("=" * 50)
    print("Scanning model outputs...")

    # Gather all plays
    nba = get_nba_plays()
    ncaab = get_ncaab_plays()
    props = get_props_plays()
    mlb = get_mlb_plays()

    print(f"  NBA spreads/totals: {len(nba)} qualifying plays")
    print(f"  NCAAB spreads/totals: {len(ncaab)} qualifying plays")
    print(f"  NBA/NCAAB player props: {len(props)} qualifying plays")
    print(f"  MLB props: {len(mlb)} qualifying plays")

    all_plays = nba + ncaab + props + mlb
    print(f"  Total: {len(all_plays)} plays")

    if not all_plays:
        print("\nNo qualifying plays found. Thin slate today!")
        print("Run your models first: bash run_all_models.sh")
        # Still generate empty-state HTML
        html = generate_html([], [], 0)
        with open(OUTPUT_HTML, 'w') as f:
            f.write(html)
        print(f"✅ Created: {OUTPUT_HTML}")
        push_to_git()
        return

    # Find correlations
    correlations = find_correlations(all_plays)
    if correlations:
        print(f"\n  Found {len(correlations)} correlated game(s)")

    # Build parlays (up to 5 entries)
    entries = build_parlays(all_plays, correlations, max_entries=5)
    print(f"\n  Built {len(entries)} parlay entries")

    # Console output
    console = format_console_output(entries, len(all_plays))
    print(console)

    # Generate HTML
    print("📄 Generating HTML...")
    html = generate_html(entries, all_plays, len(all_plays))
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    print(f"✅ Created: {OUTPUT_HTML}")

    # Push to git
    push_to_git()

    # Print link
    print(f"\n🔗 Live: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/todays_parlay.html")


if __name__ == "__main__":
    main()
