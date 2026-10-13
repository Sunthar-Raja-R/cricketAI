from __future__ import annotations

import os
import re

import pandas as pd


def _mentioned_rows(frame: pd.DataFrame, columns: list[str], query: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        if column not in frame.columns:
            continue
        values = frame[column].fillna("").astype(str).str.strip().str.casefold()
        for value in values.unique():
            if len(value) >= 3 and value in query:
                mask |= values.eq(value)
    return frame[mask].copy()


def _mentioned_teams(question: str, *frames: pd.DataFrame) -> list[str]:
    query = question.casefold()
    teams: set[str] = set()
    for frame in frames:
        for column in ("team", "opponent"):
            if column in frame.columns:
                teams.update(str(value) for value in frame[column].dropna().unique())
    return [team for team in teams if len(team) >= 3 and team.casefold() in query]


def _filter_team(frame: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    if not teams or frame.empty:
        return frame.copy()
    mask = pd.Series(False, index=frame.index)
    for column in ("team", "opponent"):
        if column in frame.columns:
            mask |= frame[column].fillna("").astype(str).str.casefold().isin({team.casefold() for team in teams})
    return frame[mask].copy()


def _top_count(query: str, default: int = 1) -> int:
    match = re.search(r"\btop\s+(\d+)\b", query)
    return min(int(match.group(1)), 5) if match else default


def _is_run_rate_question(query: str) -> bool:
    return bool(re.search(r"\b(?:average|avg)\s+run\s+rate\b|\brun[ -]?rate\b", query))


def _local_answer(
    question: str,
    matches: pd.DataFrame,
    players: pd.DataFrame,
    bowlers: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
) -> str:
    bowlers = bowlers if bowlers is not None else pd.DataFrame()
    query = question.casefold()
    lookup_query = query
    follow_up_phrases = ("what about", "and his", "and her", "their", "that player", "what was his", "what was her")
    if history is not None and not history.empty and any(phrase in query for phrase in follow_up_phrases):
        previous = history.iloc[-1]
        lookup_query = f"{previous.get('question', '')} {previous.get('answer', '')} {question}".casefold()

    if matches.empty and players.empty and bowlers.empty:
        return "The local scorebook is empty. Add match, batting, and bowling rows under `data/`, then ask again."

    teams = _mentioned_teams(lookup_query, matches, players, bowlers)
    count = _top_count(query)
    bowling_intent = any(term in query for term in ("bowler", "bowling", "wicket", "economy", "best figures", "haul"))

    if bowling_intent:
        if bowlers.empty:
            return "There are no bowling records loaded yet. Add bowling figures to `data/bowlers.csv`."
        named_bowlers = _mentioned_rows(bowlers, ["bowler"], lookup_query)
        selected = named_bowlers if not named_bowlers.empty else _filter_team(bowlers, teams)
        if selected.empty:
            selected = bowlers.copy()
        metric = "economy" if "economy" in query else "average" if "average" in query else "wickets"
        selected = selected.sort_values(metric, ascending=metric in ("economy", "average"))
        if len(named_bowlers) > 1:
            count = max(count, len(named_bowlers))
        records = selected.head(count)
        if len(named_bowlers) == 1:
            row = records.iloc[0]
            return (
                f"In the supplied sample scorebook, {row['bowler']} ({row['team']}) has "
                f"{int(row['wickets'])} wickets in {int(row['matches'])} matches, with an economy of "
                f"{float(row['economy']):.2f}, bowling average {float(row['average']):.2f}, "
                f"and best figures {row['best_figures']}. Supplemental demo rows are illustrative, not verified career stats."
            )
        summaries = [f"{row.bowler} ({row.team}): {int(row.wickets)} wickets, economy {float(row.economy):.2f}" for row in records.itertuples(index=False)]
        label = f" for {', '.join(teams)}" if teams else ""
        return f"Bowling leaders{label}, ranked by {metric}, in the supplied sample scorebook: " + "; ".join(summaries) + ". Demo figures are illustrative, not verified career stats."

    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    if date_match and any(term in query for term in ("match", "game", "played", "happen")):
        match_date = date_match.group(1)
        date_rows = matches[matches["date"].fillna("").astype(str).str[:10].eq(match_date)]
        if date_rows.empty:
            return f"I could not find a match dated {match_date} in the supplied scorebook."
        details = [
            f"{row.team} vs {row.opponent} ({row.format}) at {row.venue}: "
            f"{int(row.runs)}/{int(row.wickets)} in {row.overs} overs; {row.result}; "
            f"player of the match: {row.player_of_match}"
            for row in date_rows.itertuples(index=False)
        ]
        return f"On {match_date}, the supplied scorebook lists " + "; ".join(details) + ". Supplemental match rows may be illustrative, not verified historical results."

    if _is_run_rate_question(query):
        selected_matches = _filter_team(matches, teams)
        if selected_matches.empty:
            return "There are no matching records to calculate a run rate from."
        rates = pd.to_numeric(selected_matches["run_rate"], errors="coerce").dropna()
        if rates.empty:
            return "Run-rate values are missing from the matching records."
        mean_rate = rates.mean()
        label = f" for {', '.join(teams)}" if teams else ""
        return (
            f"The average run rate{label} is {mean_rate:.2f} runs per over across "
            f"{len(rates)} supplied match records. Supplemental demo match rows are illustrative, not verified results."
        )

    named_players = _mentioned_rows(players, ["player"], lookup_query)
    run_scorer_intent = bool(re.search(r"\b(?:run|runs)[ -]+scorer\b|\b(?:top|leading)\s+(?:run\s+)?scorer\b", query))
    batting_intent = run_scorer_intent or any(term in query for term in ("batter", "batsman", "batting", "runs", "strike rate", "centur", "fift", "batting average"))
    if not named_players.empty or batting_intent:
        selected = named_players if not named_players.empty else _filter_team(players, teams)
        if selected.empty:
            selected = players.copy()
        metric = "hundreds" if "centur" in query or "hundred" in query else "fifties" if "fift" in query else "strike_rate" if "strike rate" in query else "average" if "average" in query else "runs"
        selected = selected.sort_values(metric, ascending=False)
        if len(named_players) > 1:
            count = max(count, len(named_players))
        records = selected.head(count)
        if len(named_players) == 1:
            row = records.iloc[0]
            return (
                f"In the supplied sample scorebook, {row['player']} ({row['team']}) has {int(row['runs'])} runs "
                f"in {int(row['matches'])} matches, average {float(row['average']):.2f}, strike rate "
                f"{float(row['strike_rate']):.2f}, {int(row['hundreds'])} hundreds, and {int(row['fifties'])} fifties. "
                "Treat supplemental demo figures as illustrative, not verified career stats."
            )
        if run_scorer_intent and not records.empty:
            row = records.iloc[0]
            return (
                f"The leading run-scorer in the supplied batting records is {row['player']} ({row['team']}) "
                f"with {int(row['runs'])} runs in {int(row['matches'])} matches, an average of "
                f"{float(row['average']):.2f}, and a strike rate of {float(row['strike_rate']):.2f}. "
                "Supplemental demo statistics are synthetic, not verified career totals."
            )
        summaries = [f"{row.player} ({row.team}): {int(row.runs)} runs, average {float(row.average):.2f}, SR {float(row.strike_rate):.2f}" for row in records.itertuples(index=False)]
        label = f" for {', '.join(teams)}" if teams else ""
        return f"Batting leaders{label}, ranked by {metric.replace('_', ' ')}, in the supplied sample scorebook: " + "; ".join(summaries) + ". Supplemental demo figures are illustrative."

    selected_matches = _filter_team(matches, teams)
    if any(term in query for term in ("t20", "odi", "test")):
        formats = []
        if "t20" in query:
            formats.extend(("T20", "T20I"))
        if "odi" in query:
            formats.append("ODI")
        if "test" in query:
            formats.append("Test")
        if formats:
            format_mask = selected_matches["format"].fillna("").astype(str).str.casefold().isin({name.casefold() for name in formats})
            selected_matches = selected_matches[format_mask]
    if selected_matches.empty:
        selected_matches = matches.copy()
    if not selected_matches.empty:
        if "highest" in query or "most runs" in query or "biggest score" in query:
            row = selected_matches.sort_values("runs", ascending=False).iloc[0]
            return (
                f"The highest listed innings{f' for {', '.join(teams)}' if teams else ''} is "
                f"{int(row['runs'])}/{int(row['wickets'])} by {row['team']} against {row['opponent']} "
                f"({row['format']}, {row['venue']}, {row['date']}). Demo match rows are illustrative examples."
            )
        win_count = int(selected_matches["result"].fillna("").astype(str).str.startswith("Won", na=False).sum())
        mean_rate = pd.to_numeric(selected_matches["run_rate"], errors="coerce").mean()
        label = f" for {', '.join(teams)}" if teams else ""
        return (
            f"The supplied scorebook has {len(selected_matches)} match records{label}, "
            f"{win_count} marked as wins, and an average run rate of {mean_rate:.2f}. "
            "Supplemental demo match rows are illustrative, not verified historical results."
        )
    return "I could not find enough data for that question. Try asking about a named batter or bowler, team, format, runs, wickets, or economy."


def _context_rows(
    frame: pd.DataFrame,
    query: str,
    mention_columns: list[str],
    sort_column: str,
    ascending: bool = False,
    limit: int = 35,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    mentioned = _mentioned_rows(frame, mention_columns, query)
    if not mentioned.empty:
        return mentioned.head(limit)
    if sort_column not in frame.columns:
        return frame.head(limit)
    return frame.sort_values(sort_column, ascending=ascending).head(limit)


def answer_question(
    question: str,
    matches: pd.DataFrame,
    players: pd.DataFrame,
    bowlers: pd.DataFrame | None = None,
    history: pd.DataFrame | None = None,
) -> tuple[str, str]:
    bowlers = bowlers if bowlers is not None else pd.DataFrame()
    query = question.casefold()
    requested_date = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    date_lookup = requested_date and any(term in query for term in ("match", "game", "played", "happen"))
    exact_date_rows = pd.DataFrame()
    if date_lookup:
        exact_date_rows = matches[matches["date"].fillna("").astype(str).str[:10].eq(requested_date.group(1))]
        if exact_date_rows.empty:
            return _local_answer(question, matches, players, bowlers, history), "Local CSV analyst · exact date lookup"

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _local_answer(question, matches, players, bowlers, history), "Local CSV analyst · no API key configured"

    try:
        from google import genai
        from google.genai.errors import ServerError

        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        client = genai.Client(api_key=api_key)
        if date_lookup:
            selected_matches = exact_date_rows
        elif _is_run_rate_question(query):
            selected_matches = _filter_team(matches, _mentioned_teams(query, matches))
        else:
            selected_matches = _context_rows(matches, query, ["team", "opponent", "format", "venue", "player_of_match"], "date", limit=35)
        match_context = selected_matches.to_csv(index=False)
        player_metric = "strike_rate" if "strike rate" in query else "average" if "batting average" in query else "runs"
        player_context = _context_rows(players, query, ["player", "team"], player_metric, limit=35).to_csv(index=False)
        bowler_metric = "economy" if "economy" in query else "average" if "bowling average" in query else "wickets"
        bowler_context = _context_rows(bowlers, query, ["bowler", "team"], bowler_metric, ascending=bowler_metric == "economy", limit=35).to_csv(index=False)
        recent_turns = "No earlier chat context."
        if history is not None and not history.empty:
            recent_turns = "\n".join(
                f"User: {row.question}\nAssistant: {str(row.answer)[:500]}"
                for row in history.tail(6).itertuples(index=False)
            )
        prompt = f"""You are Boundary, a careful cricket analyst. Answer the user's question using the supplied scorebook context.
Answer the actual question first. Explain comparisons using the relevant metrics, and show short calculations for aggregate questions.
Do not invent statistics or claim these are live/current results. The supplemental demo CSV records are synthetic illustrative examples, not verified historical cricket data. Describe results as being within this sample scorebook.
If a name or statistic is absent, say it is not in the loaded records. Keep the answer concise and distinguish runs, wickets, average, strike rate, and economy correctly.

RECENT CONVERSATION:
{recent_turns}

MATCH DATA (CSV):
{match_context}

BATTER DATA (CSV):
{player_context}

BOWLER DATA (CSV):
{bowler_context}

CURRENT USER QUESTION: {question}
"""
        try:
            response = client.models.generate_content(model=model, contents=prompt)
        except ServerError:
            response = client.models.generate_content(model=model, contents=prompt)
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("The model returned an empty response.")
        return text, f"Gemini · {model}"
    except Exception as error:
        local = _local_answer(question, matches, players, bowlers, history)
        if type(error).__name__ == "ServerError":
            note = "Gemini returned a server error after one retry; showing the local scorebook answer instead."
        else:
            note = f"Gemini could not respond ({type(error).__name__}); showing the local scorebook answer instead."
        return f"{local}\n\n{note}", "Local CSV fallback"
