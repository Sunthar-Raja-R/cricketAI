from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MATCHES_FILE = DATA_DIR / "matches.csv"
PLAYERS_FILE = DATA_DIR / "players.csv"
BOWLERS_FILE = DATA_DIR / "bowlers.csv"
DEMO_MATCHES_FILE = DATA_DIR / "demo_matches.csv"
DEMO_PLAYERS_FILE = DATA_DIR / "demo_players.csv"
DEMO_BOWLERS_FILE = DATA_DIR / "demo_bowlers.csv"
CHAT_FILE = DATA_DIR / "chat_history.csv"

MATCH_COLUMNS = ["date", "format", "team", "opponent", "venue", "runs", "wickets", "overs", "run_rate", "result", "player_of_match"]
PLAYER_COLUMNS = ["player", "team", "role", "matches", "runs", "average", "strike_rate", "fifties", "hundreds"]
BOWLER_COLUMNS = ["bowler", "team", "matches", "innings", "overs", "runs_conceded", "wickets", "economy", "average", "strike_rate", "best_figures", "four_wicket_hauls", "five_wicket_hauls"]
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


def _load_csv_files(paths: list[Path], columns: list[str]) -> pd.DataFrame:
    frames = [_load_csv(path, columns) for path in paths]
    return pd.concat(frames, ignore_index=True)


def load_matches() -> pd.DataFrame:
    frame = _load_csv_files([MATCHES_FILE, DEMO_MATCHES_FILE], MATCH_COLUMNS)
    for column in ("runs", "wickets", "overs", "run_rate"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return frame


def load_players() -> pd.DataFrame:
    frame = _load_csv_files([PLAYERS_FILE, DEMO_PLAYERS_FILE], PLAYER_COLUMNS)
    for column in ("matches", "runs", "average", "strike_rate", "fifties", "hundreds"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return frame


def load_bowlers() -> pd.DataFrame:
    frame = _load_csv_files([BOWLERS_FILE, DEMO_BOWLERS_FILE], BOWLER_COLUMNS)
    for column in ("matches", "innings", "runs_conceded", "wickets", "economy", "average", "strike_rate", "four_wicket_hauls", "five_wicket_hauls"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    return frame


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
    return frame.reset_index(drop=True)


def append_chat(question: str, answer: str, mode: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    row = pd.DataFrame([{
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "mode": mode,
    }])
    history = pd.concat([load_chat_history(), row], ignore_index=True)
    history.to_csv(CHAT_FILE, index=False)


def clear_chat_history() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=CHAT_COLUMNS).to_csv(CHAT_FILE, index=False)
