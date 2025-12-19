#!/usr/bin/env python3
"""
NFL Props Grader

Grades pending props picks using nflreadpy player game logs.

Designed to be imported by the NFL props model scripts so they can:
1) grade pending picks first (no manual runs),
2) then generate the updated HTML with correct all-time tracking.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

import pytz


ET_TZ = pytz.timezone("US/Eastern")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _normalize_person_name(name: str) -> str:
    """
    Normalize player names to improve matching across sources.
    - strip punctuation
    - collapse whitespace
    - drop common suffixes
    """
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s'-]", "", s)  # keep apostrophes/hyphens
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split()
    # drop suffixes
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    if parts and parts[-1].replace(".", "") in suffixes:
        parts = parts[:-1]
    return " ".join(parts)


def _name_first_last(name: str) -> tuple[str, str]:
    n = _normalize_person_name(name)
    parts = n.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], parts[-1]


def _parse_game_time_to_et_date(game_time: str) -> Optional[datetime]:
    """
    Returns timezone-aware ET datetime corresponding to the game_time ISO string.
    """
    if not game_time:
        return None
    try:
        dt_utc = datetime.fromisoformat(str(game_time).replace("Z", "+00:00"))
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        return dt_utc.astimezone(ET_TZ)
    except Exception:
        return None


def _pick_season_year_from_game_time(game_time: str) -> Optional[int]:
    dt_et = _parse_game_time_to_et_date(game_time)
    if not dt_et:
        return None
    # nflreadpy uses season year (e.g. 2024). For late-year games, this matches.
    # For Jan/Feb games, NFL season generally belongs to previous year. We'll
    # map Jan-Aug to previous year, Sep-Dec to current year.
    if dt_et.month >= 9:
        return dt_et.year
    return dt_et.year - 1


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"picks": [], "summary": {}}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _detect_player_col(df) -> Optional[str]:
    for col in [
        "player_display_name",
        "player_name",
        "player",
        "display_name",
        "name",
    ]:
        if col in getattr(df, "columns", []):
            return col
    return None


def _detect_date_col(df) -> Optional[str]:
    for col in [
        "game_date",
        "gameday",
        "game_day",
        "date",
    ]:
        if col in getattr(df, "columns", []):
            return col
    return None


def _ensure_pandas_df(player_stats) -> Any:
    """
    nflreadpy may return a polars dataframe. Convert to pandas if possible.
    """
    try:
        return player_stats.to_pandas()
    except Exception:
        return player_stats


def _load_nflreadpy_player_stats(season_year: int):
    try:
        import nflreadpy as nfl
    except Exception:
        return None

    player_stats = nfl.load_player_stats([season_year])
    return _ensure_pandas_df(player_stats)


def _load_nflreadpy_schedules(season_year: int):
    try:
        import nflreadpy as nfl
    except Exception:
        return None
    schedules = nfl.load_schedules([season_year])
    return _ensure_pandas_df(schedules)


def _find_stat_value(row: Any, candidates: Iterable[str]) -> Optional[float]:
    for col in candidates:
        try:
            if col in row:
                v = row[col]
            else:
                v = row.get(col)  # pandas Series supports .get
        except Exception:
            v = None
        v_num = _safe_float(v)
        if v_num is not None:
            return v_num
    return None


@dataclass
class GradeSpec:
    stat_kind: str
    stat_candidates: tuple[str, ...]
    actual_field: str


GRADE_SPECS: dict[str, GradeSpec] = {
    "passing_yards": GradeSpec(
        stat_kind="passing_yards",
        stat_candidates=("passing_yards", "pass_yds", "passing_yds", "py"),
        actual_field="actual_pass_yds",
    ),
    "rushing_yards": GradeSpec(
        stat_kind="rushing_yards",
        stat_candidates=("rushing_yards", "rush_yds", "rushing_yds", "ry"),
        actual_field="actual_rush_yds",
    ),
    "receptions": GradeSpec(
        stat_kind="receptions",
        stat_candidates=("receptions", "rec", "receptions_total"),
        actual_field="actual_rec",
    ),
    "receiving_yards": GradeSpec(
        stat_kind="receiving_yards",
        stat_candidates=("receiving_yards", "rec_yds", "receiving_yds"),
        actual_field="actual_rec_yds",
    ),
    "anytime_td": GradeSpec(
        stat_kind="anytime_td",
        stat_candidates=("rushing_tds", "receiving_tds"), # We will special case this
        actual_field="actual_tds",
    ),
}


TEAM_NAME_TO_ABBR: dict[str, str] = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}


def grade_props_tracking_file(
    tracking_file: str | Path,
    *,
    stat_kind: str,
    hours_after_game_to_grade: float = 4.0,
    hours_after_game_to_void: float = 36.0,
    verbose: bool = True,
) -> int:
    """
    Grade pending picks in the tracking file using nflreadpy player stats.

    - If a pick is older than hours_after_game_to_grade, attempt to fetch its stat.
    - If stat still can't be found and the pick is older than hours_after_game_to_void,
      mark as PUSH/VOID (so it doesn't stay pending forever).
    """
    spec = GRADE_SPECS.get(stat_kind)
    if not spec:
        raise ValueError(f"Unknown stat_kind: {stat_kind}")

    tracking_path = Path(tracking_file)
    tracking_data = _load_json(tracking_path)
    picks = tracking_data.get("picks", []) or []
    pending = [p for p in picks if str(p.get("status", "")).lower() == "pending"]
    if not pending:
        return 0

    # Determine season from the first pending pick (fallback to current-year heuristics)
    season_year = None
    for p in pending:
        season_year = _pick_season_year_from_game_time(str(p.get("game_time", "")))
        if season_year:
            break
    if season_year is None:
        season_year = datetime.now(ET_TZ).year

    df = _load_nflreadpy_player_stats(season_year)
    if df is None:
        if verbose:
            print("⚠️ nflreadpy not available; cannot auto-grade NFL props yet.")
        return 0

    player_col = _detect_player_col(df)
    if not player_col:
        if verbose:
            print("⚠️ Could not detect nflreadpy player column; cannot grade.")
            print(f"Detected player_col={player_col}")
        return 0

    sched_df = _load_nflreadpy_schedules(season_year)
    if sched_df is None:
        if verbose:
            print("⚠️ nflreadpy schedules not available; cannot map game dates to weeks.")
        return 0
    if "gameday" not in getattr(sched_df, "columns", []) or "week" not in getattr(sched_df, "columns", []):
        if verbose:
            print("⚠️ nflreadpy schedules missing required columns (gameday/week); cannot grade.")
        return 0

    updated = 0
    now_et = datetime.now(ET_TZ)

    for pick in pending:
        game_time = str(pick.get("game_time", ""))
        game_dt_et = _parse_game_time_to_et_date(game_time)
        if not game_dt_et:
            continue

        hours_ago = (now_et - game_dt_et).total_seconds() / 3600.0
        # Check happens later after game completion detection

        target_date = game_dt_et.strftime("%Y-%m-%d")
        player_name = str(pick.get("player", ""))
        team_name = str(pick.get("team", ""))
        team_abbr = TEAM_NAME_TO_ABBR.get(team_name, "")
        prop_line = _safe_float(pick.get("prop_line"))
        bet_type = str(pick.get("bet_type", "")).lower()
        if prop_line is None or bet_type not in {"over", "under"}:
            continue

        # Candidate match: first/last
        p_first, p_last = _name_first_last(player_name)
        if not p_first or not p_last:
            continue

        # Map gameday -> week using schedules, then filter player stats by that week.
        sched_day = sched_df[sched_df["gameday"].astype(str) == target_date]
        if getattr(sched_day, "empty", False):
            # If too old, void it
            if hours_ago >= hours_after_game_to_void:
                pick["status"] = "push"
                pick["result"] = "VOID"
                pick[spec.actual_field] = None
                pick["updated_at"] = now_et.isoformat()
                updated += 1
            continue

        if team_abbr:
            sched_team = sched_day[(sched_day["home_team"] == team_abbr) | (sched_day["away_team"] == team_abbr)]
            if not getattr(sched_team, "empty", False):
                sched_day = sched_team

        # Check if game appears completed (has scores)
        game_finished = False
        try:
            row = sched_day.iloc[0]
            if _safe_float(row.get("home_score")) is not None and _safe_float(row.get("away_score")) is not None:
                # If scores exist, treat as potentially final.
                # nflreadpy usually updates after game.
                game_finished = True
        except Exception:
            pass

        # If game is finished, we can grade immediately (bypass 4 hour buffer)
        effective_buffer = 0.5 if game_finished else hours_after_game_to_grade
        
        if hours_ago < effective_buffer:
            continue

        week_val = _safe_float(sched_day.iloc[0].get("week"))
        if week_val is None:
            continue
        week = int(week_val)

        df_week = df[(df["season"] == season_year) & (df["week"] == week)]
        if team_abbr and "team" in getattr(df_week, "columns", []):
            df_week = df_week[df_week["team"].astype(str) == team_abbr]

        # Find player row
        try:
            player_series = df_week[player_col].astype(str)
        except Exception:
            player_series = df_week[player_col]

        def _matches(n: str) -> bool:
            first, last = _name_first_last(n)
            return (first == p_first and last == p_last) or (last == p_last and first.startswith(p_first[:1]))

        match_idx = None
        for idx, n in enumerate(list(player_series)):
            if _matches(str(n)):
                match_idx = idx
                break

        if match_idx is None:
            # If game is finished and player not found -> DNP -> Void Immediately
            # Or if too old (fallback)
            if game_finished or hours_ago >= hours_after_game_to_void:
                pick["status"] = "push" # void
                pick["result"] = "VOID"
                pick[spec.actual_field] = None
                pick["updated_at"] = now_et.isoformat()
                updated += 1
                if verbose:
                    print(f"⚠ {player_name} not found in finished game -> VOID")
            continue

        row = df_week.iloc[match_idx]
        if spec.stat_kind == "anytime_td":
             # Special logic: Sum rushing_tds + receiving_tds
             rush_td = _find_stat_value(row, ["rushing_tds", "rush_td"]) or 0
             rec_td = _find_stat_value(row, ["receiving_tds", "rec_td"]) or 0
             actual = float(rush_td + rec_td)
        else:
            actual = _find_stat_value(row, spec.stat_candidates)

        if actual is None:
            if game_finished or hours_ago >= hours_after_game_to_void:
                pick["status"] = "push"
                pick["result"] = "VOID"
                pick[spec.actual_field] = None
                pick["updated_at"] = now_et.isoformat()
                updated += 1
                if verbose:
                    print(f"⚠ {player_name} stats missing in finished game -> VOID")
            continue

        # Determine W/L/PUSH
        if actual == prop_line:
            pick["status"] = "push"
            pick["result"] = "PUSH"
        else:
            if spec.stat_kind == "anytime_td":
                 # ATD is simple: If actual >= 1, WIN. Else LOSS (assuming line is 0.5 or implied 'anytime')
                 # But usually ATD bets don't have a line like O/U 0.5, it's just "Anytime TD".
                 # So if actual >= 1 it is a WIN.
                 is_win = actual >= 1
            elif bet_type == "over":
                is_win = actual > prop_line
            else:
                is_win = actual < prop_line
            pick["status"] = "win" if is_win else "loss"
            pick["result"] = "WIN" if is_win else "LOSS"

        pick[spec.actual_field] = float(actual)
        pick["updated_at"] = now_et.isoformat()
        updated += 1

        if verbose:
            print(f"✓ {spec.stat_kind} graded: {player_name} {bet_type.upper()} {prop_line} -> {actual} ({pick['result']})")

    if updated > 0:
        _save_json(tracking_path, tracking_data)
    return updated

