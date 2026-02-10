import json
import os

TRACKING_FILE = "/Users/rico/Dev/sports-models/ncaa/ncaab_picks_tracking.json"
TARGET_TEAM = "Prairie View Panthers"

def analyze_record():
    if not os.path.exists(TRACKING_FILE):
        print(f"File not found: {TRACKING_FILE}")
        return

    with open(TRACKING_FILE, 'r') as f:
        data = json.load(f)

    picks = data.get('picks', [])
    
    print(f"Analysis for {TARGET_TEAM} (Spread/ML Only)")
    print("-" * 60)

    # Storage for details
    fav_games = []
    dog_games = []

    for p in picks:
        # Filter for Spread/ML only (exclude totals)
        if p.get('pick_type') == 'total':
            continue
            
        home = p.get('home_team', '')
        away = p.get('away_team', '')
        
        # Check if target team is involved
        if TARGET_TEAM not in [home, away]:
            continue

        pick_text = p.get('pick_text', '')
        actual_score = p.get('actual_score', 'N/A')
        status = p.get('status', '').lower()
        if status not in ['win', 'loss', 'push']:
            if p.get('result') == 'WIN': status = 'win'
            elif p.get('result') == 'LOSS': status = 'loss'
            elif p.get('result') == 'PUSH': status = 'push'

        # Determine Opponent
        opponent = home if away == TARGET_TEAM else away

        # Determine Probable Line from pick_text to identify Fav/Dog
        # If explicitly betting ON Prairie View
        is_bet_on_target = TARGET_TEAM in pick_text
        
        # Simple heuristic for Fav/Dog based on pick text
        # If "+" is in the line for the target team, they are dogs. If "-" they are favs.
        # But pick_text might be for the Opponent.
        
        is_dog = False
        is_fav = False
        
        line_str = "N/A"
        try:
            # Extract line number from text roughly
            import re
            match = re.search(r'([-+]\d+\.?\d*)', pick_text)
            if match:
                line_str = match.group(1)
                line_val = float(line_str)
                
                if is_bet_on_target:
                    if line_val > 0: is_dog = True
                    else: is_fav = True
                else:
                    # Bet is on Opponent
                    # If Opponent is +5, Target is -5 (Fav)
                    # If Opponent is -5, Target is +5 (Dog)
                    if line_val > 0: is_fav = True
                    else: is_dog = True
            else:
                # Fallback if no spread number found (e.g. ML)
                if "ML" in pick_text or "Moneyline" in pick_text:
                    # Assume Dog if plus money? Hard to tell without odds.
                    # Defaulting to Dog for now as safe assumption for PVAMU vs major teams, 
                    # but let's label as "Unknown" if needed.
                    pass
        except:
            pass

        game_info = {
            'opponent': opponent,
            'result': status.upper(),
            'score': actual_score,
            'line': line_str,
            'bet_on': "PVAMU" if is_bet_on_target else opponent
        }

        if is_dog:
            dog_games.append(game_info)
        elif is_fav:
            fav_games.append(game_info)
        else:
            # edge case, treat as dog if spread is big positive
            dog_games.append(game_info)

    # Helper function to print tables
    def print_games(title, games):
        if not games:
            return
        
        wins = sum(1 for g in games if g['result'] == 'WIN')
        losses = sum(1 for g in games if g['result'] == 'LOSS')
        pushes = sum(1 for g in games if g['result'] == 'PUSH')
        
        print(f"\n{title} (Record: {wins}-{losses}-{pushes})")
        print(f"{'Opponent':<25} {'Result':<8} {'Line':<8} {'Bet On':<20} {'Final Score'}")
        print("-" * 90)
        for g in games:
            print(f"{g['opponent']:<25} {g['result']:<8} {g['line']:<8} {g['bet_on']:<20} {g['score']}")

    print_games("AS UNDERDOG", dog_games)
    print_games("AS FAVORITE", fav_games)

if __name__ == "__main__":
    analyze_record()
