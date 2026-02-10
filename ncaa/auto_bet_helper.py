def get_auto_bet_teams():
    """
    Identify top 20 profitable teams (Auto-Bets) from tracking history.
    Returns a set of team names.
    """
    try:
        tracking_data = load_picks_tracking()
        picks = tracking_data.get('picks', [])
        
        # Filter for decided picks
        decided_picks = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
        
        team_stats = defaultdict(lambda: {'profit': 0, 'count': 0})
        
        for p in decided_picks:
            pick_text = p.get('pick_text', '').upper()
            home = p.get('home_team', '')
            away = p.get('away_team', '')

            # Simple fuzzy matching to find which team was bet on
            bet_team = None
            if home.upper() in pick_text:
                bet_team = home
            elif away.upper() in pick_text:
                bet_team = away

            if not bet_team:
                continue

            # Only count bets where the team was the underdog ("dog") for Auto-Bet logic.
            # For spread bets, a '+' in the pick text indicates the team was the dog.
            is_dog_bet = False
            if p.get('pick_type', '').lower() == 'spread':
                # Example pick_text: "✅ BET: Lehigh Mountain Hawks +17.5"
                if '+' in pick_text:
                    is_dog_bet = True

            # Skip non-dog bets for auto-bet computation
            if not is_dog_bet:
                continue

            # Calculate profit (handle missing or raw dollar values)
            raw_profit = p.get('profit', 0)
            if raw_profit == 0:
                status = p.get('status', '').lower()
                if status == 'win': raw_profit = 91.0
                elif status == 'loss': raw_profit = -100.0

            # Convert to units for consistency with report
            unit_profit = float(raw_profit) / 100.0

            team_stats[bet_team]['profit'] += unit_profit
            team_stats[bet_team]['count'] += 1

        # Sort by profit and take Top 20 (min 5 bets)
        eligible_teams = [
            t for t, s in team_stats.items() 
            if s['count'] >= 5
        ]
        
        # Sort descending by profit
        top_teams = sorted(eligible_teams, key=lambda t: team_stats[t]['profit'], reverse=True)[:20]
        
        return set(top_teams)
        
    except Exception as e:
        print(f"Warning: Could not calculate Auto-Bet teams: {e}")
        return set()

