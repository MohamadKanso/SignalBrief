from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from signalbrief import run_briefing  # noqa: E402

st.set_page_config(
    page_title="SignalBrief",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink: #111827;
          --muted: #667085;
          --line: #d8e1ee;
          --panel: rgba(255,255,255,.86);
          --blue: #1266f1;
          --teal: #02a79d;
          --amber: #d97706;
          --red: #dc2626;
        }
        .stApp {
          background:
            linear-gradient(90deg, rgba(18,102,241,.08) 1px, transparent 1px),
            linear-gradient(180deg, rgba(2,167,157,.06) 1px, transparent 1px),
            #f7f9fc;
          background-size: 44px 44px;
        }
        .block-container { padding-top: 1.25rem; max-width: 1320px; }
        header[data-testid="stHeader"] { background: transparent; }
        .topbar {
          display:flex; align-items:center; justify-content:space-between;
          padding: 14px 0 18px; border-bottom: 1px solid rgba(17,24,39,.08);
        }
        .brand { display:flex; align-items:center; gap:12px; font-weight:800; color:var(--ink); }
        .mark {
          width:34px; height:34px; border-radius:8px;
          background: linear-gradient(135deg, var(--blue), var(--teal));
          box-shadow: 0 12px 30px rgba(18,102,241,.24);
          position:relative;
        }
        .mark:after {
          content:""; position:absolute; inset:8px; border:2px solid white; border-left:0; border-bottom:0;
          transform: rotate(45deg);
        }
        .nav a {
          color: var(--ink); text-decoration:none; font-size:14px; margin-left:18px; font-weight:700;
        }
        .hero {
          margin: 22px 0 18px;
          display:grid; grid-template-columns: 1.05fr .95fr; gap:22px; align-items:stretch;
        }
        .hero-copy h1 {
          font-size: clamp(42px, 6vw, 82px); line-height:.92; letter-spacing:0;
          margin: 0 0 18px; color:var(--ink);
        }
        .hero-copy p { color:var(--muted); font-size:18px; line-height:1.6; max-width:760px; }
        .panel {
          background: var(--panel); border:1px solid rgba(17,24,39,.09); border-radius:8px;
          box-shadow: 0 24px 70px rgba(17,24,39,.08); padding:20px;
        }
        .agent-rail { display:grid; gap:10px; }
        .agent-step {
          display:grid; grid-template-columns: 34px 1fr auto; align-items:center; gap:12px;
          padding:12px; border:1px solid rgba(17,24,39,.08); border-radius:8px; background:white;
        }
        .dot {
          width:28px; height:28px; border-radius:8px; background:#e8f1ff; position:relative;
        }
        .dot:after {
          content:""; position:absolute; inset:8px; border-radius:50%; background:var(--blue);
          animation:pulse 1.8s infinite ease-in-out;
        }
        @keyframes pulse { 0%,100% { transform:scale(.72); opacity:.55; } 50% { transform:scale(1.18); opacity:1; } }
        .small { color:var(--muted); font-size:13px; }
        .metric-grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; }
        .metric-card {
          background:white; border:1px solid rgba(17,24,39,.08); border-radius:8px; padding:16px;
        }
        .metric-value { font-size:28px; line-height:1; font-weight:850; color:var(--ink); }
        .metric-label { font-size:12px; text-transform:uppercase; color:var(--muted); font-weight:800; margin-top:9px; }
        .source-card {
          padding:13px 14px; border:1px solid rgba(17,24,39,.08); border-radius:8px;
          margin-bottom:10px; background:white;
        }
        .source-card b { color: var(--ink); }
        .evidence {
          border-left:3px solid var(--blue); padding:10px 12px; background:#f8fbff; border-radius:0 8px 8px 0;
          color:#243041; font-size:14px; margin:8px 0;
        }
        .stButton > button {
          border-radius:8px; background:var(--ink); color:white; border:0; font-weight:800;
          min-height:46px; box-shadow:0 16px 40px rgba(17,24,39,.18);
        }
        .stTextInput input {
          border-radius:8px; border:1px solid rgba(17,24,39,.16); min-height:46px; font-weight:650;
        }
        @media (max-width: 900px) {
          .hero { grid-template-columns: 1fr; }
          .metric-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar() -> None:
    st.markdown(
        """
        <div class="topbar">
          <div class="brand"><div class="mark"></div><div>SignalBrief</div></div>
          <div class="nav">
            <a href="https://mohamadkanso.github.io/SignalBrief/process.html" target="_blank">Process</a>
            <a href="https://mohamadkanso.github.io/SignalBrief/why.html" target="_blank">Why</a>
            <a href="https://github.com/MohamadKanso/SignalBrief" target="_blank">GitHub</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def default_briefing():
    if "briefing" not in st.session_state:
        st.session_state.briefing = run_briefing("NVIDIA AI infrastructure")
    return st.session_state.briefing


def run(topic: str):
    with st.spinner("Agent chain researching, reading, retrieving, and synthesising..."):
        st.session_state.briefing = run_briefing(topic)


def sentiment_chart(score: float):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 34}, "valueformat": ".2f"},
            gauge={
                "axis": {"range": [-1, 1], "tickwidth": 0},
                "bar": {"color": "#1266f1"},
                "bgcolor": "white",
                "borderwidth": 0,
                "steps": [
                    {"range": [-1, -0.25], "color": "#fee2e2"},
                    {"range": [-0.25, 0.1], "color": "#fef3c7"},
                    {"range": [0.1, 0.45], "color": "#dbeafe"},
                    {"range": [0.45, 1], "color": "#ccfbf1"},
                ],
            },
        )
    )
    fig.update_layout(height=245, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def render_agent_panel(briefing) -> None:
    rows = []
    for event in briefing.agent_events:
        rows.append(
            "<div class='agent-step'>"
            "<div class='dot'></div>"
            f"<div><b>{event.agent}</b><div class='small'>{event.detail}</div></div>"
            f"<div class='small'>{event.latency_ms}ms</div>"
            "</div>"
        )
    st.markdown(f"<div class='panel'><div class='agent-rail'>{''.join(rows)}</div></div>", unsafe_allow_html=True)


def render_metrics(briefing) -> None:
    cards = []
    for metric in briefing.metrics[:4]:
        cards.append(
            "<div class='metric-card'>"
            f"<div class='metric-value'>{metric.value}</div>"
            f"<div class='metric-label'>{metric.label}</div>"
            f"<div class='small'>{metric.source_title}</div>"
            "</div>"
        )
    st.markdown(f"<div class='metric-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def render_sources(briefing) -> None:
    for source in briefing.sources[:6]:
        st.markdown(
            "<div class='source-card'>"
            f"<b>{source.title}</b><br>"
            f"<span class='small'>{source.domain} · credibility {source.credibility:.0%}</span>"
            "</div>",
            unsafe_allow_html=True,
        )


def render_briefing(briefing) -> None:
    st.markdown("### Executive briefing")
    st.write(briefing.executive_summary)
    render_metrics(briefing)

    left, mid, right = st.columns([1.05, 1, 1])
    with left:
        st.markdown("#### Key facts")
        for fact in briefing.key_facts[:4]:
            st.markdown(f"**{fact.fact}**")
            st.markdown(f"<div class='evidence'>{fact.evidence.quote}</div>", unsafe_allow_html=True)
    with mid:
        st.markdown("#### Risks")
        for risk in briefing.risks:
            st.markdown(f"**{risk.severity}: {risk.title}**")
            st.caption(risk.rationale)
        st.markdown("#### Opportunities")
        for opportunity in briefing.opportunities:
            st.markdown(f"**{opportunity.upside}: {opportunity.title}**")
            st.caption(opportunity.rationale)
    with right:
        st.markdown("#### Sentiment")
        st.plotly_chart(sentiment_chart(briefing.sentiment.score), width="stretch")
        st.markdown(f"**{briefing.sentiment.label}**")
        for driver in briefing.sentiment.drivers:
            st.caption(driver)


def main() -> None:
    inject_css()
    topbar()
    briefing = default_briefing()

    hero_left, hero_right = st.columns([0.95, 1.05], gap="large")
    with hero_left:
        st.markdown(
            """
            <div class="hero-copy">
              <h1>AI analyst briefings in seconds.</h1>
              <p>Give SignalBrief a company, sector, or topic. A LangGraph agent chain plans the research,
              collects sources, builds a retrieval index, extracts evidence, and returns the kind of structured
              risk/opportunity briefing a junior analyst would normally spend hours producing.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_right:
        render_agent_panel(briefing)

    controls = st.columns([4, 1])
    with controls[0]:
        topic = st.text_input("Company or topic", value=briefing.topic, label_visibility="collapsed")
    with controls[1]:
        if st.button("Run Briefing", width="stretch"):
            run(topic)
            st.rerun()

    briefing = st.session_state.briefing
    render_briefing(briefing)

    st.markdown("### Source map")
    source_col, export_col = st.columns([1.2, 1])
    with source_col:
        render_sources(briefing)
    with export_col:
        payload = json.dumps(briefing.model_dump(mode="json"), indent=2)
        st.download_button(
            "Export structured JSON",
            data=payload,
            file_name=f"signalbrief-{briefing.topic.lower().replace(' ', '-')}.json",
            mime="application/json",
            width="stretch",
        )
        df = pd.DataFrame([m.model_dump() for m in briefing.metrics])
        st.dataframe(df, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
