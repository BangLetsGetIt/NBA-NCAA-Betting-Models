#!/usr/bin/env python3
"""
Automated NBA Pick Results Updater
Fetches actual game scores from ESPN API and updates pick statuses automatically
"""

import json
import os
from datetime import datetime, timezone
import requests
import time

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_tracking():
    """Load tracking data"""
    tracking_file = 'nba_picks_tracking.json'

    if not os.path.exists(tracking_file):
        print(f"{Colors.RED}❌ No tracking file found: {tracking_file}{Colors.END}")
        return None

    with open(tracking_file, 'r') as f:
        return json.load(f)

def save_tracking(tracking_data):
    """Save tracking data"""
    with open('nba_picks_tracking.json', 'w') as f:
        json.dump(tracking_data, f, indent=2)
    print(f"{Colors.GREEN}✅ Tracking data saved{Colors.END}")

def fetch_game_scores(game_date_str):
    """
    Fetch game scores for a specific date using ESPN API
    game_date_str should be in format: YYYY-MM-DD
    Returns dict: {(home_team, away_team): (home_score, away_score)}
    """
    try:
        # ESPN API uses YYYYMMDD format
        date_obj = datetime.strptime(game_date_str, '%Y-%m-%d')
        api_date = date_obj.strftime('%Y%m%d')

        print(f"{Colors.CYAN}Fetching scores from ESPN for {game_date_str}...{Colors.END}")

        # ESPN NBA Scoreboard API
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={api_date}'
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"{Colors.RED}❌ ESPN API returned status {response.status_code}{Colors.END}")
            return {}

        data = response.json()
        events = data.get('events', [])

        # Build scores dict
        scores = {}
        final_games = 0

        for event in events:
            # Check if game is final
            status = event.get('status', {}).get('type', {}).get('description', '')

            # Only include completed games
            if 'final' not in status.lower():
                continue

            final_games += 1
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])

            if len(competitors) >= 2:
                # Find home and away teams
                away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
                home = next((c for c in competitors if c.get('homeAway') == 'home'), None)

                if away and home:
                    away_team = away.get('team', {}).get('displayName', '')
                    home_team = home.get('team', {}).get('displayName', '')
                    away_score = int(away.get('score', 0))
                    home_score = int(home.get('score', 0))

                    scores[(home_team, away_team)] = (home_score, away_score)

        print(f"{Colors.GREEN}✅ Found {final_games} completed games{Colors.END}")
        return scores

    except Exception as e:
        print(f"{Colors.RED}❌ Error fetching scores: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
        return {}

def normalize_team_name(team_name):
    """Normalize team names for matching"""
    # Extract just the team city/name part
    name = team_name.strip()

    # Common normalizations
    normalizations = {
        'LA Clippers': 'Los Angeles Clippers',
        'LA Lakers': 'Los Angeles Clippers',
        'Blazers': 'Trail Blazers',
        'Sixers': '76ers',
    }

    for old, new in normalizations.items():
        if old in name:
            name = name.replace(old, new)

    return name

def find_game_score(pick, scores_dict):
    """Find the score for a pick's game from the scores dictionary"""
    home_team = normalize_team_name(pick['home_team'])
    away_team = normalize_team_name(pick['away_team'])

    # Try to find in scores dict with various team name formats
    for (h, a), (h_score, a_score) in scores_dict.items():
        h_norm = normalize_team_name(str(h))
        a_norm = normalize_team_name(str(a))

        # Check if teams match (try different substring matches)
        if (home_team in h_norm or h_norm in home_team) and \
           (away_team in a_norm or a_norm in away_team):
            return h_score, a_score

    return None, None

def calculate_pick_result(pick, home_score, away_score):
    """Calculate win/loss/push for a pick given the actual scores"""

    if pick['pick_type'] == 'Spread':
        actual_spread = home_score - away_score  # Positive if home won by more
        market_line = pick['market_line']

        # Determine which team we picked
        pick_text = pick['pick'].upper()
        if pick['home_team'].upper() in pick_text:
            # We picked home team with the spread
            cover_margin = actual_spread - market_line
        else:
            # We picked away team with the spread
            cover_margin = -actual_spread - market_line

        if abs(cover_margin) < 0.5:
            return 'Push', 0
        elif cover_margin > 0:
            return 'Win', 91  # Standard -110 payout
        else:
            return 'Loss', -100

    elif pick['pick_type'] == 'Total':
        actual_total = home_score + away_score
        market_total = pick['market_line']

        if 'OVER' in pick['pick'].upper():
            diff = actual_total - market_total
            if abs(diff) < 0.5:
                return 'Push', 0
            elif diff > 0:
                return 'Win', 91
            else:
                return 'Loss', -100
        else:  # UNDER
            diff = market_total - actual_total
            if abs(diff) < 0.5:
                return 'Push', 0
            elif diff > 0:
                return 'Win', 91
            else:
                return 'Loss', -100

    return None, 0

def update_results():
    """Main function to update pick results"""

    print(f"\n{Colors.BOLD}{Colors.CYAN}🏀 NBA RESULTS UPDATER 🏀{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    # Load tracking data
    tracking_data = load_tracking()
    if not tracking_data:
        return

    # Find pending picks
    pending = [p for p in tracking_data['picks'] if p['status'] == 'Pending']

    if not pending:
        print(f"{Colors.GREEN}✅ No pending picks to update!{Colors.END}\n")
        return

    print(f"{Colors.CYAN}Found {len(pending)} pending picks{Colors.END}\n")

    # Group pending picks by game date (in ET timezone)
    picks_by_date = {}
    now = datetime.now(timezone.utc)

    for pick in pending:
        game_date = pick['game_date']

        # Check if game is in the past
        game_datetime = datetime.fromisoformat(game_date.replace('Z', '+00:00'))

        # Only process games that started more than 3 hours ago (to ensure they're finished)
        hours_since_game = (now - game_datetime).total_seconds() / 3600

        if hours_since_game > 3:
            # Convert to ET timezone for NBA API (which uses ET)
            from datetime import timedelta
            et_offset = timedelta(hours=-5)
            et_tz = timezone(et_offset)
            et_time = game_datetime.astimezone(et_tz)
            date_only = et_time.strftime('%Y-%m-%d')

            if date_only not in picks_by_date:
                picks_by_date[date_only] = []
            picks_by_date[date_only].append(pick)

    if not picks_by_date:
        print(f"{Colors.YELLOW}No finished games to update yet.{Colors.END}\n")
        return

    print(f"{Colors.CYAN}Found {len(picks_by_date)} game dates with finished games{Colors.END}\n")

    updated_count = 0

    # Process each date
    for game_date, date_picks in picks_by_date.items():
        print(f"\n{Colors.BOLD}Processing games from {game_date}{Colors.END}")

        # Fetch scores for this date
        scores = fetch_game_scores(game_date)

        if not scores:
            print(f"{Colors.YELLOW}⚠️  No scores found for {game_date}, skipping...{Colors.END}")
            continue

        # Update each pick for this date
        for pick in date_picks:
            home_score, away_score = find_game_score(pick, scores)

            if home_score is None or away_score is None:
                print(f"{Colors.YELLOW}⚠️  Could not find score for: {pick['matchup']}{Colors.END}")
                continue

            # Calculate result
            result, profit = calculate_pick_result(pick, home_score, away_score)

            if result is None:
                print(f"{Colors.RED}❌ Could not calculate result for: {pick['matchup']}{Colors.END}")
                continue

            # Update the pick
            pick['actual_home_score'] = home_score
            pick['actual_away_score'] = away_score
            pick['result'] = result
            pick['status'] = result
            pick['profit_loss'] = profit

            # Update summary
            tracking_data['summary']['pending'] -= 1
            if result == 'Win':
                tracking_data['summary']['wins'] += 1
                result_symbol = f"{Colors.GREEN}✅ WIN{Colors.END}"
            elif result == 'Loss':
                tracking_data['summary']['losses'] += 1
                result_symbol = f"{Colors.RED}❌ LOSS{Colors.END}"
            else:
                tracking_data['summary']['pushes'] += 1
                result_symbol = f"{Colors.YELLOW}➖ PUSH{Colors.END}"

            print(f"  {result_symbol}: {pick['matchup']} ({home_score}-{away_score}) - {pick['pick_type']}: {pick['pick']}")
            updated_count += 1

    # Save updates
    if updated_count > 0:
        save_tracking(tracking_data)

        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}UPDATED {updated_count} PICK(S){Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

        # Show summary
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        pending_remaining = tracking_data['summary']['pending']

        print(f"{Colors.CYAN}Current Record:{Colors.END}")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        print(f"  Pushes: {pushes}")
        print(f"  Pending: {pending_remaining}")

        if (wins + losses) > 0:
            win_rate = (wins / (wins + losses)) * 100
            print(f"  Win Rate: {win_rate:.1f}%")

        print(f"\n{Colors.GREEN}✅ Now run the tracking dashboard script to regenerate the HTML!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}No picks were updated{Colors.END}")

    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    try:
        update_results()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Cancelled by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
