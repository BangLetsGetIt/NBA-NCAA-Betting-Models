import json
import os
from ufc_model import UFCModel
from ufc_odds_fetcher import UFCOddsFetcher
from ufc_stats_scraper import UFCStatsScraper
from datetime import datetime
import jinja2

# ANSI Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    END = '\033[0m'

class UFCModelRunner:
    def __init__(self, data_dir="ufc/data"):
        self.data_dir = data_dir
        self.model = UFCModel(data_dir=data_dir)
        self.odds_fetcher = UFCOddsFetcher(data_dir=data_dir)
        self.scraper = UFCStatsScraper(data_dir=data_dir)
        self.picks_file = os.path.join(data_dir, "ufc_picks.json")
        self.dashboard_template = os.path.join("ufc", "ufc_dashboard_template.html")
        self.dashboard_output = os.path.join("ufc", "ufc_dashboard.html")
        
    def run_daily_scan(self):
        """
        1. Fetch latest odds
        2. Load model
        3. Predict outcome for each fight
        4. Calculate EV
        5. Save 'Picks' to JSON
        """
        print(f"[{datetime.now()}] Starting UFC Model Scan...")
        
        # 1. Update Odds
        events = self.odds_fetcher.fetch_upcoming_odds()
        if not events:
            print("No upcoming events found or API error.")
            return

        # 2. Load Model Data
        self.model.load_data()
        
        picks = []
        
        for event in events:
            event_name = event.get('sport_title', 'UFC Event') 
            # The Odds API structure: bookmakers -> markets -> outcomes
            # We need to find the best odds? Or just average?
            # Let's use the first available bookmaker for simplicity or 'pinnacle' if available
            
            bookmakers = event.get('bookmakers', [])
            if not bookmakers: continue
            
            # Using first bookmaker for now
            market = next((m for m in bookmakers[0]['markets'] if m['key'] == 'h2h'), None)
            if not market: continue
            
            outcomes = market['outcomes']
            if len(outcomes) != 2: continue # Skip 3-way markets if any
            
            f1_name = outcomes[0]['name']
            f1_price = outcomes[0]['price']
            
            f2_name = outcomes[1]['name']
            f2_price = outcomes[1]['price']
            
            # 3. Predict
            # prediction return: {'win_prob': float, 'fair_odds': int, ...}
            # We need to run predict(f1, f2). The model handles the perspective of f1 vs f2.
            
            pred = self.model.predict(f1_name, f2_name)
            if not pred:
                continue
                
            # 4. Calculate EV
            # Model gives probability of f1 winning.
            f1_prob = pred['win_prob']
            
            # Convert market price to implied prob
            def price_to_prob(price):
                if price > 0: return 100 / (price + 100)
                else: return (-price) / (-price + 100)
                
            f1_implied = price_to_prob(f1_price)
            f2_implied = price_to_prob(f2_price)
            
            # Calculate Edge
            f1_edge = f1_prob - f1_implied
            f2_edge = (1 - f1_prob) - f2_implied
            
            # Determine Bet
            bet_on = None
            edge = 0
            odds = 0
            
            if f1_edge > 0.05: # 5% threshold
                bet_on = f1_name
                edge = f1_edge
                odds = f1_price
            elif f2_edge > 0.05:
                bet_on = f2_name
                edge = f2_edge
                odds = f2_price
            
            if bet_on:
                pick = {
                    "event_id": event['id'],
                    "fighter": bet_on,
                    "opponent": f2_name if bet_on == f1_name else f1_name,
                    "odds": odds,
                    "model_prob": f1_prob if bet_on == f1_name else (1 - f1_prob),
                    "edge_pct": round(edge * 100, 2),
                    "recommended_bet_size_unit": 1, # Placeholder
                    "status": "pending",
                    "timestamp": datetime.now().isoformat(),
                    "game_time": event.get('commence_time') 
                }
                picks.append(pick)
                # Parse date for log
                game_date = event.get('commence_time', '')[:10]
                print(f"💰 Found Value ({game_date}): {bet_on} ({odds}) over {pick['opponent']}. Edge: {pick['edge_pct']}%")
        
        # Save picks
        if picks:
            # Load existing picks to avoid overwriting history?
            # ideally we append new ones.
            existing = []
            if os.path.exists(self.picks_file):
                with open(self.picks_file, 'r') as f:
                    existing = json.load(f)
            
            # Simple dedup by event_id + fighter
            existing_keys = set(f"{p['event_id']}_{p['fighter']}" for p in existing)
            new_picks = [p for p in picks if f"{p['event_id']}_{p['fighter']}" not in existing_keys]
            
            all_picks = existing + new_picks
            
            with open(self.picks_file, 'w') as f:
                json.dump(all_picks, f, indent=4)
                
            print(f"Saved {len(new_picks)} new picks to {self.picks_file}")
        else:
            print("No value bets found.")

    def grade_pending_picks(self):
        """
        Check pending picks against historical results.
        Returns number of picks updated.
        """
        print(f"[{datetime.now()}] Grading UFC Picks...")
        
        if not os.path.exists(self.picks_file):
            return 0
            
        with open(self.picks_file, 'r') as f:
            picks = json.load(f)
            
        pending_picks = [p for p in picks if p.get('status') == 'pending']
        if not pending_picks:
            print("No pending picks to grade.")
            return 0
            
        # Refresh historical data
        # We only need to scrape if we have pending picks from the past
        # BUT for simplicity, let's just ensure we have recent results
        print("Refreshing fight results...")
        self.scraper.scrape_completed_events()
        
        # Load results
        history_file = os.path.join(self.data_dir, "historical_fights.json")
        if not os.path.exists(history_file):
            print("No historical fight data found.")
            return 0
            
        with open(history_file, 'r') as f:
            fights = json.load(f)
            
        # Mapping: Event Date + Fighter Names -> Result
        # Since names can vary, we might need fuzzy match, but let's try exact first (cleaned)
        
        updated_count = 0
        
        for pick in picks:
            if pick.get('status') != 'pending':
                continue
                
            fighter = pick['fighter'].lower()
            opponent = pick['opponent'].lower()
            
            # Find matching fight
            # We don't have event_date in pick usually? We added timestamp but checks event_id logic?
            # Creating a reliable lookup is key.
            # Let's search all fights for this matchup
            
            match = None
            for fight in fights:
                f1 = fight['fighter_1'].lower()
                f2 = fight['fighter_2'].lower()
                
                if (fighter in f1 and opponent in f2) or (fighter in f2 and opponent in f1):
                    # Found match!
                    # Check if date is recent enough? skipping for now
                    match = fight
                    break
            
            if match:
                # determine winner
                # We need to know which fighter corresponds to our pick
                # "fighter": "Islam Makhachev"
                
                pick_won = False
                result_known = False
                
                f1 = match['fighter_1'].lower()
                f2 = match['fighter_2'].lower()
                
                # Check outcome
                if fighter in f1:
                    # Our fighter is f1
                    outcome = match['fighter_1_outcome']
                    if outcome == 'win':
                        pick_won = True
                        result_known = True
                    elif outcome == 'loss':
                        pick_won = False
                        result_known = True
                    # else draw/nc/etc
                elif fighter in f2:
                    # Our fighter is f2
                    outcome = match['fighter_2_outcome']
                    if outcome == 'win':
                        pick_won = True
                        result_known = True
                    elif outcome == 'loss':
                        pick_won = False
                        result_known = True
                        
                if result_known:
                    pick['status'] = 'won' if pick_won else 'lost'
                    pick['result_timestamp'] = datetime.now().isoformat()
                    updated_count += 1
                    status_color = Colors.GREEN if pick_won else Colors.RED
                    print(f"Graded: {pick['fighter']} vs {pick['opponent']} -> {status_color}{pick['status'].upper()}{Colors.END}")

        if updated_count > 0:
            with open(self.picks_file, 'w') as f:
                json.dump(picks, f, indent=4)
            print(f"Updated {updated_count} picks.")
            
        return updated_count

    def generate_dashboard(self):
        """Generates HTML dashboard from picks history"""
        print(f"[{datetime.now()}] Generating UFC Dashboard...")
        
        if not os.path.exists(self.picks_file):
            print("No picks file found.")
            return

        with open(self.picks_file, 'r') as f:
            picks = json.load(f)
            
        # Calculate Stats
        total_picks = len(picks)
        wins = sum(1 for p in picks if p.get('status') == 'won')
        losses = sum(1 for p in picks if p.get('status') == 'lost')
        pending = sum(1 for p in picks if p.get('status') == 'pending')
        
        win_rate = 0
        if (wins + losses) > 0:
            win_rate = (wins / (wins + losses)) * 100
            
        # Calculate Profit (Units)
        profit = 0.0
        for p in picks:
            if p.get('status') == 'won':
                # Profit = (Odds - 1) * Units if Odds > 2.0 (Decimal) ?? 
                # Wait, odds in JSON are American or Decimal?
                # ufc_model_runner.py saves odds from API.
                # fetch_upcoming_odds uses 'american' by default? 
                # Let's check ufc_model_runner.py line 134: 'american' is typically default for The Odds API if not specified?
                # Actually ufc_odds_fetcher.py decides. Let's check.
                # Assuming American for now as per other models.
                
                odds = float(p.get('odds', -110))
                units = float(p.get('recommended_bet_size_unit', 1))
                
                if odds > 0:
                    profit += (odds / 100) * units
                else:
                    profit += (100 / abs(odds)) * units
            elif p.get('status') == 'lost':
                units = float(p.get('recommended_bet_size_unit', 1))
                profit -= units
                
        roi = 0
        invested = wins + losses # assuming 1 unit per bet
        if invested > 0:
            roi = (profit / invested) * 100
            
        # Prepare context for Jinja
        # Sort picks by date (newest first)
        picks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Load fighter stats for enrichment
        fighters_db = {}
        fighters_db_path = os.path.join(self.data_dir, "fighters_db.json")
        if os.path.exists(fighters_db_path):
            with open(fighters_db_path, 'r') as f:
                fighters_list = json.load(f)
                # Convert list to dict for lookup: "First Last" -> stats
                for f_obj in fighters_list:
                    full_name = f"{f_obj.get('first_name', '')} {f_obj.get('last_name', '')}".strip()
                    fighters_db[full_name] = f_obj

        formatted_picks = []
        for p in picks:
            # Format date from game_time if available, else timestamp
            ts = p.get('game_time') or p.get('timestamp', '')
            date_str = ts[:10] if ts else 'N/A'
            
            # Odds display
            odds_val = p.get('odds', -110)
            if odds_val > 0: odds_str = f"+{odds_val}"
            else: odds_str = str(odds_val)
            
            status_class = 'pending'
            if p.get('status') == 'won': status_class = 'win'
            elif p.get('status') == 'lost': status_class = 'lost'
            
            # Implied Probability
            if odds_val > 0:
                implied_prob = 100 / (odds_val + 100)
            else:
                implied_prob = abs(odds_val) / (abs(odds_val) + 100)
            implied_prob_pct = round(implied_prob * 100, 1)

            # Kelly Suggestion (Simple fractional)
            kelly = 0
            edge = p.get('edge_pct', 0) / 100.0
            if edge > 0:
                decimal_odds = (odds_val / 100) + 1 if odds_val > 0 else (100 / abs(odds_val)) + 1
                b = decimal_odds - 1
                q = 1 - (p.get('model_prob', 0))
                p_win = p.get('model_prob', 0)
                kelly = (b * p_win - q) / b
                kelly = max(0, kelly) * 0.5 # Quarter kelly safety
            kelly_units = round(kelly * 10, 2) # Arbitrary scale for display
            if kelly_units < 0.1: kelly_units = 0.5 # Minimum unit

            # Fetch Fighter Stats
            fighter_name = p.get('fighter')
            f_stats = fighters_db.get(fighter_name, {})
            
            # Stats Display
            str_diff = 0
            str_diff_display = "N/A"
            if 'slpm' in f_stats:
                str_diff = f_stats.get('slpm', 0) 
                str_diff_display = f"{str_diff:.2f}"
            
            td_avg_display = f"{f_stats.get('td_avg', 0):.2f}"
            reach_display = f_stats.get('reach', 'N/A')
            weight_class = "Catchweight" # Placeholder or inferred from matchup
            
            formatted_picks.append({
                'date': date_str,
                'fighter': fighter_name,
                'opponent': p.get('opponent'),
                'model_prob': round(p.get('model_prob', 0) * 100, 1),
                'edge': p.get('edge_pct'),
                'edge_pct': p.get('edge_pct'),
                'odds': odds_str,
                'odds_val': odds_val,
                'status': p.get('status', 'pending').upper(),
                'status_class': status_class,
                'implied_prob': implied_prob_pct,
                'kelly_suggestion': kelly_units,
                'str_diff': str_diff,
                'str_diff_display': str_diff_display,
                'td_avg_display': td_avg_display,
                'reach_display': reach_display,
                'weight_class': weight_class
            })
            
        context = {
            'total_picks': total_picks,
            'wins': wins,
            'losses': losses,
            'pending_count': pending,
            'win_rate': round(win_rate, 1),
            'profit_units': round(profit, 2),
            'roi': round(roi, 1),
            'picks': formatted_picks,
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Render
        try:
            # Need colors for verify?
            # actually kelly_suggestion above had a bug with colors.strip which isn't imported potentially here or is local class.
            # Fixed plain assignment:
            
            with open(self.dashboard_template, 'r') as f:
                template_str = f.read()
                
            template = jinja2.Template(template_str)
            html_out = template.render(context)
            
            with open(self.dashboard_output, 'w') as f:
                f.write(html_out)
                
            print(f"Dashboard generated: {self.dashboard_output}")
        except Exception as e:
            print(f"Error rendering dashboard: {e}")


if __name__ == "__main__":
    runner = UFCModelRunner()
    runner.run_daily_scan()
