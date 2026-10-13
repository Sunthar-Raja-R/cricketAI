# Boundary: Cricket Intelligence

A local-first cricket dashboard built with Streamlit, Python, CSV files, and optional Gemini-powered Q&A. It includes a match centre, player index, and a cricket analyst that uses the local scorebook as context. No SQL database is used.

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

The analyst works in local CSV mode without a key. To enable Gemini:

1. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey). The Gemini Developer API offers a free tier for selected models, subject to availability and quotas. Review the [current pricing and terms](https://ai.google.dev/gemini-api/docs/pricing); Google may use free-tier inputs and outputs to improve its products, so do not send private data.
2. Copy `.env.example` to `.env` and add the key to `GEMINI_API_KEY`.
3. The default model is `gemini-3.8-flash`. Set `GEMINI_MODEL` to another model enabled for your API key if needed.
4. Restart Streamlit.

The key stays in `.env`, which is excluded from Git. Free-tier quotas, available models, and terms can change; a key does not guarantee unlimited or permanently free usage. If a Gemini request fails, the app returns a local CSV-based answer instead.

## CSV storage

- `data/matches.csv` stores match score summaries.
- `data/players.csv` stores the player index.
- `data/bowlers.csv` stores bowling figures: overs, runs conceded, wickets, economy, average, strike rate, and best figures.
- `data/chat_history.csv` stores conversation history with a header row; the app repairs older headerless chat logs when loading them.
- `data/demo_matches.csv`, `data/demo_players.csv`, and `data/demo_bowlers.csv` each contain 150 generated illustrative rows. Match venues use real stadium names associated with one of the competing teams. The rows use contemporary player names assigned to real national teams, but all generated statistics are synthetic, not verified records. The roster lists are static and are not a live feed; refresh them against current squad announcements when needed.

Edit the base match, player, and bowling CSV files directly to add or change records. Keep the column names and value types documented in `cricket_assistant/data_store.py`. Regenerate the illustrative rows with `python scripts/generate_demo_data.py`. The analyst uses relevant records from all three data categories and recent chat turns as context; its local fallback can answer basic leader, lookup, team, format, and bowling questions without an API key. The app does not use SQL or a hosted database.

## Project map

- `app.py`: Streamlit screens and controls.
- `cricket_assistant/data_store.py`: CSV loading and append-only chat storage.
- `cricket_assistant/ai_engine.py`: Gemini integration and local answer fallback.
- `scripts/generate_demo_data.py`: reproducible generator for the three illustrative datasets.
- `data/`: starter CSV datasets.
