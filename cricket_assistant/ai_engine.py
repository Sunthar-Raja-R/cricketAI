from __future__ import annotations

import os
import re

import pandas as pd

from cricket_assistant.data_store import summarize_overs


MAX_CONTEXT_ROWS = 40


def _mentioned_values(frame: pd.DataFrame, column: str, text: str) -> list[str]:
    if frame.empty or column not in frame:
        return []
    query = text.casefold()
    values = [str(value) for value in frame[column].dropna().unique()]
    direct = [
        value
        for value in values
        if len(value) >= 3 and value.casefold() in query
    ]
    if direct or column not in {"player", "bowler"}:
        return direct

    query_words = set(re.findall(r"[a-z0-9]+", query))
    surname_counts: dict[str, int] = {}
    for value in values:
        surname = re.findall(r"[a-z0-9]+", value.casefold())[-1]
        surname_counts[surname] = surname_counts.get(surname, 0) + 1
    return [
        str(value)
        for value in values
        if (surname := re.findall(r"[a-z0-9]+", value.casefold())[-1]) in query_words
        and surname_counts[surname] == 1
    ]


def _mentioned_teams(matches: pd.DataFrame, text: str) -> list[str]:
    return list(dict.fromkeys(
        name
        for column in ("team", "opponent")
        for name in _mentioned_values(matches, column, text)
    ))


def _match_context(matches: pd.DataFrame, reference: str) -> pd.DataFrame:
    if matches.empty:
        return matches
    date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", reference)
    selected = matches.copy()
    match_id = re.search(r"\bmatch[_\s-]*id\s*[:#=]?\s*(\d+)\b", reference, re.IGNORECASE)
    if match_id and "match_id" in selected:
        id_matches = selected[selected["match_id"].astype(str).eq(match_id.group(1))]
        if not id_matches.empty:
            selected = id_matches
    if date:
        selected = selected[selected["date"].astype(str).str[:10].eq(date.group(0))]

    team_names = _mentioned_teams(matches, reference)
    if len(team_names) >= 2:
        selected = selected[
            selected.apply(
                lambda row: all(
                    team.casefold() in f"{row.get('team', '')} {row.get('opponent', '')}".casefold()
                    for team in team_names
                ),
                axis=1,
            )
        ]
    return selected


def _csv_text(frame: pd.DataFrame | None, columns: list[str] | None = None, limit: int = MAX_CONTEXT_ROWS) -> str:
    if frame is None or frame.empty:
        return "(no matching records)"
    available = [column for column in columns or frame.columns.tolist() if column in frame.columns]
    if not available:
        return "(no matching records)"
    return frame[available].head(limit).to_csv(index=False)


def _select_batters(players: pd.DataFrame, reference: str, question: str) -> pd.DataFrame:
    mentioned = _mentioned_values(players, "player", reference)
    if mentioned:
        return players[players["player"].isin(mentioned)]
    query = question.casefold()
    metric = "sixes" if "six" in query else "strike_rate" if "strike rate" in query else "runs"
    return players.sort_values(metric, ascending=False).head(20) if metric in players else players.head(20)


def _select_bowlers(bowlers: pd.DataFrame, reference: str, question: str) -> pd.DataFrame:
    mentioned = _mentioned_values(bowlers, "bowler", reference)
    if mentioned:
        return bowlers[bowlers["bowler"].isin(mentioned)]
    query = question.casefold()
    metric = "economy" if "economy" in query else "average" if "average" in query else "wickets"
    return bowlers.sort_values(metric, ascending=metric in {"economy", "average"}).head(20) if metric in bowlers else bowlers.head(20)


def _recent_turns(history: pd.DataFrame | None) -> str:
    if history is None or history.empty:
        return "No previous conversation."
    return "\n".join(
        f"User: {row.question}\nAssistant: {str(row.answer)[:700]}"
        for row in history.tail(6).itertuples(index=False)
    )


def _context_prompt(
    question: str,
    matches: pd.DataFrame,
    players: pd.DataFrame,
    bowlers: pd.DataFrame,
    history: pd.DataFrame | None,
    innings: pd.DataFrame | None,
    deliveries: pd.DataFrame | None,
    fielding: pd.DataFrame | None,
    teams: pd.DataFrame | None,
    match_batting: pd.DataFrame | None,
    match_bowling: pd.DataFrame | None,
    metadata: pd.DataFrame | None,
) -> str:
    history_text = _recent_turns(history)
    reference = f"{history_text}\n{question}"
    query = question.casefold()

    season_winner_question = "ipl" in query and bool(re.search(
        r"\b(?:who|which team)\b.{0,50}\b(?:won|winner|champion|champions)\b|"
        r"\b(?:winner|champion|champions)\b.{0,50}\bipl\b",
        query,
    ))
    if season_winner_question:
        playoffs = matches[matches["stage"].fillna("").astype(str).str.casefold().eq("playoffs")] if "stage" in matches else pd.DataFrame()
        final = playoffs.sort_values("date").tail(1) if not playoffs.empty else pd.DataFrame()
        final_id = set(final["match_id"].astype(str)) if not final.empty and "match_id" in final else set()
        final_innings = innings[innings["match_id"].astype(str).isin(final_id)] if innings is not None and final_id else pd.DataFrame()
        return f"""You are Boundary, an IPL 2026 analyst. Answer the user's season-winner question using only the final match record below.

State the champion and the final opponent/result. The result field identifies the winning team. Do not confuse the league-stage points leader with the IPL champion. If no playoff final record is supplied, say the winner cannot be confirmed from these records.

SOURCE:\n{_csv_text(metadata, limit=1)}

IPL 2026 FINAL:\n{_csv_text(final, limit=1)}

FINAL INNINGS:\n{_csv_text(final_innings, limit=2)}

RECENT CONVERSATION:\n{history_text}

QUESTION:\n{question}
"""

    match_statistics_question = any(term in query for term in ("stat", "scorecard", "full detail", "all detail", "ball by ball", "ball-by-ball", "ballbyball", "over by over")) and "match" in query
    if match_statistics_question:
        final_reference = "final" in query
        date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", query)
        team_names = _mentioned_teams(matches, query)
        if not date_match and not team_names and not final_reference:
            date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", reference)
            team_names = _mentioned_teams(matches, reference)
        if final_reference and not date_match:
            playoffs = matches[matches["stage"].fillna("").astype(str).str.casefold().eq("playoffs")] if "stage" in matches else pd.DataFrame()
            candidates = playoffs.sort_values("date").tail(1) if not playoffs.empty else pd.DataFrame()
        else:
            candidates = _match_context(matches, reference)

        has_fixture_reference = bool(date_match) or len(team_names) >= 2 or final_reference or bool(re.search(r"\bmatch[_\s-]*id\s*[:#=]?\s*\d+\b", reference, re.IGNORECASE))
        unique_match = candidates if has_fixture_reference and len(candidates) == 1 else pd.DataFrame()
        match_ids = set(unique_match["match_id"].astype(str)) if not unique_match.empty and "match_id" in unique_match else set()
        match_innings = innings[innings["match_id"].astype(str).isin(match_ids)].sort_values("innings") if innings is not None and match_ids else pd.DataFrame()
        match_batting_rows = match_batting[match_batting["match_id"].astype(str).isin(match_ids)].sort_values(["innings", "runs"], ascending=[True, False]) if match_batting is not None and match_ids else pd.DataFrame()
        match_bowling_rows = match_bowling[match_bowling["match_id"].astype(str).isin(match_ids)].sort_values(["innings", "wickets", "economy"], ascending=[True, False, True]) if match_bowling is not None and match_ids else pd.DataFrame()
        match_deliveries = deliveries[deliveries["match_id"].astype(str).isin(match_ids)].sort_values(["innings", "over", "ball"]) if deliveries is not None and match_ids else pd.DataFrame()
        over_summary = summarize_overs(match_deliveries)
        include_ball_by_ball = any(term in query for term in ("ball by ball", "ball-by-ball", "ballbyball"))
        if len(candidates) > 1:
            selection_note = "Several matches match those details. Ask the user for the date before giving match statistics."
        elif unique_match.empty:
            selection_note = "No unique match was identified. Ask for a date, both teams, or whether the user means the IPL 2026 final. Do not say the statistics are absent from the dataset."
        else:
            selection_note = "The selected match has full innings, batting, bowling, over, and delivery records. Answer from those records; do not claim those statistics are missing."
        delivery_section = f"\nBALL-BY-BALL DELIVERIES:\n{_csv_text(match_deliveries, limit=300)}" if include_ball_by_ball else ""
        return f"""You are Boundary, an IPL 2026 match analyst. The user is asking for a complete match-statistics report, not only the winner.

{selection_note}
For a selected match, report the match header and result, each innings total, complete batting scorecards, complete bowling figures, and over-by-over scoring. Include runs, dismissals, balls, fours, sixes, extras, dot balls, economy, wickets, and player of the match when present. Use only supplied records and preserve their values. Do not replace available scorecards with a statement that the data is missing. If the user explicitly asks ball by ball, use the delivery table as well.

MATCH RECORD:\n{_csv_text(unique_match, limit=1)}

INNINGS TOTALS:\n{_csv_text(match_innings, limit=4)}

FULL BATTING SCORECARD:\n{_csv_text(match_batting_rows, limit=50)}

FULL BOWLING FIGURES:\n{_csv_text(match_bowling_rows, limit=50)}

OVER-BY-OVER SUMMARY:\n{_csv_text(over_summary, limit=80)}{delivery_section}

QUESTION:\n{question}
"""

    match_result_question = "match" in query and bool(re.search(r"\bwho\s+won\b|\bmatch\s+result\b", query))
    if match_result_question:
        candidates = _match_context(matches, reference)
        date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", reference)
        team_names = _mentioned_teams(matches, reference)
        has_fixture = bool(date_match) or len(team_names) >= 2
        if has_fixture:
            unique_match = candidates if len(candidates) == 1 else pd.DataFrame()
            match_ids = set(unique_match["match_id"].astype(str)) if not unique_match.empty and "match_id" in unique_match else set()
            match_innings = innings[innings["match_id"].astype(str).isin(match_ids)] if innings is not None and match_ids else pd.DataFrame()
            if len(candidates) > 1:
                note = "Multiple fixtures match these details. Ask which date the user means; do not choose one."
            elif unique_match.empty:
                note = "No match record matches these details. Say the result is not present in the loaded IPL 2026 records."
            else:
                note = "Use the result field in the single matching record to identify the winner and margin."
            return f"""You are Boundary, an IPL 2026 analyst. Answer this match-result question from the records below only.

{note} Keep the answer to one or two sentences. Do not use unrelated season leaders or infer a result.

MATCH RECORD:\n{_csv_text(candidates, limit=6)}

INNINGS:\n{_csv_text(match_innings, limit=2)}

QUESTION:\n{question}
"""

    selected_matches = _match_context(matches, reference)
    has_date = bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", reference))
    team_names = _mentioned_teams(matches, reference)
    has_match_id = bool(re.search(r"\bmatch[_\s-]*id\s*[:#=]?\s*\d+\b", reference, re.IGNORECASE))
    match_selected = not selected_matches.empty and (has_date or len(team_names) >= 2 or has_match_id)
    selected_ids = set(selected_matches["match_id"].astype(str)) if match_selected and "match_id" in selected_matches else set()
    if not match_selected:
        selected_matches = matches.sort_values("date", ascending=False).head(20) if "date" in matches else matches.head(20)

    match_specific = any(term in query for term in ("this match", "that match", "in this match", "which match", "match on", "match between")) or (
        "match" in query and any(term in query for term in ("six", "player of the match", "most runs", "highest score", "scorecard"))
    )
    ambiguous_match = match_selected and match_specific and not has_date and len(selected_matches) > 1
    if ambiguous_match:
        selected_ids = set()

    if match_batting is None:
        selected_batting = pd.DataFrame()
    elif selected_ids:
        selected_batting = match_batting[match_batting["match_id"].astype(str).isin(selected_ids)]
    elif match_specific:
        selected_batting = pd.DataFrame()
    elif any(term in query for term in ("six", "batter", "run", "innings")):
        selected_batting = match_batting.sort_values("sixes" if "six" in query else "runs", ascending=False).head(30)
    else:
        selected_batting = pd.DataFrame()

    if match_bowling is None:
        selected_match_bowling = pd.DataFrame()
    elif selected_ids:
        selected_match_bowling = match_bowling[match_bowling["match_id"].astype(str).isin(selected_ids)]
    elif any(term in query for term in ("bowler", "wicket", "economy", "bowling")) and not match_specific:
        selected_match_bowling = match_bowling.sort_values("wickets", ascending=False).head(25)
    else:
        selected_match_bowling = pd.DataFrame()

    selected_innings = innings[innings["match_id"].astype(str).isin(selected_ids)] if innings is not None and selected_ids else pd.DataFrame()
    selected_deliveries = pd.DataFrame()
    if deliveries is not None and selected_ids and any(term in query for term in ("over", "delivery", "ball by ball", "ball-by-ball", "ballbyball", "partnership")):
        selected_deliveries = deliveries[deliveries["match_id"].astype(str).isin(selected_ids)]
        requested_over = re.search(r"\bover(?:_number)?\s*(?:number\s*)?(?:#|no\.?\s*)?(\d+)\b", query)
        requested_innings = re.search(r"\binnings\s*(\d+)\b|\b(\d+)(?:st|nd)\s+innings\b", query)
        if requested_over:
            # Cricsheet stores overs zero-based; user-facing over numbers are one-based.
            selected_deliveries = selected_deliveries[selected_deliveries["over"].eq(int(requested_over.group(1)) - 1)]
        if requested_innings:
            innings_number = next(group for group in requested_innings.groups() if group is not None)
            selected_deliveries = selected_deliveries[selected_deliveries["innings"].eq(int(innings_number))]

    selected_players = _select_batters(players, reference, question)
    if team_names:
        selected_players = players[players["team"].isin(team_names)].sort_values("runs", ascending=False).head(30)
    selected_bowlers = _select_bowlers(bowlers, reference, question)
    if team_names:
        selected_bowlers = bowlers[bowlers["team"].isin(team_names)].sort_values("wickets", ascending=False).head(30)

    team_table = teams[teams["team"].isin(team_names)] if teams is not None and team_names else teams
    fielding_table = fielding.sort_values("catches", ascending=False).head(15) if fielding is not None else pd.DataFrame()
    if fielding is not None and any(term in query for term in ("catch", "stumping", "run out", "fielding")):
        named_fielders = _mentioned_values(fielding, "player", reference)
        if named_fielders:
            fielding_table = fielding[fielding["player"].isin(named_fielders)]

    source_note = _csv_text(metadata, limit=1) if metadata is not None else "Cricsheet IPL 2026 source metadata unavailable."
    if ambiguous_match:
        match_hint = "Several IPL 2026 matches match the named teams; ask which date or fixture the user means before giving a match-specific statistic."
    elif not match_selected and match_specific:
        match_hint = "No unique match was identified from the question or recent conversation; ask the user which match they mean."
    else:
        match_hint = "Use the match rows only when they identify the requested game; do not treat a recent match as the requested match without evidence."

    return f"""You are Boundary, an IPL 2026 cricket analyst. Answer using only the supplied IPL 2026 CSV records and the recent conversation.

Answer factual questions with exact supplied values. For match-specific questions, cite the date, teams, innings or match_id used. The match_batting table already contains per-player match totals, so determine most sixes by comparing its sixes column for the identified match. Use player_of_match from the match table for the award. Do not recalculate or guess a missing value.

For strategy questions, make useful conditional recommendations grounded in team/player/bowling/venue evidence. Explain the evidence, identify uncertainty (pitch, toss, injuries, and live form are not supplied), and never promise a win or present a prediction as certain. Separate measured facts from your tactical judgment. If the match or stat is not represented, say what is missing and ask one concise clarification where needed.

The CSV statistics are season-derived from the Cricsheet archive, not live data. Preserve the distinction between batter runs and team runs, batter balls faced and legal balls, and wickets credited to a bowler versus other dismissals. Do not infer omitted records. Keep answers clear and concise.

DATA PROVENANCE:\n{source_note}

MATCH SELECTION NOTE:\n{match_hint}

RECENT CONVERSATION:\n{history_text}

MATCH SUMMARIES:\n{_csv_text(selected_matches, limit=74)}

INNINGS TOTALS FOR IDENTIFIED MATCH:\n{_csv_text(selected_innings, limit=20)}

PLAYER SEASON BATTING:\n{_csv_text(selected_players, limit=30)}

PLAYER TOTALS BY MATCH:\n{_csv_text(selected_batting, limit=MAX_CONTEXT_ROWS)}

BOWLER SEASON FIGURES:\n{_csv_text(selected_bowlers, limit=30)}

BOWLER FIGURES BY MATCH:\n{_csv_text(selected_match_bowling, limit=MAX_CONTEXT_ROWS)}

TEAM SEASON TABLE:\n{_csv_text(team_table, limit=10)}

FIELDING FIGURES:\n{_csv_text(fielding_table, limit=20)}

DELIVERIES FOR IDENTIFIED MATCH (only when requested; over numbers in this table are zero-based, so add 1 for the user's over_number):\n{_csv_text(selected_deliveries, limit=300)}

CURRENT QUESTION:\n{question}
"""


def answer_question(
    question: str,
    matches: pd.DataFrame,
    players: pd.DataFrame,
    bowlers: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
    *,
    innings: pd.DataFrame | None = None,
    deliveries: pd.DataFrame | None = None,
    fielding: pd.DataFrame | None = None,
    teams: pd.DataFrame | None = None,
    match_batting: pd.DataFrame | None = None,
    match_bowling: pd.DataFrame | None = None,
    metadata: pd.DataFrame | None = None,
) -> tuple[str, str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to .env or Streamlit secrets to ask the analyst.")

    from google import genai
    from google.genai import types

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    timeout_ms = max(1_000, min(int(os.getenv("GEMINI_TIMEOUT_MS", "15000")), 120_000))
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=timeout_ms,
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=0.5,
                max_delay=1.0,
                http_status_codes=[429, 500, 502, 503, 504],
            ),
        ),
    )
    prompt = _context_prompt(
        question, matches, players, bowlers if bowlers is not None else pd.DataFrame(), history,
        innings, deliveries, fielding, teams, match_batting, match_bowling, metadata,
    )
    response = client.models.generate_content(model=model, contents=prompt)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response. Please retry.")
    return text, f"Gemini · IPL 2026 · {model}"
