# System Architecture: Sports Betting Models

## 1. Technical Summary
This codebase is a **multi-sport betting analytics platform** powered by Python, utilizing **The Odds API** and **Sports-Reference** for data ingestion. It employs a modular architecture where individual sport models (NBA, NFL, NCAAB, etc.) fetch data, predict outcomes, and log bets to JSON tracking files, which are then aggregated by a central **Auto-Grader** and **Best Plays Bot**. The system outputs rich HTML dashboards for visualization and tracking, utilizing Jinja2 templating for report generation.

## 2. Core Data Flow
1.  **Ingestion:**
    *   `fetch_odds()` (The Odds API) -> Live Market Data
    *   `fetch_*_stats()` (Scrapers/APIs) -> Team/Player Performance Data
2.  **Processing (The "Brain"):**
    *   **Models:** (e.g., `ncaa/ncaab_model_2ndFINAL.py`) Apply statistical logic, handicapping parameters (e.g., `HOME_COURT_ADVANTAGE`), and value detection against market lines.
    *   **Grading:** `auto_grader.py` loops through tracking files, queries scores, and resolves bets (Win/Loss/Push).
    *   **Aggregation:** `best_plays_bot.py` scans all model outputs to identify high-confidence ("Fire") plays.
3.  **Persistence (State):**
    *   `*_tracking.json`: The source of truth for all bets.
    *   `analytics_data.json`: Aggregated performance metrics.
4.  **Presentation:**
    *   `analytics_dashboard.html`: The user-facing "Commmand Center".
    *   `best_plays.html`: Curated list of top bets.

## 3. Key Components
*   **Auto-Grader (`auto_grader.py`):** Daemon process that manages the lifecycle of a bet from "Pending" to "Graded", triggers HTML updates, and pushes to Git.
*   **Best Plays Bot (`best_plays_bot.py`):** Heuristic engine that scores bets (0-100) based on Edge, Model Win Rate, and Kelly Criterion principles to classify plays as FIRE, SOLID, or VALUE.
*   **Analytics Dashboard (`generate_analytics_dashboard.py`):** Reporting engine that computes ROI, Win Rate, and time-series performance across all sports.

## 4. Directory Structure
*   `/nba`, `/nfl`, `/ncaa`: Sport-specific logic and tracking files.
*   `/tools`: Utility scripts.
*   `root`: Core orchestrators (`auto_grader.py`, `run_all_models.sh`) and dashboard generators.
