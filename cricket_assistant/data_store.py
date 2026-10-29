from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MATCHES_FILE = DATA_DIR / "matches.csv"
PLAYERS_FILE = DATA_DIR / "players.csv"
BOWLERS_FILE = DATA_DIR / "bowlers.csv"
INNINGS_FILE = DATA_DIR / "innings.csv"
DELIVERIES_FILE = DATA_DIR / "deliveries.csv"
FIELDING_FILE = DATA_DIR / "fielding_stats.csv"
TEAM_STATS_FILE = DATA_DIR / "team_stats.csv"
MATCH_BATTING_FILE = DATA_DIR / "match_batting.csv"
MATCH_BOWLING_FILE = DATA_DIR / "match_bowling.csv"
METADATA_FILE = DATA_DIR / "dataset_metadata.csv"
CHAT_FILE = DATA_DIR / "chat_history.csv"

MATCH_COLUMNS = ["date", "format", "team", "opponent", "venue", "runs", "wickets", "overs", "run_rate", "result", "player_of_match", "match_id", "stage"]
PLAYER_COLUMNS = ["player", "team", "role", "matches", "runs", "average", "strike_rate", "fifties", "hundreds", "innings", "not_outs", "balls_faced", "fours", "sixes", "highest_score"]
BOWLER_COLUMNS = ["bowler", "team", "matches", "innings", "overs", "runs_conceded", "wickets", "economy", "average", "strike_rate", "best_figures", "four_wicket_hauls", "five_wicket_hauls", "balls_bowled"]
INNINGS_COLUMNS = ["match_id", "date", "innings", "batting_team", "bowling_team", "runs", "wickets", "legal_balls", "overs", "run_rate", "fours", "sixes", "extras", "dot_balls"]
DELIVERY_COLUMNS = ["match_id", "date", "innings", "batting_team", "bowling_team", "over", "ball", "batter", "bowler", "non_striker", "batter_runs", "extras", "total_runs", "wides", "noballs", "byes", "legbyes", "penalty", "is_four", "is_six", "wicket_kind", "player_out", "fielders"]
FIELDING_COLUMNS = ["player", "team", "matches", "catches", "stumpings", "run_outs"]
TEAM_STATS_COLUMNS = ["team", "matches_played", "wins", "losses", "ties", "no_results", "points", "runs_scored", "legal_balls_faced", "runs_conceded", "legal_balls_bowled", "nrr_balls_faced", "nrr_balls_bowled", "net_run_rate"]
MATCH_BATTING_COLUMNS = ["match_id", "date", "innings", "team", "opponent", "player", "runs", "balls_faced", "fours", "sixes", "strike_rate", "dismissal"]
MATCH_BOWLING_COLUMNS = ["match_id", "date", "innings", "team", "opponent", "bowler", "overs", "runs_conceded", "wickets", "economy", "dots", "fours_conceded", "sixes_conceded"]
METADATA_COLUMNS = ["season", "source", "retrieved_at", "matches", "first_match", "last_match"]
CHAT_COLUMNS = ["timestamp", "question", "answer", "mode"]


def _load_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        frame = pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[columns]


def _coerce_numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return frame


def load_matches() -> pd.DataFrame:
    return _coerce_numeric(_load_csv(MATCHES_FILE, MATCH_COLUMNS), ["runs", "wickets", "overs", "run_rate"])


def load_players() -> pd.DataFrame:
    return _coerce_numeric(_load_csv(PLAYERS_FILE, PLAYER_COLUMNS), ["matches", "runs", "average", "strike_rate", "fifties", "hundreds", "innings", "not_outs", "balls_faced", "fours", "sixes", "highest_score"])


def load_bowlers() -> pd.DataFrame:
    return _coerce_numeric(_load_csv(BOWLERS_FILE, BOWLER_COLUMNS), ["matches", "innings", "runs_conceded", "wickets", "economy", "average", "strike_rate", "four_wicket_hauls", "five_wicket_hauls", "balls_bowled"])


def load_innings() -> pd.DataFrame:
    frame = _load_csv(INNINGS_FILE, INNINGS_COLUMNS)
    return _coerce_numeric(frame, ["innings", "runs", "wickets", "legal_balls", "overs", "run_rate", "fours", "sixes", "extras", "dot_balls"])


def load_deliveries() -> pd.DataFrame:
    frame = _load_csv(DELIVERIES_FILE, DELIVERY_COLUMNS)
    return _coerce_numeric(frame, ["innings", "over", "batter_runs", "extras", "total_runs", "wides", "noballs", "byes", "legbyes", "penalty", "is_four", "is_six"])


def load_fielding_stats() -> pd.DataFrame:
    frame = _load_csv(FIELDING_FILE, FIELDING_COLUMNS)
    return _coerce_numeric(frame, ["matches", "catches", "stumpings", "run_outs"])


def load_team_stats() -> pd.DataFrame:
    frame = _load_csv(TEAM_STATS_FILE, TEAM_STATS_COLUMNS)
    return _coerce_numeric(frame, ["matches_played", "wins", "losses", "ties", "no_results", "points", "runs_scored", "legal_balls_faced", "runs_conceded", "legal_balls_bowled", "nrr_balls_faced", "nrr_balls_bowled", "net_run_rate"])


def load_match_batting() -> pd.DataFrame:
    frame = _load_csv(MATCH_BATTING_FILE, MATCH_BATTING_COLUMNS)
    return _coerce_numeric(frame, ["innings", "runs", "balls_faced", "fours", "sixes", "strike_rate"])


def load_match_bowling() -> pd.DataFrame:
    frame = _load_csv(MATCH_BOWLING_FILE, MATCH_BOWLING_COLUMNS)
    return _coerce_numeric(frame, ["innings", "overs", "runs_conceded", "wickets", "economy", "dots", "fours_conceded", "sixes_conceded"])


def summarize_overs(deliveries: pd.DataFrame) -> pd.DataFrame:
    if deliveries.empty:
        return pd.DataFrame()

    over_rows = deliveries.copy()
    over_rows["legal_ball"] = over_rows["wides"].eq(0) & over_rows["noballs"].eq(0)
    over_rows["dot_ball"] = over_rows["total_runs"].eq(0) & over_rows["legal_ball"]
    over_rows["wicket_count"] = over_rows["wicket_kind"].fillna("").map(
        lambda kinds: sum(kind.strip().casefold() != "retired hurt" for kind in str(kinds).split(";") if kind.strip())
    )
    summary = over_rows.groupby(
        ["innings", "batting_team", "bowling_team", "over"], as_index=False, sort=True
    ).agg(
        runs=("total_runs", "sum"),
        wickets=("wicket_count", "sum"),
        legal_balls=("legal_ball", "sum"),
        dot_balls=("dot_ball", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        extras=("extras", "sum"),
    )
    summary["over"] += 1
    return summary.rename(columns={
        "innings": "Innings", "batting_team": "Batting team", "bowling_team": "Bowling team",
        "over": "Over", "runs": "Runs", "wickets": "Wickets", "legal_balls": "Legal balls",
        "dot_balls": "Dot balls", "fours": "Fours", "sixes": "Sixes", "extras": "Extras",
    })


def load_dataset_metadata() -> pd.DataFrame:
    return _load_csv(METADATA_FILE, METADATA_COLUMNS)


def load_chat_history() -> pd.DataFrame:
    empty_history = pd.DataFrame(columns=CHAT_COLUMNS)
    if not CHAT_FILE.exists():
        return empty_history
    try:
        frame = pd.read_csv(CHAT_FILE)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return empty_history

    if not set(CHAT_COLUMNS).issubset(frame.columns):
        try:
            legacy = pd.read_csv(CHAT_FILE, header=None)
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            return empty_history
        if legacy.shape[1] != len(CHAT_COLUMNS):
            return empty_history
        legacy.columns = CHAT_COLUMNS
        if not pd.to_datetime(legacy["timestamp"], errors="coerce", utc=True).notna().any():
            return empty_history
        frame = legacy
        frame.to_csv(CHAT_FILE, index=False)

    frame = frame[CHAT_COLUMNS].dropna(subset=["question", "answer"])
    current_mode = frame["mode"].fillna("").astype(str).str.contains("IPL 2026", case=False)
    frame = frame[current_mode]
    return frame.reset_index(drop=True)


def append_chat(question: str, answer: str, mode: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([{
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "mode": mode,
    }])
    row.to_csv(CHAT_FILE, mode="a", header=not CHAT_FILE.exists(), index=False)


def clear_chat_history() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=CHAT_COLUMNS).to_csv(CHAT_FILE, index=False)
