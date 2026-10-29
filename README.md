# Boundary: Cricket Intelligence

A Streamlit cricket dashboard focused on the completed 2026 Indian Premier League season. It stores Cricsheet-derived match, innings, delivery, batting, bowling, fielding, and team data in CSV files and uses Gemini for every analyst response. No SQL database or local answer fallback is used.

## Run it

1. Install Python 3.10 or newer.
2. From this project folder, create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start the app:

   ```powershell
   streamlit run app.py
   ```

Streamlit prints the local URL, usually `http://localhost:8501`.

## Enable generated answers

The analyst requires Gemini; it does not return locally generated substitute answers when Gemini is unavailable.

1. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey). The Gemini Developer API offers a free tier for selected models, subject to availability and quotas. Review the [current pricing and terms](https://ai.google.dev/gemini-api/docs/pricing); Google may use free-tier inputs and outputs to improve its products, so do not send private data.
2. Add the key to `.env` as `GEMINI_API_KEY=...`, or configure `GEMINI_API_KEY` in Streamlit secrets.
3. The default model is `gemini-3.8-flash`. Set `GEMINI_MODEL` to another model enabled for your API key if needed.
4. Restart Streamlit.

The key stays outside source control. Free-tier quotas, available models, and terms can change. If Gemini is unavailable, the app displays an error and does not save a fabricated answer.
Gemini requests use `gemini-3.5-flash-lite` by default and have a 15-second per-attempt timeout with one retry for transient failures. Set `GEMINI_MODEL` to another enabled model or `GEMINI_TIMEOUT_MS` to adjust the timeout (between 1,000 and 120,000 milliseconds).

## CSV storage

- `data/matches.csv`, `data/innings.csv`, and `data/deliveries.csv` contain the 74 completed 2026 IPL matches, innings totals, and ball-by-ball records.
- `data/players.csv`, `data/bowlers.csv`, `data/match_batting.csv`, and `data/match_bowling.csv` contain season and match-level performance.
- `data/team_stats.csv` contains league-stage standings and net run rate; `data/fielding_stats.csv` contains catches, stumpings, and run-outs.
- `data/dataset_metadata.csv` records the source URL, import timestamp, and date coverage. `data/chat_history.csv` stores Gemini conversations; pre-IPL legacy entries remain archived but are not shown or sent as context.

Refresh the season tables with `python scripts/import_ipl_2026.py`. The importer downloads Cricsheet's IPL JSON archive; use `--archive path\to\ipl_json.zip` to import a local archive. It writes CSVs under `data/` and replaces those generated season tables. Source: [Cricsheet IPL downloads](https://cricsheet.org/downloads/) and [official IPL statistics](https://www.iplt20.com/stats/2026). The dataset is source-derived, not a live feed; derived totals can differ slightly from the official site's display after score corrections. Do not manually edit generated CSVs unless you intend to replace those changes on the next import.

## Project map

- `app.py`: Streamlit screens and controls.
- `cricket_assistant/data_store.py`: CSV loading and append-only chat storage.
- `cricket_assistant/ai_engine.py`: Gemini-only answer generation and relevant CSV context selection.
- `scripts/import_ipl_2026.py`: reproducible Cricsheet-to-CSV importer.
- `data/`: imported 2026 IPL CSV tables and chat history.
