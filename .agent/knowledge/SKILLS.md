# Agent Skills Specification

To effectively manage this codebase, the Agent requires the following specialized skills, defined here as Python function signatures.

## 1. Execution & Deployment
```python
def run_model(sport: str, model_type: str = 'main') -> dict:
    """
    Executes a specific sport model to generate new picks.
    
    Args:
        sport: 'nba', 'nfl', 'ncaab', 'wnba', 'soccer'
        model_type: 'main' (spreads/totals) or 'props' (player props)
        
    Returns:
        dict: Summary of new picks generated.
    """
    pass

def trigger_deployment() -> bool:
    """
    Manually triggers the 'auto_push.sh' script to sync latest HTML/JSON to GitHub.
    Useful after making manual edits to tracking files.
    """
    pass

def run_auto_grader(force: bool = False) -> dict:
    """
    Triggers 'auto_grader.py' to resolve pending bets and update dashboards.
    
    Args:
        force: If True, regenerates HTML even if no new grades found.
    """
    pass
```

## 2. Data & State Management
```python
def fetch_live_odds(sport: str) -> list:
    """
    Directly queries The Odds API for a specific sport to validate market lines
    before running a full model backtest.
    """
    pass

def get_active_portfolio() -> dict:
    """
    Aggregates all 'pending' bets from all *_tracking.json files.
    Returns a unified view of currently at-risk capital.
    """
    pass

def patch_tracking_result(pick_id: str, status: str, result_score: str) -> bool:
    """
    Manually corrects a bet result in the JSON tracking file if the Auto-Grader fails.
    
    Args:
        pick_id: Unique identifier of the pick.
        status: 'win', 'loss', 'push', 'void'
        result_score: e.g. "Lakers 110, Warriors 100"
    """
    pass
```

## 3. Analysis & Reporting
```python
def generate_performance_report(days: int = 7) -> str:
    """
    Runs 'generate_analytics_dashboard.py' and extracts a text summary 
    of ROI/Win Rate for the last N days.
    """
    pass

def analyze_model_drift(sport: str) -> dict:
    """
    Compares 'Recent Form' (L10) vs 'Season Form' to detect if a model 
    is losing its edge.
    """
    pass
```
