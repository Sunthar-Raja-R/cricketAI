from __future__ import annotations

import argparse
import csv
import json
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCE_URL = "https://cricsheet.org/downloads/ipl_json.zip"
SEASON = "2026"

MATCH_FIELDS = ["date", "format", "team", "opponent", "venue", "runs", "wickets", "overs", "run_rate", "result", "player_of_match", "match_id", "stage"]
PLAYER_FIELDS = ["player", "team", "role", "matches", "runs", "average", "strike_rate", "fifties", "hundreds", "innings", "not_outs", "balls_faced", "fours", "sixes", "highest_score"]
BOWLER_FIELDS = ["bowler", "team", "matches", "innings", "overs", "runs_conceded", "wickets", "economy", "average", "strike_rate", "best_figures", "four_wicket_hauls", "five_wicket_hauls", "balls_bowled"]
INNINGS_FIELDS = ["match_id", "date", "innings", "batting_team", "bowling_team", "runs", "wickets", "legal_balls", "overs", "run_rate", "fours", "sixes", "extras", "dot_balls"]
DELIVERY_FIELDS = ["match_id", "date", "innings", "batting_team", "bowling_team", "over", "ball", "batter", "bowler", "non_striker", "batter_runs", "extras", "total_runs", "wides", "noballs", "byes", "legbyes", "penalty", "is_four", "is_six", "wicket_kind", "player_out", "fielders"]
FIELDING_FIELDS = ["player", "team", "matches", "catches", "stumpings", "run_outs"]
TEAM_FIELDS = ["team", "matches_played", "wins", "losses", "ties", "no_results", "points", "runs_scored", "legal_balls_faced", "runs_conceded", "legal_balls_bowled", "nrr_balls_faced", "nrr_balls_bowled", "net_run_rate"]
MATCH_BATTING_FIELDS = ["match_id", "date", "innings", "team", "opponent", "player", "runs", "balls_faced", "fours", "sixes", "strike_rate", "dismissal"]
MATCH_BOWLING_FIELDS = ["match_id", "date", "innings", "team", "opponent", "bowler", "overs", "runs_conceded", "wickets", "economy", "dots", "fours_conceded", "sixes_conceded"]
METADATA_FIELDS = ["season", "source", "retrieved_at", "matches", "first_match", "last_match"]


def _read_archive(archive_path: Path | None) -> zipfile.ZipFile:
    if archive_path is not None:
        return zipfile.ZipFile(archive_path)
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "BoundaryIPLDataImporter/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return zipfile.ZipFile(BytesIO(response.read()))


def _write_csv(filename: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with (DATA_DIR / filename).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _overs(legal_balls: int) -> float:
    return round(legal_balls // 6 + (legal_balls % 6) / 10, 1)


def _fielders(wicket: dict[str, Any]) -> list[str]:
    return [item if isinstance(item, str) else item.get("name", "") for item in wicket.get("fielders", [])]


def _result(info: dict[str, Any]) -> str:
    outcome = info.get("outcome", {})
    winner = outcome.get("winner")
    margin = outcome.get("by", {})
    if winner and margin:
        kind, value = next(iter(margin.items()))
        return f"{winner} won by {value} {kind}"
    if winner:
        return f"{winner} won"
    if outcome.get("result"):
        return str(outcome["result"]).replace("no result", "No result").replace("tie", "Tie")
    return "No result"


def _parse_matches(archive: zipfile.ZipFile) -> list[tuple[str, dict[str, Any]]]:
    matches = []
    for filename in archive.namelist():
        if not filename.endswith(".json"):
            continue
        match = json.loads(archive.read(filename))
        if str(match.get("info", {}).get("season")) == SEASON:
            matches.append((Path(filename).stem, match))
    return sorted(matches, key=lambda item: (item[1]["info"]["dates"][0], item[0]))


def build_csvs(matches: list[tuple[str, dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    innings_rows: list[dict[str, Any]] = []
    delivery_rows: list[dict[str, Any]] = []
    match_batting_rows: list[dict[str, Any]] = []
    match_bowling_rows: list[dict[str, Any]] = []
    batting: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"matches": set(), "innings": set(), "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "scores": defaultdict(int), "outs": set()})
    bowling: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"matches": set(), "innings": set(), "balls": 0, "runs": 0, "wickets": 0, "figures": defaultdict(lambda: [0, 0])})
    fielding: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"matches": set(), "catches": 0, "stumpings": 0, "run_outs": 0})
    team_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"matches_played": 0, "wins": 0, "losses": 0, "ties": 0, "no_results": 0, "points": 0, "runs_scored": 0, "legal_balls_faced": 0, "runs_conceded": 0, "legal_balls_bowled": 0, "nrr_balls_faced": 0, "nrr_balls_bowled": 0})

    for match_id, match in matches:
        info = match["info"]
        date = str(info["dates"][0])
        teams = info.get("teams", [])
        is_league_match = info.get("event", {}).get("match_number") is not None
        stage = "League" if is_league_match else "Playoffs"
        player_of_match = ", ".join(info.get("player_of_match", []))
        innings_summaries = []
        nrr_balls_by_team: dict[str, int] = {}

        for team, names in info.get("players", {}).items():
            for player in names:
                fielding[(player, team)]["matches"].add(match_id)

        for innings_number, innings in enumerate(match.get("innings", []), start=1):
            batting_team = innings["team"]
            bowling_team = next((team for team in teams if team != batting_team), "")
            score = {"runs": 0, "wickets": 0, "legal_balls": 0, "fours": 0, "sixes": 0, "extras": 0, "dot_balls": 0}
            innings_batter_scores: dict[str, int] = defaultdict(int)
            innings_batter_figures: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "dismissal": ""})
            innings_bowler_figures: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0])

            for over in innings.get("overs", []):
                for delivery_number, delivery in enumerate(over.get("deliveries", []), start=1):
                    runs = delivery.get("runs", {})
                    extras = delivery.get("extras", {})
                    batter_runs = int(runs.get("batter", 0))
                    total_runs = int(runs.get("total", 0))
                    wides = int(extras.get("wides", 0))
                    noballs = int(extras.get("noballs", 0))
                    byes = int(extras.get("byes", 0))
                    legbyes = int(extras.get("legbyes", 0))
                    penalty = int(extras.get("penalty", 0))
                    bowler = delivery["bowler"]
                    batter = delivery["batter"]
                    legal = wides == 0 and noballs == 0
                    score["runs"] += total_runs
                    score["extras"] += total_runs - batter_runs
                    score["legal_balls"] += int(legal)
                    score["fours"] += int(batter_runs == 4)
                    score["sixes"] += int(batter_runs == 6)
                    score["dot_balls"] += int(total_runs == 0 and legal)
                    innings_batter_scores[batter] += batter_runs
                    batter_figures = innings_batter_figures[batter]
                    batter_figures["runs"] += batter_runs
                    batter_figures["balls"] += int(wides == 0)
                    batter_figures["fours"] += int(batter_runs == 4)
                    batter_figures["sixes"] += int(batter_runs == 6)

                    batter_record = batting[(batter, batting_team)]
                    batter_record["matches"].add(match_id)
                    batter_record["innings"].add((match_id, innings_number))
                    batter_record["runs"] += batter_runs
                    batter_record["balls"] += int(wides == 0)
                    batter_record["fours"] += int(batter_runs == 4)
                    batter_record["sixes"] += int(batter_runs == 6)
                    batter_record["scores"][(match_id, innings_number)] += batter_runs

                    bowler_record = bowling[(bowler, bowling_team)]
                    bowler_record["matches"].add(match_id)
                    bowler_record["innings"].add((match_id, innings_number))
                    bowler_record["balls"] += int(legal)
                    bowler_record["runs"] += total_runs - byes - legbyes - penalty
                    innings_bowler_figures[bowler][1] += total_runs - byes - legbyes - penalty
                    innings_bowler_figures[bowler][2] += int(legal)
                    innings_bowler_figures[bowler][3] += int(total_runs == 0 and legal)
                    innings_bowler_figures[bowler][4] += int(batter_runs == 4)
                    innings_bowler_figures[bowler][5] += int(batter_runs == 6)

                    wickets = delivery.get("wickets", [])
                    wicket_kinds = []
                    players_out = []
                    fielders_on_delivery = []
                    for wicket in wickets:
                        kind = wicket.get("kind", "")
                        player_out = wicket.get("player_out", "")
                        wicket_kinds.append(kind)
                        players_out.append(player_out)
                        if player_out and kind != "retired hurt":
                            innings_batter_figures[player_out]["dismissal"] = kind
                        if kind != "retired hurt":
                            score["wickets"] += 1
                            if player_out:
                                batting[(player_out, batting_team)]["outs"].add((match_id, innings_number))
                            if kind in {"bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket"}:
                                bowler_record["wickets"] += 1
                                innings_bowler_figures[bowler][0] += 1
                        for fielder in _fielders(wicket):
                            if fielder:
                                fielding_record = fielding[(fielder, bowling_team)]
                                fielding_record["matches"].add(match_id)
                                if kind in {"caught", "caught and bowled"}:
                                    fielding_record["catches"] += 1
                                elif kind == "stumped":
                                    fielding_record["stumpings"] += 1
                                elif kind == "run out":
                                    fielding_record["run_outs"] += 1
                                fielders_on_delivery.append(fielder)

                    delivery_rows.append({
                        "match_id": match_id, "date": date, "innings": innings_number,
                        "batting_team": batting_team, "bowling_team": bowling_team,
                        "over": over.get("over", 0),
                        "ball": delivery.get("actual_delivery", f"{over.get('over', 0)}.{delivery_number}"),
                        "batter": batter, "bowler": bowler, "non_striker": delivery.get("non_striker", ""),
                        "batter_runs": batter_runs, "extras": total_runs - batter_runs, "total_runs": total_runs,
                        "wides": wides, "noballs": noballs, "byes": byes, "legbyes": legbyes, "penalty": penalty,
                        "is_four": int(batter_runs == 4), "is_six": int(batter_runs == 6),
                        "wicket_kind": "; ".join(wicket_kinds), "player_out": "; ".join(players_out),
                        "fielders": "; ".join(fielders_on_delivery),
                    })

            score["run_rate"] = round(score["runs"] * 6 / score["legal_balls"], 2) if score["legal_balls"] else 0
            nrr_balls = score["legal_balls"]
            if score["wickets"] >= 10:
                allocated_overs = innings.get("target", {}).get("overs", info.get("overs", 20))
                nrr_balls = round(float(allocated_overs) * 6)
            nrr_balls_by_team[batting_team] = nrr_balls
            innings_rows.append({
                "match_id": match_id, "date": date, "innings": innings_number,
                "batting_team": batting_team, "bowling_team": bowling_team,
                **score, "overs": _overs(score["legal_balls"]),
            })
            for player, player_runs in innings_batter_scores.items():
                batting[(player, batting_team)]["scores"][(match_id, innings_number)] = player_runs
            for player, figures in innings_batter_figures.items():
                match_batting_rows.append({
                    "match_id": match_id, "date": date, "innings": innings_number,
                    "team": batting_team, "opponent": bowling_team, "player": player,
                    "runs": figures["runs"], "balls_faced": figures["balls"],
                    "fours": figures["fours"], "sixes": figures["sixes"],
                    "strike_rate": round(figures["runs"] * 100 / figures["balls"], 2) if figures["balls"] else 0,
                    "dismissal": figures["dismissal"],
                })
            for bowler, figures in innings_bowler_figures.items():
                bowling[(bowler, bowling_team)]["figures"][(match_id, innings_number)] = figures
                match_bowling_rows.append({
                    "match_id": match_id, "date": date, "innings": innings_number,
                    "team": bowling_team, "opponent": batting_team, "bowler": bowler,
                    "overs": _overs(figures[2]), "runs_conceded": figures[1],
                    "wickets": figures[0],
                    "economy": round(figures[1] * 6 / figures[2], 2) if figures[2] else 0,
                    "dots": figures[3], "fours_conceded": figures[4], "sixes_conceded": figures[5],
                })
            innings_summaries.append((batting_team, score))

        first_team, first_score = innings_summaries[0]
        second_team, second_score = innings_summaries[1] if len(innings_summaries) > 1 else ("", {"runs": 0, "wickets": 0, "legal_balls": 0, "run_rate": 0})
        winner = info.get("outcome", {}).get("winner", "")
        summaries.append({
            "date": date, "format": "IPL T20", "team": first_team,
            "opponent": second_team, "venue": info.get("venue", ""),
            "runs": first_score["runs"], "wickets": first_score["wickets"],
            "overs": _overs(first_score["legal_balls"]), "run_rate": first_score["run_rate"],
            "result": _result(info), "player_of_match": player_of_match, "match_id": match_id,
            "stage": stage,
        })

        outcome = info.get("outcome", {})
        if is_league_match:
            for team in teams:
                team_stats[team]["matches_played"] += 1
                if winner:
                    if team == winner:
                        team_stats[team]["wins"] += 1
                        team_stats[team]["points"] += 2
                    else:
                        team_stats[team]["losses"] += 1
                elif outcome.get("result", "").casefold() == "tie":
                    team_stats[team]["ties"] += 1
                    team_stats[team]["points"] += 1
                else:
                    team_stats[team]["no_results"] += 1
                    team_stats[team]["points"] += 1
            for team, score in innings_summaries:
                stats = team_stats[team]
                stats["runs_scored"] += score["runs"]
                stats["legal_balls_faced"] += score["legal_balls"]
                stats["nrr_balls_faced"] += nrr_balls_by_team[team]
                other_team = next((candidate for candidate in teams if candidate != team), "")
                team_stats[other_team]["runs_conceded"] += score["runs"]
                team_stats[other_team]["legal_balls_bowled"] += score["legal_balls"]
                team_stats[other_team]["nrr_balls_bowled"] += nrr_balls_by_team[team]

    player_rows = []
    for (player, team), record in sorted(batting.items()):
        innings_count = len(record["innings"])
        dismissals = len(record["outs"])
        scores = list(record["scores"].values())
        player_rows.append({
            "player": player, "team": team, "role": "Batter",
            "matches": len(record["matches"]), "runs": record["runs"],
            "average": round(record["runs"] / dismissals, 2) if dismissals else record["runs"],
            "strike_rate": round(record["runs"] * 100 / record["balls"], 2) if record["balls"] else 0,
            "fifties": sum(50 <= score < 100 for score in scores),
            "hundreds": sum(score >= 100 for score in scores),
            "innings": innings_count, "not_outs": innings_count - dismissals,
            "balls_faced": record["balls"], "fours": record["fours"], "sixes": record["sixes"],
            "highest_score": max(scores, default=0),
        })

    bowler_rows = []
    for (player, team), record in sorted(bowling.items()):
        balls = record["balls"]
        runs = record["runs"]
        wickets = record["wickets"]
        figures = list(record["figures"].values())
        best = max(figures, key=lambda item: (item[0], -item[1]), default=[0, 0])
        bowler_rows.append({
            "bowler": player, "team": team, "matches": len(record["matches"]),
            "innings": len(record["innings"]), "overs": _overs(balls),
            "runs_conceded": runs, "wickets": wickets,
            "economy": round(runs * 6 / balls, 2) if balls else 0,
            "average": round(runs / wickets, 2) if wickets else 0,
            "strike_rate": round(balls / wickets, 2) if wickets else 0,
            "best_figures": f"{best[0]}/{best[1]}",
            "four_wicket_hauls": sum(item[0] == 4 for item in figures),
            "five_wicket_hauls": sum(item[0] >= 5 for item in figures),
            "balls_bowled": balls,
        })

    fielding_rows = [
        {"player": player, "team": team, "matches": len(stats["matches"]),
         "catches": stats["catches"], "stumpings": stats["stumpings"], "run_outs": stats["run_outs"]}
        for (player, team), stats in sorted(fielding.items())
    ]
    team_rows = []
    for team, stats in sorted(team_stats.items()):
        scoring_rate = stats["runs_scored"] * 6 / stats["nrr_balls_faced"] if stats["nrr_balls_faced"] else 0
        conceded_rate = stats["runs_conceded"] * 6 / stats["nrr_balls_bowled"] if stats["nrr_balls_bowled"] else 0
        team_rows.append({**{"team": team}, **stats, "net_run_rate": round(scoring_rate - conceded_rate, 3)})

    return {
        "matches.csv": summaries,
        "players.csv": player_rows,
        "bowlers.csv": bowler_rows,
        "innings.csv": innings_rows,
        "deliveries.csv": delivery_rows,
        "fielding_stats.csv": fielding_rows,
        "team_stats.csv": team_rows,
        "match_batting.csv": match_batting_rows,
        "match_bowling.csv": match_bowling_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import real 2026 IPL data from Cricsheet into CSV files.")
    parser.add_argument("--archive", type=Path, help="Use an existing Cricsheet IPL JSON zip instead of downloading it.")
    args = parser.parse_args()

    with _read_archive(args.archive) as archive:
        matches = _parse_matches(archive)
    if not matches:
        raise RuntimeError("The Cricsheet IPL archive contained no 2026 matches.")
    tables = build_csvs(matches)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    contracts = {
        "matches.csv": MATCH_FIELDS, "players.csv": PLAYER_FIELDS, "bowlers.csv": BOWLER_FIELDS,
        "innings.csv": INNINGS_FIELDS, "deliveries.csv": DELIVERY_FIELDS,
        "fielding_stats.csv": FIELDING_FIELDS, "team_stats.csv": TEAM_FIELDS,
        "match_batting.csv": MATCH_BATTING_FIELDS, "match_bowling.csv": MATCH_BOWLING_FIELDS,
    }
    for filename, fields in contracts.items():
        _write_csv(filename, fields, tables[filename])
    dates = [str(match[1]["info"]["dates"][0]) for match in matches]
    _write_csv("dataset_metadata.csv", METADATA_FIELDS, [{
        "season": SEASON, "source": SOURCE_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "matches": len(matches), "first_match": min(dates), "last_match": max(dates),
    }])
    print(f"Imported {len(matches)} IPL {SEASON} matches and {len(tables['deliveries.csv'])} ball-by-ball records from Cricsheet.")


if __name__ == "__main__":
    main()