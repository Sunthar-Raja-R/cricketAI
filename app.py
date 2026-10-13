from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from cricket_assistant.ai_engine import answer_question
from cricket_assistant.data_store import DATA_DIR, append_chat, clear_chat_history, load_bowlers, load_chat_history, load_matches, load_players


ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="Boundary | Cricket intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Oswald:wght@500;600;700&display=swap');
      :root { --ink:#17231e; --muted:#718078; --paper:#f3f5f1; --line:#dfe5df; --green:#17684d; --lime:#c5e96b; --orange:#ed8054; --blue:#477bb3; }
      html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
      .stApp { background:var(--paper); }
      [data-testid="stHeader"] { background:transparent; }
      [data-testid="stSidebar"] { background:#172b23; border-right:0; }
      [data-testid="stSidebar"] * { color:#edf4ef; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#aebdb4; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:8px 10px; border-radius:6px; }
      [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:#294338; }
      .brand { font:600 30px 'Oswald', sans-serif; letter-spacing:0; color:white; margin:7px 0 2px; }
      .brand span { color:var(--lime); }
      .side-note { color:#9db0a4; font-size:12px; margin-bottom:25px; }
      .eyebrow { color:var(--green); text-transform:uppercase; font-size:11px; font-weight:700; letter-spacing:1.1px; }
      .page-title { font:600 38px 'Oswald', sans-serif; letter-spacing:0; line-height:1.1; margin:5px 0 7px; color:var(--ink); }
      .subhead { color:var(--muted); margin:0 0 22px; font-size:14px; }
      .hero { background:#183c2e; color:#f5f8f5; padding:25px 28px; border-radius:8px; position:relative; overflow:hidden; margin:4px 0 22px; }
      .hero:after { content:'BOUNDARY'; position:absolute; right:22px; bottom:-27px; color:rgba(255,255,255,.055); font:700 94px 'Oswald',sans-serif; letter-spacing:0; }
      .hero .eyebrow { color:var(--lime); }
      .hero h2 { color:white; font:600 29px 'Oswald',sans-serif; letter-spacing:0; margin:5px 0 7px; }
      .hero p { color:#c7d7ce; margin:0; max-width:600px; font-size:14px; }
      .metric { background:white; border:1px solid var(--line); border-radius:7px; padding:15px 17px; min-height:92px; }
      .metric-label { color:var(--muted); text-transform:uppercase; font-size:10px; font-weight:700; letter-spacing:.8px; }
      .metric-value { color:var(--ink); font:600 29px 'Oswald',sans-serif; letter-spacing:0; margin-top:4px; }
      .metric-detail { color:var(--muted); font-size:11px; margin-top:1px; }
      .section-title { font:600 21px 'Oswald',sans-serif; letter-spacing:0; margin:18px 0 9px; }
      .panel { background:white; border:1px solid var(--line); border-radius:7px; padding:16px 18px; }
      .callout { border-left:3px solid var(--orange); background:#fff7f2; padding:12px 14px; color:#684b3f; border-radius:0 5px 5px 0; font-size:13px; }
      div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:6px; overflow:hidden; }
      .stButton button[kind="primary"] { background:var(--green); border:0; }
      .stButton button { border-radius:5px; }
      .stChatMessage { background:white; border:1px solid var(--line); border-radius:7px; }
      .stCaption { color:var(--muted); }
      @media (max-width:700px) { .page-title {font-size:32px;} .hero:after {font-size:58px; right:8px;} }
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
players = load_players()
bowlers = load_bowlers()
chat_history = load_chat_history()

with st.sidebar:
    st.markdown('<div class="brand">BOUNDARY<span>.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="side-note">CRICKET INTELLIGENCE / 01</div>', unsafe_allow_html=True)
    section = st.radio("Workspace", ["Match centre", "Ask the analyst", "Player index", "Bowling index"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**DATA STATUS**")
    st.caption(f"{len(matches)} matches · {len(players)} batters · {len(bowlers)} bowlers")
    st.caption("Local CSV storage")
    st.markdown("---")
    if os.getenv("GEMINI_API_KEY"):
        st.success("Gemini connected", icon="✨")
    else:
        st.info("Local analyst mode", icon="💬")
    st.caption("Add a Gemini key in `.env` to enable live AI answers.")

if section == "Match centre":
    heading("THE NUMBERS BEHIND THE GAME", "Match centre", "Explore the starter sample scorebook, then replace or expand it with your own CSV records.")
    st.warning("Supplemental match and player rows contain generated statistics and are illustrative, not verified historical records.")
    st.markdown(
        '<div class="hero"><div class="eyebrow">THE CURRENT READ</div>'
        '<h2>Every over has a story.</h2>'
        '<p>Filter the scorebook, spot the form line, and use the analyst when the numbers need a second look.</p></div>',
        unsafe_allow_html=True,
    )
    controls = st.columns([1, 1, 2])
    formats = ["All formats", *sorted(matches["format"].dropna().unique().tolist())]
    teams = ["All teams", *sorted(set(matches["team"].dropna()) | set(matches["opponent"].dropna()))]
    selected_format = controls[0].selectbox("Format", formats)
    selected_team = controls[1].selectbox("Team", teams)
    search = controls[2].text_input("Find a venue or player", placeholder="Try: Lord's, Kohli...")

    filtered = matches.copy()
    if selected_format != "All formats":
        filtered = filtered[filtered["format"] == selected_format]
    if selected_team != "All teams":
        filtered = filtered[(filtered["team"] == selected_team) | (filtered["opponent"] == selected_team)]
    if search.strip():
        mask = filtered.astype(str).apply(lambda column: column.str.contains(search.strip(), case=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    total_runs = int(filtered["runs"].sum()) if not filtered.empty else 0
    avg_rr = float(filtered["run_rate"].mean()) if not filtered.empty else 0.0
    wins = int(filtered["result"].str.startswith("Won", na=False).sum()) if not filtered.empty else 0
    cards = st.columns(4)
    cards[0].markdown(f'<div class="metric"><div class="metric-label">MATCHES</div><div class="metric-value">{len(filtered)}</div><div class="metric-detail">in this view</div></div>', unsafe_allow_html=True)
    cards[1].markdown(f'<div class="metric"><div class="metric-label">RUNS SCORED</div><div class="metric-value">{total_runs:,}</div><div class="metric-detail">combined innings</div></div>', unsafe_allow_html=True)
    cards[2].markdown(f'<div class="metric"><div class="metric-label">AVG RUN RATE</div><div class="metric-value">{avg_rr:.2f}</div><div class="metric-detail">runs per over</div></div>', unsafe_allow_html=True)
    cards[3].markdown(f'<div class="metric"><div class="metric-label">WINS</div><div class="metric-value">{wins}</div><div class="metric-detail">in the selected view</div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown('<div class="section-title">Runs by match</div>', unsafe_allow_html=True)
        if filtered.empty:
            st.info("No matches match those filters.")
        else:
            chart_data = filtered.sort_values("date").set_index("opponent")["runs"]
            st.bar_chart(chart_data, color="#17684d", height=260)
    with right:
        st.markdown('<div class="section-title">Recent results</div>', unsafe_allow_html=True)
        if filtered.empty:
            st.markdown('<div class="panel">Try widening the filters to see results.</div>', unsafe_allow_html=True)
        else:
            recent = filtered.sort_values("date", ascending=False).head(5)
            for row in recent.itertuples(index=False):
                st.markdown(
                    f'<div class="panel" style="padding:11px 14px;margin-bottom:7px;display:flex;justify-content:space-between;gap:12px">'
                    f'<span><b>{row.team}</b> <span style="color:#718078">v {row.opponent}</span><br>'
                    f'<small style="color:#718078">{row.date} · {row.format} · {row.venue}</small></span>'
                    f'<b style="white-space:nowrap">{row.runs}/{row.wickets}</b></div>',
                    unsafe_allow_html=True,
                )
    st.markdown('<div class="section-title">Scorebook</div>', unsafe_allow_html=True)
    st.dataframe(filtered.sort_values("date", ascending=False), width="stretch", hide_index=True)

elif section == "Ask the analyst":
    heading("ASK A BETTER CRICKET QUESTION", "The analyst", "Ask about form, matchups, score trends, or what the scorebook might be missing.")
    if not os.getenv("GEMINI_API_KEY"):
        st.markdown('<div class="callout">You are in local analyst mode. Add a free-tier Gemini API key to <code>.env</code> for generated answers; local answers still use the CSV scorebook.</div>', unsafe_allow_html=True)
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
            with st.spinner("Reading the scorebook..."):
                response, mode = answer_question(prompt, matches, players, bowlers, chat_history.tail(8))
            st.write(response)
            st.caption(mode)
        append_chat(prompt, response, mode)
        st.rerun()

elif section == "Player index":
    heading("PLAYER FORM, WITHOUT THE NOISE", "Player index", "Compare batting output in the sample scorebook. Add rows to the CSV to grow your own dataset.")
    st.warning("Supplemental batting statistics are generated examples assigned to real cricketer names; they are not verified career records.")
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
    st.caption(f"Match records: {DATA_DIR / 'matches.csv'} · Player records: {DATA_DIR / 'players.csv'}")
    st.caption("Edit these CSV files directly; the app reads them again on each interaction.")
else:
    heading("WICKETS, CONTROL, AND BOWLING FORM", "Bowling index", "Explore bowling figures and compare wicket-taking and economy in the local scorebook.")
    st.warning("Supplemental bowling statistics are generated examples assigned to real cricketer names; they are not verified career records.")
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
    st.caption(f"Bowling records: {DATA_DIR / 'bowlers.csv'} · Generated examples: {DATA_DIR / 'demo_bowlers.csv'}")
