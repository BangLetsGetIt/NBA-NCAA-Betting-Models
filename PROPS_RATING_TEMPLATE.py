"""
TEMPLATE: Probability-Based A.I. Rating for Props Models
==========================================================
Use this as a template when adding rating to props models.

Key differences from team models:
1. Uses probability edges (percentages) instead of point edges
2. Normalizes by dividing by 0.03 (15% = 5.0 rating) instead of 3.0 (15 points = 5.0)
3. Uses EV as proxy for probability edge if not explicitly calculated
"""

def get_historical_performance_by_edge_props(tracking_data):
    """Calculate win rates by EV/edge magnitude for props (probability-based)"""
    picks = tracking_data.get('picks', [])
    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss']]
    
    from collections import defaultdict
    edge_ranges = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for pick in completed_picks:
        # Use EV as edge proxy (EV is percentage-based)
        ev = abs(float(pick.get('ev', 0)))
        status = pick.get('status', '')
        
        # Probability/EV edge range buckets (in percentage points)
        if ev >= 15:
            range_key = "15%+"
        elif ev >= 12:
            range_key = "12-14.9%"
        elif ev >= 10:
            range_key = "10-11.9%"
        elif ev >= 8:
            range_key = "8-9.9%"
        elif ev >= 5:
            range_key = "5-7.9%"
        else:
            range_key = "0-4.9%"
        
        if status == 'win':
            edge_ranges[range_key]['wins'] += 1
        elif status == 'loss':
            edge_ranges[range_key]['losses'] += 1
    
    performance_by_edge = {}
    for range_key, stats in edge_ranges.items():
        total = stats['wins'] + stats['losses']
        if total >= 5:  # Only use ranges with sufficient data
            win_rate = stats['wins'] / total if total > 0 else 0.5
            performance_by_edge[range_key] = win_rate
    
    return performance_by_edge

def calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type):
    """Calculate probability edge for props (model prob - market prob)"""
    # Convert American odds to implied probability
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    # Calculate model probability (adapt to your specific model logic)
    base_prob = 0.50
    ai_multiplier = max(0, (ai_score - 9.0) / 1.0)
    
    if bet_type == 'over':
        edge = season_avg - prop_line
    else:
        edge = prop_line - season_avg
    
    edge_factor = min(abs(edge) / 2.0, 1.0)
    
    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)
    
    model_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    model_prob = min(max(model_prob, 0.40), 0.70)
    
    # Probability edge = model prob - market prob
    prob_edge = abs(model_prob - implied_prob)
    return prob_edge

def calculate_ai_rating_props(play, historical_edge_performance):
    """
    Calculate A.I. Rating for props models (probability-based edges)
    Returns rating in 2.3-4.9 range
    """
    # Get probability edge from play data
    prob_edge = play.get('probability_edge')
    
    if prob_edge is None:
        # Calculate from EV (EV is percentage-based and correlates with prob edge)
        ev = abs(play.get('ev', 0))
        prob_edge = ev / 100.0  # EV is already in percentage, convert to decimal
    
    # Normalize probability edge to 0-5 scale (15% = 5.0 rating)
    if prob_edge >= 0.15:
        normalized_edge = 5.0
    else:
        normalized_edge = prob_edge / 0.03  # 15% = 5.0 rating
        normalized_edge = min(5.0, max(0.0, normalized_edge))
    
    # Data quality
    data_quality = 1.0 if play.get('ai_score', 0) >= 9.0 else 0.85
    
    # Historical performance
    historical_factor = 1.0
    if historical_edge_performance:
        ev = abs(play.get('ev', 0))
        if ev >= 15:
            range_key = "15%+"
        elif ev >= 12:
            range_key = "12-14.9%"
        elif ev >= 10:
            range_key = "10-11.9%"
        elif ev >= 8:
            range_key = "8-9.9%"
        elif ev >= 5:
            range_key = "5-7.9%"
        else:
            range_key = "0-4.9%"
        
        if range_key in historical_edge_performance:
            hist_win_rate = historical_edge_performance[range_key]
            historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
            historical_factor = max(0.9, min(1.1, historical_factor))
    
    # Model confidence
    confidence = 1.0
    ai_score = play.get('ai_score', 0)
    ev = abs(play.get('ev', 0))
    
    if ai_score >= 9.8 and ev >= 12:
        confidence = 1.12
    elif ai_score >= 9.5 and ev >= 10:
        confidence = 1.08
    elif ai_score >= 9.0 and ev >= 8:
        confidence = 1.05
    elif ai_score >= 9.0:
        confidence = 1.0
    else:
        confidence = 0.95
    
    confidence = max(0.9, min(1.15, confidence))
    
    # Calculate composite rating
    composite_rating = normalized_edge * data_quality * historical_factor * confidence
    
    # Scale to 2.3-4.9 range
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))
    
    return round(ai_rating, 1)

# INTEGRATION STEPS:
# 1. Copy these functions to your props model
# 2. In analyze_props() or equivalent:
#    - Calculate probability_edge for each play
#    - Call calculate_ai_rating_props() for each play
#    - Add 'ai_rating' and 'probability_edge' to play dict
# 3. Update sorting: sort by rating (primary), ai_score (secondary)
# 4. Update display: show rating in terminal and HTML
# 5. In main(): load tracking_data and get historical_edge_performance before analyzing
