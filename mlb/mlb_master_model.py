import pandas as pd
import numpy as np
from pybaseball import pitching_stats, batting_stats, statcast_batter_exitvelo_barrels
from scipy.stats import poisson
from datetime import datetime

# --- CONFIGURATION ---
SEASON = 2025
MIN_INN = 50  # Minimum innings for pitchers to be considered
MIN_PA = 150  # Minimum plate appearances for batters
BANKROLL = 10000  # Example Bankroll $10,000

print(f"--- INITIALIZING MLB ALPHA MODEL ({SEASON} Data) ---")

# ==========================================
# 1. DATA INGESTION ENGINE
# ==========================================
def get_data():
    print("1. Fetching Advanced Stats from FanGraphs & Statcast...")
    
    # Pitching: We want SIERA (Skill-Interactive ERA) and xFIP
    pitching = pitching_stats(SEASON, qual=MIN_INN)
    pitching = pitching[['Name', 'Team', 'SIERA', 'xFIP', 'K/9', 'BB/9', 'HR/9', 'K%', 'BB%']]
    
    # Batting: We want wRC+ (Weighted Runs Created) and ISO (Power)
    batting = batting_stats(SEASON, qual=MIN_PA)
    batting = batting[['Name', 'Team', 'wRC+', 'ISO', 'K%', 'BB%']]
    
    # Statcast: For Home Run props (Barrel Rate is king)
    # Note: This function fetches heavy data, simplified here for speed
    try:
        barrels = statcast_batter_exitvelo_barrels(SEASON, MIN_PA)
        barrels = barrels[['last_name, first_name', 'brl_percent']]
        # Clean names to match FanGraphs
        barrels['Name'] = barrels['last_name, first_name'].apply(lambda x: f"{x.split(', ')[1]} {x.split(', ')[0]}")
        batting = batting.merge(barrels[['Name', 'brl_percent']], on='Name', how='left').fillna(0)
    except:
        print("   ! Statcast Barrel data unavailable, using ISO proxy.")
        batting['brl_percent'] = batting['ISO'] * 10 # Rough proxy if API fails

    return pitching, batting

# ==========================================
# 2. PROBABILITY ENGINES
# ==========================================

def calculate_f5_probability(pitcher_a, pitcher_b, lineup_a_wrc, lineup_b_wrc):
    """
    Calculates Win Probability for First 5 Innings.
    Logic: Pitching is 70% of F5, Hitting is 30%.
    """
    # Lower SIERA is better. We invert it for a "Score".
    score_a = (5.00 - pitcher_a['SIERA']) * 0.7 + (lineup_a_wrc / 100) * 0.3
    score_b = (5.00 - pitcher_b['SIERA']) * 0.7 + (lineup_b_wrc / 100) * 0.3
    
    total_score = score_a + score_b
    win_prob_a = score_a / total_score
    return win_prob_a

def calculate_k_prop_probability(pitcher, opp_lineup_k_rate, line=5.5):
    """
    Uses Poisson Distribution to find probability of Over/Under Ks.
    Input: Pitcher's K/9 and Opponent's tendency to strike out.
    """
    # Expected Ks = (Pitcher K/9) * (Opponent K factor) * (Innings Expected / 9)
    # We assume average starter goes 5.5 innings
    avg_innings = 5.5
    
    # Adjust pitcher's K rate by opponent's K vulnerability (1.0 is avg, 1.2 is high Ks)
    opp_k_factor = opp_lineup_k_rate / 0.22 # 22% is roughly league average K%
    expected_ks = (pitcher['K/9'] * (avg_innings / 9)) * opp_k_factor
    
    # Poisson Probability of getting MORE than the line
    # poisson.cdf returns probability of getting <= x. So 1 - cdf is > x.
    prob_over = 1 - poisson.cdf(line, expected_ks)
    return expected_ks, prob_over

def calculate_hr_probability(batter, pitcher):
    """
    Simplified HR Model: Barrel Rate vs Pitcher HR/9
    """
    # Base HR probability per AB is roughly 3-4%
    base_prob = 0.035
    
    # Modifiers
    batter_mod = batter['brl_percent'] / 6.0  # 6% barrel rate is approx avg
    pitcher_mod = pitcher['HR/9'] / 1.2      # 1.2 HR/9 is approx avg
    
    estimated_prob = base_prob * batter_mod * pitcher_mod
    
    # Probability of at least 1 HR in 4 At-Bats (Binomial)
    prob_hr_game = 1 - (1 - estimated_prob) ** 4
    return prob_hr_game

# ==========================================
# 3. THE KELLY CRITERION (Bankroll Management)
# ==========================================
def kelly_criterion(true_prob, decimal_odds):
    """
    Calculates optimal bet size. 
    f = (bp - q) / b
    """
    b = decimal_odds - 1
    q = 1 - true_prob
    f = (b * true_prob - q) / b
    return max(0, f) # Never bet negative money

# ==========================================
# 4. HTML GENERATION
# ==========================================
def generate_html(results):
    """
    Generates a mobile-optimized, dark-themed HTML report.
    Perfect for social media screenshots.
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Alpha Model - {results['date']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: #000000;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            font-weight: 700;
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }}

        .header {{
            background: #1a1a1a;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
            border: 3px solid #0077ff;
        }}

        .header h1 {{
            font-size: 28px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 3px;
        }}

        .header .subtitle {{
            color: #0077ff;
            font-size: 14px;
            font-weight: 700;
        }}

        .matchup {{
            background: #1a1a1a;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
            border: 3px solid #ff6b35;
        }}

        .matchup h2 {{
            font-size: 22px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 15px;
        }}

        .teams {{
            display: flex;
            justify-content: space-around;
            align-items: center;
            margin-top: 15px;
        }}

        .team {{
            flex: 1;
            text-align: center;
        }}

        .team-name {{
            font-size: 20px;
            font-weight: 900;
            color: #ffd60a;
            margin-bottom: 5px;
        }}

        .pitcher-name {{
            font-size: 14px;
            color: #ffffff;
            font-weight: 700;
        }}

        .vs {{
            font-size: 24px;
            font-weight: 900;
            color: #ff6b35;
            margin: 0 15px;
        }}

        .bet-card {{
            background: #1a1a1a;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 3px solid #06d6a0;
        }}

        .bet-card.highlight {{
            border-color: #ffd60a;
        }}

        .bet-card h3 {{
            font-size: 18px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .bet-card.highlight h3 {{
            color: #ffd60a;
        }}

        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .stat-row:last-child {{
            border-bottom: none;
        }}

        .stat-label {{
            font-weight: 700;
            color: #ffffff;
            font-size: 14px;
        }}

        .stat-value {{
            font-weight: 900;
            color: #ffffff;
            font-size: 16px;
        }}

        .stat-value.positive {{
            color: #0077ff;
        }}

        .stat-value.highlight {{
            color: #e63946;
            font-size: 18px;
        }}

        .bet-recommendation {{
            background: #06d6a0;
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
            text-align: center;
            border: 3px solid #06d6a0;
        }}

        .bet-recommendation.value {{
            background: #e63946;
            border-color: #e63946;
        }}

        .bet-recommendation strong {{
            font-size: 18px;
            font-weight: 900;
            color: #ffffff;
            display: block;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .bet-recommendation.value strong {{
            color: #ffffff;
        }}

        .no-bet {{
            background: #1a1a1a;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            text-align: center;
            color: #888888;
            font-weight: 700;
            border: 2px solid #333333;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #ffffff;
            font-size: 12px;
            font-weight: 700;
            opacity: 0.6;
        }}

        .emoji {{
            font-size: 24px;
            margin-right: 10px;
        }}

        /* Tablet and smaller */
        @media (max-width: 768px) {{
            .container {{
                max-width: 600px;
            }}

            .header h1 {{
                font-size: 26px;
            }}
        }}

        /* Mobile */
        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}

            .container {{
                max-width: 100%;
            }}

            .header {{
                padding: 20px;
            }}

            .header h1 {{
                font-size: 22px;
                letter-spacing: 1px;
            }}

            .header .subtitle {{
                font-size: 12px;
            }}

            .matchup h2 {{
                font-size: 18px;
            }}

            .teams {{
                flex-direction: column;
            }}

            .team-name {{
                font-size: 18px;
            }}

            .pitcher-name {{
                font-size: 13px;
            }}

            .vs {{
                margin: 10px 0;
                font-size: 20px;
            }}

            .bet-card {{
                padding: 20px;
            }}

            .bet-card h3 {{
                font-size: 16px;
            }}

            .stat-label {{
                font-size: 13px;
            }}

            .stat-value {{
                font-size: 15px;
            }}

            .stat-value.highlight {{
                font-size: 16px;
            }}

            .bet-recommendation strong {{
                font-size: 16px;
            }}
        }}

        /* Large screens - better for YouTube videos */
        @media (min-width: 1200px) {{
            body {{
                padding: 40px;
            }}

            .header {{
                padding: 40px;
            }}

            .header h1 {{
                font-size: 36px;
            }}

            .header .subtitle {{
                font-size: 16px;
            }}

            .matchup {{
                padding: 30px;
            }}

            .matchup h2 {{
                font-size: 28px;
            }}

            .team-name {{
                font-size: 24px;
            }}

            .pitcher-name {{
                font-size: 16px;
            }}

            .bet-card {{
                padding: 35px;
            }}

            .bet-card h3 {{
                font-size: 22px;
            }}

            .stat-label {{
                font-size: 16px;
            }}

            .stat-value {{
                font-size: 18px;
            }}

            .stat-value.highlight {{
                font-size: 22px;
            }}

            .bet-recommendation {{
                padding: 25px;
            }}

            .bet-recommendation strong {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚾ MLB Alpha Model</h1>
            <div class="subtitle">{results['date']}</div>
        </div>

        <div class="matchup">
            <h2>Today's Featured Game</h2>
            <div class="teams">
                <div class="team">
                    <div class="team-name">{results['team_a']}</div>
                    <div class="pitcher-name">{results['pitcher_a']}</div>
                </div>
                <div class="vs">VS</div>
                <div class="team">
                    <div class="team-name">{results['team_b']}</div>
                    <div class="pitcher-name">{results['pitcher_b']}</div>
                </div>
            </div>
        </div>

        <!-- F5 Betting Section -->
        <div class="bet-card {'highlight' if results['f5_bet'] else ''}">
            <h3>🎯 First 5 Innings (F5)</h3>
            <div class="stat-row">
                <span class="stat-label">Win Probability</span>
                <span class="stat-value highlight">{results['f5_prob']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Book Odds</span>
                <span class="stat-value">{results['f5_odds']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Kelly Criterion</span>
                <span class="stat-value positive">{results['f5_kelly']}</span>
            </div>
            {results['f5_recommendation']}
        </div>

        <!-- Strikeout Prop Section -->
        <div class="bet-card {'highlight' if results['k_bet'] else ''}">
            <h3>🔥 Strikeout Prop</h3>
            <div class="stat-row">
                <span class="stat-label">Player</span>
                <span class="stat-value">{results['k_player']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Projected Ks</span>
                <span class="stat-value highlight">{results['k_projected']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Market Line</span>
                <span class="stat-value">{results['k_line']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Over Probability</span>
                <span class="stat-value positive">{results['k_prob']}</span>
            </div>
            {results['k_recommendation']}
        </div>

        <!-- Home Run Prop Section -->
        <div class="bet-card {'highlight' if results['hr_bet'] else ''}">
            <h3>💣 Home Run Prop</h3>
            <div class="stat-row">
                <span class="stat-label">Player</span>
                <span class="stat-value">{results['hr_player']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">HR Probability</span>
                <span class="stat-value highlight">{results['hr_prob']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Fair Odds</span>
                <span class="stat-value positive">{results['hr_fair']}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Book Odds</span>
                <span class="stat-value">{results['hr_odds']}</span>
            </div>
            {results['hr_recommendation']}
        </div>

        <div class="footer">
            Model based on SIERA, xFIP, wRC+, Barrel Rate & Advanced Analytics<br>
            Always bet responsibly. Past performance doesn't guarantee future results.
        </div>
    </div>
</body>
</html>
"""
    return html

# ==========================================
# 5. EXECUTION (Simulated Day)
# ==========================================

# Get Data
pitchers, batters = get_data()

print("\n--- SIMULATING A GAME: YANKEES (Cole) vs DODGERS (Glasnow) ---")

# Mock Data Lookup (In production, this comes from Today's Schedule)
try:
    p_nyy = pitchers[pitchers['Name'].str.contains("Cole")].iloc[0]
    p_lad = pitchers[pitchers['Name'].str.contains("Glasnow")].iloc[0]

    # Mock Lineup Stats (Average wRC+ of the team)
    nyy_wrc = 115 # Yankees are good
    lad_wrc = 118 # Dodgers are great

    # Mock Lineup K% (Average K% of opponent)
    nyy_k_rate = 0.21
    lad_k_rate = 0.23

    # Initialize results dictionary
    results = {
        'date': datetime.now().strftime('%B %d, %Y'),
        'team_a': 'YANKEES',
        'team_b': 'DODGERS',
        'pitcher_a': p_nyy['Name'],
        'pitcher_b': p_lad['Name'],
    }

    # --- MODEL 1: FIRST 5 INNINGS ---
    prob_nyy = calculate_f5_probability(p_nyy, p_lad, nyy_wrc, lad_wrc)
    print(f"\n[F5 MODEL] NYY Win Prob: {prob_nyy:.2%}")

    # Check for Value (e.g., Book has NYY +105, which is 2.05 decimal)
    book_odds = 2.05
    kel = kelly_criterion(prob_nyy, book_odds)

    results['f5_prob'] = f"{prob_nyy:.1%}"
    results['f5_odds'] = "+105"
    results['f5_kelly'] = f"{kel*0.5:.1%} of bankroll"
    results['f5_bet'] = kel > 0

    if kel > 0:
        print(f"   >>> BET FOUND: Bet {kel*0.5:.2%} of bankroll (Half-Kelly) on NYY F5")
        results['f5_recommendation'] = '<div class="bet-recommendation"><strong>🚨 BET RECOMMENDED: Yankees F5 ML</strong></div>'
    else:
        print("   >>> NO BET: Market price is efficient.")
        results['f5_recommendation'] = '<div class="no-bet">No value found - Market is efficient</div>'

    # --- MODEL 2: PLAYER PROP (Glasnow Strikeouts) ---
    # Book Line: 7.5 Ks at -110 (1.91 decimal)
    market_line = 7.5
    exp_k, prob_over = calculate_k_prop_probability(p_lad, nyy_k_rate, line=market_line)
    print(f"\n[PROP MODEL] Glasnow Proj Ks: {exp_k:.2f} | Prob Over {market_line}: {prob_over:.2%}")

    results['k_player'] = p_lad['Name']
    results['k_projected'] = f"{exp_k:.1f}"
    results['k_line'] = f"{market_line}"
    results['k_prob'] = f"{prob_over:.1%}"
    results['k_bet'] = prob_over > 0.55

    if prob_over > 0.55: # 55% is roughly break-even for -110
        print(f"   >>> BET FOUND: Hammer the OVER {market_line} Ks")
        results['k_recommendation'] = f'<div class="bet-recommendation"><strong>🚨 BET RECOMMENDED: OVER {market_line} Ks</strong></div>'
    else:
        results['k_recommendation'] = '<div class="no-bet">No value found - Pass on this prop</div>'

    # --- MODEL 3: HOME RUN (Aaron Judge vs Glasnow) ---
    judge = batters[batters['Name'] == 'Aaron Judge'].iloc[0]
    hr_prob = calculate_hr_probability(judge, p_lad)
    fair_odds = 1 / hr_prob
    print(f"\n[HR MODEL] Aaron Judge HR Prob: {hr_prob:.2%} | Fair Odds: +{int((fair_odds-1)*100)}")

    results['hr_player'] = 'Aaron Judge'
    results['hr_prob'] = f"{hr_prob:.1%}"
    results['hr_fair'] = f"+{int((fair_odds-1)*100)}"
    results['hr_odds'] = "+250"
    results['hr_bet'] = 3.50 > fair_odds

    # If Book offers +250 and our fair odds are +210, we bet.
    if 3.50 > fair_odds: # 3.50 is +250
        print(f"   >>> VALUE: Book offers +250, Model says +{int((fair_odds-1)*100)}. BET IT.")
        results['hr_recommendation'] = '<div class="bet-recommendation value"><strong>💎 VALUE BET: Aaron Judge HR at +250</strong></div>'
    else:
        results['hr_recommendation'] = '<div class="no-bet">No value - Book odds are too low</div>'

    # Generate HTML
    html_output = generate_html(results)
    output_file = 'mlb_model_output.html'
    with open(output_file, 'w') as f:
        f.write(html_output)

    print(f"\n✅ HTML report generated: {output_file}")

except IndexError:
    print(f"Could not find specific players in the {SEASON} dataset. Ensure names match FanGraphs exactly.")