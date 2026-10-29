# Boundary: IPL 2026 Cricket Intelligence

## Overview

Boundary is a Python and Streamlit analyst for the completed 2026 Indian Premier League season. Match, innings, delivery, player, bowling, fielding, and team data are stored in CSV files under `data/`. Gemini generates every analyst response using selected CSV records as context. There is no SQL database and no local answer fallback.

The model is not fine-tuned on cricket data. The application grounds its responses with prompt context assembled from the season CSVs. Exact statistics should be read from those structured records; strategic suggestions are conditional analysis, not guarantees.

## Data source and refresh

Season records are imported from Cricsheet's IPL JSON archive:

- Download page: <https://cricsheet.org/downloads/>
- Archive: <https://cricsheet.org/downloads/ipl_json.zip>
- Official IPL season statistics for cross-checking: <https://www.iplt20.com/stats/2026>

Cricsheet's archive contained 74 IPL 2026 matches, dated March 28 through May 31, 2026: 70 league matches and four playoff matches. The import script records source URL, retrieval timestamp, match count, and date span in `data/dataset_metadata.csv`.

Refresh the files from the source:

```powershell
python scripts/import_ipl_2026.py
```

To use an already-downloaded archive:

```powershell
python scripts/import_ipl_2026.py --archive path\to\ipl_json.zip
```

The importer uses Python's standard library and writes generated tables under `data/`. Running it replaces the season CSVs. Keep `GEMINI_API_KEY` in `.env` or Streamlit secrets; do not put API keys in source files.

## CSV data model

The existing match, player, and bowler column contracts remain as their original leading columns; additive fields support match joins and IPL-specific analysis.

| File | Contents |
| --- | --- |
| `matches.csv` | One record per match: date, teams, venue, first-innings summary, result, player of the match, match ID, and league/playoff stage. |
| `innings.csv` | One record per innings: score, wickets, legal balls, run rate, fours, sixes, extras, and dot balls. |
| `deliveries.csv` | One record per delivery: teams, over/ball, batter, bowler, runs, extras, boundaries, dismissal, player out, and fielders. |
| `players.csv` | Season batting totals: matches, innings, runs, average, strike rate, fifties, hundreds, balls, fours, sixes, and highest score. |
| `match_batting.csv` | Batter figures by match and innings, including runs, balls, boundaries, strike rate, and dismissal. |
| `bowlers.csv` | Season bowling totals: innings, overs, runs conceded, wickets, economy, average, strike rate, best figures, and haul counts. |
| `match_bowling.csv` | Bowler figures by match and innings, including overs, runs, wickets, dots, and boundaries conceded. |
| `fielding_stats.csv` | Player catches, stumpings, and run-outs. |
| `team_stats.csv` | League-stage standings, points, runs, legal balls, NRR-denominator balls, and net run rate. Playoffs are excluded from standings. |
| `dataset_metadata.csv` | Season, source, import time, count, and date coverage. |
| `chat_history.csv` | Saved user questions and successful Gemini answers. Legacy entries without the IPL 2026 mode marker remain in the file but are hidden from the UI and prompt context. |

Metric notes:

- Batter balls faced exclude wides and include no-balls; team legal balls exclude wides and no-balls.
- Player spellings follow Cricsheet's scorecard names, which may be abbreviated.
- Bowler wickets exclude run-outs and other dismissals not credited to the bowler.
- League standings use 70 regular-season games. A team bowled out early is charged the innings' allocated overs for NRR, while the CSV separately records actual legal balls.
- Cricsheet-derived counts can differ slightly from the official IPL website after score corrections. During this import, total sixes matched the official season display (1,426); the source-derived four count was 2,334 versus 2,332 displayed by IPL. The importer preserves source records instead of applying an unexplained adjustment.

## Application structure

- `app.py`: Streamlit navigation, match centre, player/bowling indexes, team table, fielding index, and chat UI.
- `cricket_assistant/data_store.py`: CSV contracts, loading, numeric coercion, and chat-history persistence.
- `cricket_assistant/ai_engine.py`: Gemini client call and question-relevant CSV context selection.
- `scripts/import_ipl_2026.py`: Cricsheet archive parser and CSV generator.
- `data/`: imported IPL 2026 CSVs and chat history.

## Gemini analyst

Configure `GEMINI_API_KEY` in `.env` or Streamlit secrets. `GEMINI_MODEL` may select a model enabled for the key; the default is `gemini-3.5-flash-lite`. Requests time out after 15 seconds per attempt by default and retry once for transient errors; `GEMINI_TIMEOUT_MS` can change the per-attempt timeout from 1,000 to 120,000 milliseconds.

For each submitted question, the application selects relevant match summaries, innings, match-level player figures, season batting/bowling rows, team standings, fielding data, and recent conversation. For a match-specific question, `match_id` joins the match, innings, batting, bowling, and delivery records. Gemini receives instructions to use the supplied facts, distinguish measured values from tactical judgment, ask for clarification when a fixture is ambiguous, and avoid promising a future result.

The season-champion question uses a smaller context containing only the final match and its innings, avoiding unrelated player and delivery tables.

If no key is configured, the model returns an empty response, or the API/network call fails, the app shows an error. Failed requests are not stored as analyst answers, and no local engine substitutes for Gemini.

Gemini can still make reasoning mistakes. The application sends structured records to improve grounding, but model-generated natural language is not a substitute for checking important decisions against the CSV source data. The season files are not a live feed and contain no injury, pitch, or current-availability information.

## Run the app

Requirements: Python 3.10 or newer.

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit prints the local URL, usually `http://localhost:8501`.
