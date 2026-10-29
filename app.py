from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from cricket_assistant.ai_engine import answer_question
from cricket_assistant.data_store import (
    DATA_DIR,
    append_chat,
    clear_chat_history,
    load_bowlers,
    load_chat_history,
    load_dataset_metadata,
    load_deliveries,
    load_fielding_stats,
    load_innings,
    load_match_batting,
    load_match_bowling,
    load_matches,
    load_players,
    summarize_overs,
    load_team_stats,
)


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="Boundary | Cricket intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="auto",
)

try:
    if st.secrets.get("GEMINI_API_KEY"):
        os.environ.setdefault("GEMINI_API_KEY", st.secrets["GEMINI_API_KEY"])
except Exception:
    pass

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#15263b; --muted:#63748a; --paper:#f3f7fb; --line:#dce6f0; --blue:#1769aa; --yellow:#f2c94c; --yellow-soft:#fff8df; --surface:#ffffff; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
    .stApp { background:linear-gradient(180deg,#ffffff 0%,var(--paper) 100%); }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { background:#122a45; border-right:1px solid #294968; }
    [data-testid="stSidebar"] * { color:#f4f8fc; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#c6d8e8; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:9px 11px; border-radius:8px; transition:background .15s ease; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:#1d3d5d; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:#24517b; }
    .brand { font:700 27px 'Space Grotesk',sans-serif; color:#fff; margin:8px 0 2px; }
    .brand span { color:var(--yellow); }
    .side-note { color:#b6cbe0; font-size:11px; margin-bottom:22px; }
    .eyebrow { color:var(--blue); text-transform:uppercase; font-size:11px; font-weight:700; letter-spacing:1px; }
    .page-title { font:600 39px 'Space Grotesk',sans-serif; line-height:1.12; margin:5px 0 7px; color:var(--ink); }
    .subhead { color:var(--muted); margin:0 0 22px; font-size:14px; }
    .hero { background:linear-gradient(115deg,#123a60 0%,#175b8a 72%,#244d70 100%); color:#f7fbff; padding:27px 30px; border-radius:10px; position:relative; overflow:hidden; margin:4px 0 22px; }
    .hero:after { content:'BOUNDARY'; position:absolute; right:20px; bottom:-24px; color:rgba(255,255,255,.07); font:700 82px 'Space Grotesk',sans-serif; }
    .hero .eyebrow { color:var(--yellow); }
    .hero h2 { color:#fff; font:600 29px 'Space Grotesk',sans-serif; margin:5px 0 7px; }
    .hero p { color:#e0edf8; margin:0; max-width:620px; font-size:14px; }
    .metric { background:var(--surface); border:1px solid var(--line); border-radius:9px; padding:15px 17px; min-height:94px; box-shadow:0 3px 12px rgba(21,49,78,.045); }
    .metric-label { color:var(--muted); text-transform:uppercase; font-size:10px; font-weight:700; letter-spacing:.7px; }
    .metric-value { color:var(--ink); font:600 27px 'Space Grotesk',sans-serif; margin-top:5px; overflow-wrap:anywhere; }
    .metric-detail { color:var(--muted); font-size:11px; margin-top:1px; }
    .section-title { font:600 20px 'Space Grotesk',sans-serif; margin:20px 0 9px; }
    .panel { background:var(--surface); border:1px solid var(--line); border-radius:9px; padding:16px 18px; }
    .callout { border-left:3px solid var(--yellow); background:var(--yellow-soft); padding:12px 14px; color:#594a20; border-radius:0 7px 7px 0; font-size:13px; }
    .st-key-player_face_gallery [data-testid="stImage"] { display:flex; justify-content:center; }
    .st-key-player_face_gallery [data-testid="stImage"] img { width:96px; max-width:100%; aspect-ratio:4/5; object-fit:cover; border-radius:8px; background:#fff; margin:0 auto; }
    .st-key-player_face_gallery [data-testid="stCaptionContainer"] { min-height:2.4rem; }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    .stButton button[kind="primary"] { background:var(--blue); border:0; }
    .stButton button { border-radius:7px; }
    .stChatMessage { background:var(--surface); border:1px solid var(--line); border-radius:9px; }
    .stCaption { color:var(--muted); }
    .block-container { padding-top:1.75rem; padding-bottom:2.5rem; }
    [data-testid="stTextInput"] input, [data-testid="stChatInput"] textarea { color:var(--ink); }
    [data-testid="stTextInput"] input::placeholder, [data-testid="stChatInput"] textarea::placeholder { color:#75817b; opacity:1; }
    @media (max-width:700px) { .block-container {padding-left:1rem; padding-right:1rem;} .page-title {font-size:32px;} .hero {padding:22px 20px;} .hero:after {font-size:48px; right:6px;} }
    </style>
    """,
    unsafe_allow_html=True,
)


def metric(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f'<div class="metric"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def heading(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="eyebrow">{kicker}</div><div class="page-title">{title}</div>'
        f'<p class="subhead">{subtitle}</p>',
        unsafe_allow_html=True,
    )


matches = load_matches()
team_options = ["All teams", *sorted(set(matches["team"].dropna()) | set(matches["opponent"].dropna()))]
players = load_players()
bowlers = load_bowlers()
innings = load_innings()
deliveries = load_deliveries()
fielding = load_fielding_stats()
team_stats = load_team_stats()
match_batting = load_match_batting()
match_bowling = load_match_bowling()
dataset_metadata = load_dataset_metadata()
chat_history = load_chat_history()

scorecards: dict[str, str] = {}
for match_id, match_innings in innings.groupby("match_id", sort=False):
    scorecards[str(match_id)] = " · ".join(
        f"{row.batting_team} {int(row.runs)}/{int(row.wickets)} ({row.overs:g} ov)"
        for row in match_innings.sort_values("innings").itertuples(index=False)
    )
match_index = matches.copy()
match_index["scorecard"] = match_index["match_id"].astype(str).map(scorecards).fillna("")

with st.sidebar:
    st.markdown('<div class="brand">BOUNDARY<span>.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-note">IPL 2026 · CRICKET INTELLIGENCE</div>', unsafe_allow_html=True)
    workspace = st.radio("Workspace", ["General", "Ask analyst"], label_visibility="collapsed", key="workspace")
    if workspace == "General":
        st.markdown("**GENERAL**")
        section = st.radio(
            "General pages",
            ["Match centre", "Match index", "Batting index", "Bowling index", "Team table", "Fielding index"],
            label_visibility="collapsed",
            key="general_page",
        )
    else:
        section = "Ask the analyst"
    st.markdown("---")
    st.markdown("**DATA STATUS**")
    season = dataset_metadata.iloc[0]["season"] if not dataset_metadata.empty else "unavailable"
    st.caption(f"IPL {season} · {len(matches)} matches · {len(players)} batters · {len(bowlers)} bowlers")
    st.caption(f"{len(deliveries):,} ball-by-ball records · CSV storage")
    st.markdown("---")
    if os.getenv("GEMINI_API_KEY"):
        st.success("Gemini connected", icon="✨")
    else:
        st.warning("Gemini key required", icon="🔑")
    st.caption("Analyst responses are Gemini-generated; there is no local answer fallback.")

if section == "Match centre":
    heading("SEASON OVERVIEW", "IPL 2026", "The season at a glance: league phase, playoffs, scoring, and recent results.")
    st.markdown(
        '<div class="hero"><div class="eyebrow">TATA INDIAN PREMIER LEAGUE</div>'
        '<h2>A season decided at the margins.</h2>'
        '<p>Review the season totals, compare innings output, and keep the latest results in view.</p></div>',
        unsafe_allow_html=True,
    )
    featured_players = [
        ("Virat Kohli", "V Kohli", "virat-kohli.jpg"),
        ("Shubman Gill", "Shubman Gill", "shubman-gill.jpg"),
        ("MS Dhoni", "MS Dhoni", "ms-dhoni.jpg"),
        ("Rohit Sharma", "RG Sharma", "rohit-sharma.jpg"),
        ("Shreyas Iyer", "SS Iyer", "shreyas-iyer.jpg"),
    ]
    st.markdown('<div class="section-title">Player spotlights</div>', unsafe_allow_html=True)
    with st.container(key="player_face_gallery"):
        portrait_columns = st.columns(len(featured_players), gap="small")
        for column, (display_name, record_name, image_name) in zip(portrait_columns, featured_players):
            with column:
                st.image(ROOT / "assets" / "player_portraits" / image_name, width=96)
                st.markdown(f"**{display_name}**")
                player_record = players[players["player"].eq(record_name)]
                if player_record.empty:
                    st.caption("No 2026 match record")
                else:
                    record = player_record.iloc[0]
                    st.caption(f"{record['team']} · {int(record['runs']):,} runs")
    with st.expander("Photo credits"):
        st.markdown(
            "- Virat Kohli, photographed July 2024 by the Prime Minister's Office, Government of India, [GODL-India](https://data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf) ([source](https://commons.wikimedia.org/wiki/File:Virat_Kohli_in_PMO_New_Delhi.jpg))\n"
            "- Shubman Gill 2023 (cropped) by Bollywood Hungama, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) ([source](https://commons.wikimedia.org/wiki/File:Shubman_Gill_2023_(cropped).jpg))\n"
            "- MS Dhoni, photographed October 2023 by RIGI, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) ([source](https://commons.wikimedia.org/wiki/File:MS_Dhoni_(Prabhav_%2723_-_RiGI_2023).jpg))\n"
            "- Rohit Sharma, photographed June 2026 by the President's Secretariat, Government of India, [GODL-India](https://data.gov.in/sites/default/files/Gazette_Notification_OGDL.pdf) ([source](https://commons.wikimedia.org/wiki/File:The_President_of_Bharat,_Smt._Droupadi_Murmu_presenting_the_Padma_Shri_Award_to_Shri_Rohit_Gurunath_Sharma_at_the_Civil_Investiture_Ceremony-II_at_Rashtrapati_Bhavan.jpg))\n"
            "- Shreyas Iyer, photographed April 2025 by Bollywood Hungama, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) ([source](https://commons.wikimedia.org/wiki/File:Shreyas_Iyer_snapped_at_the_airport.jpg))"
        )
    controls = st.columns([1, 1])
    selected_team = controls[0].selectbox("Team", team_options)
    selected_stage = controls[1].selectbox("Stage", ["All stages", "League", "Playoffs"])

    filtered = match_index.copy()
    if selected_team != "All teams":
        filtered = filtered[(filtered["team"] == selected_team) | (filtered["opponent"] == selected_team)]
    if selected_stage != "All stages":
        filtered = filtered[filtered["stage"] == selected_stage]

    selected_match_ids = set(filtered["match_id"].astype(str)) if "match_id" in filtered else set()
    filtered_innings = innings[innings["match_id"].astype(str).isin(selected_match_ids)]
    total_runs = int(filtered_innings["runs"].sum()) if not filtered_innings.empty else 0
    avg_rr = float(filtered_innings["run_rate"].mean()) if not filtered_innings.empty else 0.0
    sixes = int(filtered_innings["sixes"].sum()) if not filtered_innings.empty else 0
    league_count = int(matches["stage"].eq("League").sum())
    playoff_count = int(matches["stage"].eq("Playoffs").sum())
    cards = st.columns(4)
    cards[0].markdown(f'<div class="metric"><div class="metric-label">FIXTURES</div><div class="metric-value">{len(filtered)}</div><div class="metric-detail">in this view</div></div>', unsafe_allow_html=True)
    cards[1].markdown(f'<div class="metric"><div class="metric-label">RUNS SCORED</div><div class="metric-value">{total_runs:,}</div><div class="metric-detail">both innings</div></div>', unsafe_allow_html=True)
    cards[2].markdown(f'<div class="metric"><div class="metric-label">LEAGUE / PLAYOFFS</div><div class="metric-value">{league_count} / {playoff_count}</div><div class="metric-detail">season fixtures</div></div>', unsafe_allow_html=True)
    cards[3].markdown(f'<div class="metric"><div class="metric-label">SIXES</div><div class="metric-value">{sixes:,}</div><div class="metric-detail">in this view</div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown('<div class="section-title">Runs by match</div>', unsafe_allow_html=True)
        if filtered_innings.empty:
            st.info("No matches match those filters.")
        else:
            chart_data = filtered_innings.sort_values(["date", "innings"]).assign(
                innings_label=lambda frame: frame["date"] + " · " + frame["batting_team"]
            ).set_index("innings_label")["runs"]
            st.bar_chart(chart_data, color="#1769aa", height=270)
    with right:
        st.markdown('<div class="section-title">Recent results</div>', unsafe_allow_html=True)
        if filtered.empty:
            st.markdown('<div class="panel">Try widening the filters to see results.</div>', unsafe_allow_html=True)
        else:
            recent = filtered.sort_values("date", ascending=False).head(5)
            for row in recent.itertuples(index=False):
                st.markdown(
                    f'<div class="panel" style="padding:12px 14px;margin-bottom:8px">'
                    f'<small style="color:#718078">{row.date} · {row.stage} · {row.venue}</small><br>'
                    f'<b>{row.team}</b> <span style="color:#718078">v</span> <b>{row.opponent}</b><br>'
                    f'<small style="color:#526157">{row.scorecard}</small><br>'
                    f'<small style="color:#1769aa">{row.result}</small></div>',
                    unsafe_allow_html=True,
                )
    if not filtered_innings.empty:
        st.caption(f"Average innings run rate in this view: {avg_rr:.2f}")

elif section == "Match index":
    heading("FIXTURES · SCORECARDS · BALL BY BALL", "Match index", "Browse every fixture, then open its innings, batting, bowling, over, and delivery details.")
    filters = st.columns([1, 1, 2])
    stage_filter = filters[0].selectbox("Stage", ["All stages", "League", "Playoffs"])
    team_filter = filters[1].selectbox("Team", team_options)
    fixture_search = filters[2].text_input("Search fixtures", placeholder="Opponent, venue, player, or date")
    fixture_view = match_index.copy()
    if stage_filter != "All stages":
        fixture_view = fixture_view[fixture_view["stage"] == stage_filter]
    if team_filter != "All teams":
        fixture_view = fixture_view[(fixture_view["team"] == team_filter) | (fixture_view["opponent"] == team_filter)]
    if fixture_search.strip():
        searchable = fixture_view.astype(str).apply(lambda column: column.str.contains(fixture_search.strip(), case=False, na=False)).any(axis=1)
        fixture_view = fixture_view[searchable]
    st.caption(f"{len(fixture_view)} of {len(match_index)} fixtures")
    st.dataframe(
        fixture_view.sort_values("date", ascending=False)[["date", "stage", "team", "opponent", "scorecard", "result", "player_of_match", "venue"]],
        width="stretch",
        hide_index=True,
    )
    if fixture_view.empty:
        st.info("No fixtures match these filters.")
    else:
        fixture_options = fixture_view.sort_values("date", ascending=False)
        fixture_labels = {
            str(row.match_id): f"{row.date} · {row.team} v {row.opponent} · {row.venue}"
            for row in fixture_options.itertuples(index=False)
        }
        selected_match_id = st.selectbox(
            "Inspect a match",
            options=list(fixture_labels),
            format_func=fixture_labels.get,
            key="match_detail_selector",
        )
        selected_match = fixture_options[fixture_options["match_id"].astype(str).eq(selected_match_id)].iloc[0]
        selected_innings = innings[innings["match_id"].astype(str).eq(selected_match_id)].sort_values("innings")
        selected_batting = match_batting[match_batting["match_id"].astype(str).eq(selected_match_id)].sort_values(["innings", "runs"], ascending=[True, False])
        selected_bowling = match_bowling[match_bowling["match_id"].astype(str).eq(selected_match_id)].sort_values(["innings", "wickets", "economy"], ascending=[True, False, True])
        selected_deliveries = deliveries[deliveries["match_id"].astype(str).eq(selected_match_id)].sort_values(["innings", "over", "ball"])

        st.markdown('<div class="section-title">Match details</div>', unsafe_allow_html=True)
        st.caption(f"{selected_match['date']} · {selected_match['stage']} · {selected_match['venue']} · {selected_match['result']} · Player of the match: {selected_match['player_of_match']}")
        score_columns = st.columns(max(1, len(selected_innings)))
        for index, row in enumerate(selected_innings.itertuples(index=False)):
            with score_columns[index]:
                metric(
                    f"Innings {row.innings} · {row.batting_team}",
                    f"{int(row.runs)}/{int(row.wickets)}",
                    f"{row.overs:g} overs · RR {row.run_rate:.2f} · {int(row.fours)} fours · {int(row.sixes)} sixes",
                )

        detail_tabs = st.tabs(["Innings", "Batting", "Bowling", "Overs", "Ball by ball"])
        with detail_tabs[0]:
            st.dataframe(
                selected_innings[["innings", "batting_team", "bowling_team", "runs", "wickets", "overs", "legal_balls", "run_rate", "fours", "sixes", "extras", "dot_balls"]],
                width="stretch",
                hide_index=True,
            )
        with detail_tabs[1]:
            st.dataframe(selected_batting, width="stretch", hide_index=True)
        with detail_tabs[2]:
            st.dataframe(selected_bowling, width="stretch", hide_index=True)
        with detail_tabs[3]:
            over_summary = summarize_overs(selected_deliveries)
            st.dataframe(over_summary, width="stretch", hide_index=True)
        with detail_tabs[4]:
            delivery_view = selected_deliveries.copy()
            delivery_view["over"] += 1
            delivery_view = delivery_view.rename(columns={
                "innings": "innings", "over": "over_number", "ball": "delivery",
                "batting_team": "batting_team", "bowling_team": "bowling_team",
                "batter": "batter", "bowler": "bowler", "non_striker": "non_striker",
                "batter_runs": "runs_off_bat", "extras": "extras", "total_runs": "total_runs",
                "wides": "wides", "noballs": "no_balls", "byes": "byes",
                "legbyes": "leg_byes", "penalty": "penalty", "is_four": "four",
                "is_six": "six", "wicket_kind": "wicket_kind", "player_out": "player_out",
                "fielders": "fielders",
            })
            delivery_columns = ["innings", "over_number", "delivery", "batting_team", "batter", "bowler", "non_striker", "runs_off_bat", "extras", "total_runs", "wides", "no_balls", "byes", "leg_byes", "penalty", "four", "six", "wicket_kind", "player_out", "fielders"]
            st.caption(f"{len(delivery_view)} deliveries across {len(selected_innings)} innings")
            st.dataframe(delivery_view[delivery_columns], width="stretch", hide_index=True)
            st.download_button(
                "Download this match's ball-by-ball CSV",
                data=selected_deliveries.to_csv(index=False).encode("utf-8"),
                file_name=f"ipl_2026_{selected_match_id}_deliveries.csv",
                mime="text/csv",
                key=f"download_deliveries_{selected_match_id}",
            )

elif section == "Ask the analyst":
    heading("GEMINI · IPL 2026", "The analyst", "Ask about match facts, player performance, team trends, or tactical ways to improve a side's chances.")
    if not os.getenv("GEMINI_API_KEY"):
        st.markdown('<div class="callout">Gemini is not configured. Add <code>GEMINI_API_KEY</code> to <code>.env</code> or Streamlit secrets to enable generated answers.</div>', unsafe_allow_html=True)
    conversation_heading, clear_action = st.columns([3, 1])
    with conversation_heading:
        st.markdown('<div class="section-title">Conversation</div>', unsafe_allow_html=True)
    with clear_action:
        if st.button("Clear history", icon="🗑️", disabled=chat_history.empty, width="stretch"):
            clear_chat_history()
            st.rerun()
    for item in chat_history.tail(12).itertuples(index=False):
        with st.chat_message("user"):
            st.write(item.question)
        with st.chat_message("assistant"):
            st.write(item.answer)
            st.caption(item.mode)

    prompt = st.chat_input("Ask about a player, team, or match trend...")
    if prompt:
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Asking Gemini..."):
                try:
                    response, mode = answer_question(
                        prompt, matches, players, bowlers, chat_history.tail(8),
                        innings=innings, deliveries=deliveries, fielding=fielding,
                        teams=team_stats, match_batting=match_batting,
                        match_bowling=match_bowling, metadata=dataset_metadata,
                    )
                except Exception as error:
                    error_status = str(getattr(error, "status", "")).upper()
                    error_code = getattr(error, "code", None)
                    if error_status == "DEADLINE_EXCEEDED" or error_code == 504 or "timeout" in type(error).__name__.casefold():
                        st.error("Gemini timed out (504). Retry in a moment; the request now uses a faster model and a 15-second per-attempt limit.")
                    elif error_status == "UNAVAILABLE" or error_code in {429, 500, 502, 503}:
                        st.error("Gemini is temporarily unavailable or rate-limited. Wait a moment and try again.")
                    else:
                        st.error(f"Gemini could not answer ({type(error).__name__}). Check the API key, model setting, or connection and try again.")
                else:
                    st.write(response)
                    st.caption(mode)
                    append_chat(prompt, response, mode)
                    st.rerun()

elif section == "Batting index":
    heading("2026 SEASON", "Batting index", "Batting performance across the 2026 IPL season.")
    search_player = st.text_input("Search players", placeholder="Player name or team")
    player_view = players.copy()
    if search_player.strip():
        mask = player_view.astype(str).apply(lambda column: column.str.contains(search_player.strip(), case=False, na=False)).any(axis=1)
        player_view = player_view[mask]
    if not player_view.empty:
        best = player_view.sort_values("runs", ascending=False).iloc[0]
        st.markdown(
            f'<div class="hero"><div class="eyebrow">LEADING RUN-SCORER IN THIS VIEW</div>'
            f'<h2>{best["player"]}</h2><p>{int(best["runs"])} runs across {int(best["matches"])} matches · '
            f'{best["team"]} · strike rate {float(best["strike_rate"]):.1f}</p></div>',
            unsafe_allow_html=True,
        )
    st.dataframe(player_view.sort_values("runs", ascending=False), width="stretch", hide_index=True)
    st.markdown('<div class="section-title">Your local data</div>', unsafe_allow_html=True)
    st.caption(f"Season CSVs: {DATA_DIR / 'players.csv'} · {DATA_DIR / 'match_batting.csv'}")
elif section == "Bowling index":
    heading("2026 SEASON", "Bowling index", "Compare wicket-taking, control, and innings-level bowling figures.")
    search_bowler = st.text_input("Search bowlers", placeholder="Bowler name or team")
    bowler_view = bowlers.copy()
    if search_bowler.strip():
        mask = bowler_view.astype(str).apply(lambda column: column.str.contains(search_bowler.strip(), case=False, na=False)).any(axis=1)
        bowler_view = bowler_view[mask]
    if not bowler_view.empty:
        leader = bowler_view.sort_values(["wickets", "economy"], ascending=[False, True]).iloc[0]
        wickets_col, economy_col, average_col = st.columns(3)
        wickets_col.markdown(f'<div class="metric"><div class="metric-label">WICKET LEADER</div><div class="metric-value">{leader["bowler"]}</div><div class="metric-detail">{int(leader["wickets"])} wickets · {leader["team"]}</div></div>', unsafe_allow_html=True)
        economy_col.markdown(f'<div class="metric"><div class="metric-label">ECONOMY</div><div class="metric-value">{float(leader["economy"]):.2f}</div><div class="metric-detail">leader row economy</div></div>', unsafe_allow_html=True)
        average_col.markdown(f'<div class="metric"><div class="metric-label">BOWLING AVERAGE</div><div class="metric-value">{float(leader["average"]):.2f}</div><div class="metric-detail">runs per wicket</div></div>', unsafe_allow_html=True)
    st.dataframe(bowler_view.sort_values("wickets", ascending=False), width="stretch", hide_index=True)
    st.caption(f"Season CSVs: {DATA_DIR / 'bowlers.csv'} · {DATA_DIR / 'match_bowling.csv'}")
elif section == "Team table":
    heading("2026 SEASON", "Team table", "Season standings and run-rate totals derived from recorded match innings.")
    st.dataframe(team_stats.sort_values(["points", "net_run_rate"], ascending=[False, False]), width="stretch", hide_index=True)
elif section == "Fielding index":
    heading("2026 SEASON", "Fielding index", "Recorded catches, stumpings, and run-outs by player.")
    st.dataframe(fielding.sort_values(["catches", "stumpings", "run_outs"], ascending=False), width="stretch", hide_index=True)
