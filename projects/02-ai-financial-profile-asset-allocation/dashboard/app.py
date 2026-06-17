"""
app.py — AI-Powered Financial Profile & Asset Allocation Tool
Step-by-step wizard powered by Groq (Llama 3.3).
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from allocation_engine import get_allocation
from fund_recommender import build_fund_recommendations
from risk_profiler import (
    BASE_ALLOCATIONS,
    QUESTIONS,
    compute_risk_score,
    get_risk_label,
    score_to_gauge_color,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Asset Allocator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Animations ── */
@keyframes fadeUp   { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn   { from{opacity:0} to{opacity:1} }
@keyframes barGrow  { from{transform:scaleX(0)} to{transform:scaleX(1)} }
@keyframes gradPulse{
    0%,100%{background-position:0% 50%}
    50%{background-position:100% 50%}
}
@keyframes shimmer  {
    0%  {background-position:-200% center}
    100%{background-position: 200% center}
}
@keyframes scalePop { from{opacity:0;transform:scale(0.9)} to{opacity:1;transform:scale(1)} }

/* ── Landing ── */
.landing-wrap {
    max-width: 760px; margin: 4rem auto 0; text-align: center;
    animation: fadeUp 0.7s ease both;
}
.landing-eyebrow {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #818CF8; margin-bottom: 1.2rem;
}
.landing-title {
    font-size: 3.2rem; font-weight: 800; line-height: 1.1;
    background: linear-gradient(270deg, #818CF8, #C4B5FD, #38BDF8, #818CF8);
    background-size: 300% 300%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradPulse 6s ease infinite;
    margin-bottom: 1.1rem;
}
.landing-sub {
    font-size: 1.1rem; color: #64748B; max-width: 500px;
    margin: 0 auto 2.5rem; line-height: 1.65;
}
.landing-pills {
    display: flex; justify-content: center; flex-wrap: wrap;
    gap: 0.5rem; margin-bottom: 2.5rem;
}
.pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px; padding: 0.3rem 0.85rem;
    font-size: 0.78rem; color: #64748B;
}
.pill i { color: #818CF8; }
.trust-row {
    display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;
    margin-top: 3rem; padding-top: 2rem;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.trust-item { text-align: center; }
.trust-num { font-size: 1.5rem; font-weight: 700; color: #E2E8F0; }
.trust-label { font-size: 0.72rem; color: #475569; margin-top: 0.15rem; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Wizard ── */
.wizard-wrap {
    max-width: 600px; margin: 0 auto;
    animation: fadeUp 0.5s ease both;
}
.progress-row {
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 2.5rem;
}
.prog-dot {
    width: 8px; height: 8px; border-radius: 999px;
    background: rgba(255,255,255,0.1); transition: all 0.3s ease;
}
.prog-dot.done  { background: #818CF8; }
.prog-dot.active{ background: #818CF8; width: 24px; }
.prog-line { flex: 1; height: 1px; background: rgba(255,255,255,0.06); }
.prog-label { font-size: 0.75rem; color: #475569; margin-left: auto; }

.q-icon-wrap {
    width: 3rem; height: 3rem; border-radius: 14px;
    background: rgba(129,140,248,0.1); border: 1px solid rgba(129,140,248,0.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.25rem; color: #818CF8; margin-bottom: 1.5rem;
}
.q-heading {
    font-size: 1.7rem; font-weight: 700; color: #E2E8F0;
    line-height: 1.25; margin-bottom: 0.6rem;
}
.q-hint {
    font-size: 0.85rem; color: #475569; line-height: 1.6;
    margin-bottom: 1.8rem;
}

/* ── Radio option cards ── */
div[data-testid="stRadio"] > div { gap: 0 !important; }

div[data-testid="stRadio"] > div > label {
    display: flex !important;
    align-items: center;
    width: 100%;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 0.9rem 1.1rem !important;
    margin-bottom: 0.5rem !important;
    cursor: pointer;
    transition: all 0.15s ease;
    color: #94A3B8 !important;
    font-size: 0.9rem !important;
}
div[data-testid="stRadio"] > div > label:hover {
    background: rgba(129,140,248,0.07);
    border-color: rgba(129,140,248,0.25);
    color: #E2E8F0 !important;
    transform: translateX(3px);
}
div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: rgba(129,140,248,0.1);
    border-color: #818CF8;
    color: #E2E8F0 !important;
}
/* Hide the default radio circle SVG */
div[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }

/* ── Income step ── */
.income-label {
    font-size: 1.7rem; font-weight: 700; color: #E2E8F0;
    line-height: 1.25; margin-bottom: 0.6rem;
}
.income-hint { font-size: 0.85rem; color: #475569; line-height: 1.6; margin-bottom: 1.8rem; }

/* ── Results ── */
.result-hero {
    text-align: center; padding: 1rem 0 0.5rem;
    animation: fadeUp 0.5s ease both;
}
.result-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #475569; margin-bottom: 0.5rem;
}
.result-profile {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.45rem 1.1rem; border-radius: 999px;
    font-size: 1rem; font-weight: 600;
    margin-bottom: 0.3rem;
    animation: scalePop 0.4s ease both;
}
.result-score { font-size: 0.85rem; color: #475569; margin-bottom: 1.5rem; }

/* Metric cards */
.metric-row {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 0.65rem; margin: 1.2rem 0;
}
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 1rem 0.8rem; text-align: center;
    animation: fadeUp 0.5s ease both;
    transition: transform 0.2s ease;
}
.metric-card:hover { transform: translateY(-3px); }
.mc-icon { font-size: 1.1rem; margin-bottom: 0.35rem; }
.mc-num { font-size: 1.85rem; font-weight: 800; line-height: 1; animation: scalePop 0.5s ease both; }
.mc-label { font-size: 0.68rem; color: #475569; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500; }

/* Bars */
.bar-section { animation: fadeUp 0.6s ease both; }
.bar-row { margin-bottom: 1rem; }
.bar-label-row { display: flex; justify-content: space-between; margin-bottom: 0.3rem; }
.bar-name { font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 0.35rem; }
.bar-pct  { font-size: 0.85rem; font-weight: 700; }
.bar-bg   { background: rgba(255,255,255,0.06); border-radius: 999px; height: 6px; overflow: hidden; }
.bar-fill { height: 6px; border-radius: 999px; transform-origin: left; animation: barGrow 1s cubic-bezier(0.34,1.56,0.64,1) both; }
.bar-reason { margin-top: 0.4rem; font-size: 0.78rem; color: #475569; line-height: 1.55; }

/* Comparison chart label */
.compare-note { font-size: 0.76rem; color: #334155; margin-top: 0.4rem; text-align: center; }

/* SIP card */
.sip-card {
    background: linear-gradient(270deg, rgba(16,185,129,0.08), rgba(56,189,248,0.05), rgba(16,185,129,0.08));
    background-size: 300% 300%;
    animation: shimmer 5s ease infinite, fadeUp 0.5s ease both;
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 14px; padding: 1.2rem 1.4rem;
    display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;
}
.sip-icon { width: 2.8rem; height: 2.8rem; border-radius: 12px;
    background: rgba(16,185,129,0.12); display: flex; align-items: center;
    justify-content: center; font-size: 1.2rem; color: #10B981; flex-shrink:0; }
.sip-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; }
.sip-amount { font-size: 1.6rem; font-weight: 800; color: #10B981; line-height: 1.1; }
.sip-sub { font-size: 0.75rem; color: #334155; margin-top: 0.1rem; }

/* Considerations */
.consid-wrap {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px; overflow: hidden;
}
.consid-item {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.85rem 1.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.83rem; color: #94A3B8; line-height: 1.55;
    transition: background 0.15s;
}
.consid-item:last-child { border-bottom: none; }
.consid-item:hover { background: rgba(255,255,255,0.015); }
.consid-item i { color: #10B981; font-size: 0.9rem; flex-shrink:0; margin-top: 0.15rem; }

/* Fund cards */
.fund-card {
    border: 1px solid rgba(255,255,255,0.06);
    border-left: 3px solid #818CF8;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.1rem; margin-bottom: 0.6rem;
    transition: all 0.15s ease;
}
.fund-card:hover { background: rgba(129,140,248,0.04); border-left-color: #A78BFA; }
.fund-card-title { font-size: 0.9rem; font-weight: 600; color: #E2E8F0; display: flex; align-items: center; gap: 0.5rem; }
.fund-badge {
    display: inline-block; background: rgba(129,140,248,0.1); color: #818CF8;
    font-size: 0.67rem; font-weight: 600; padding: 0.1rem 0.45rem;
    border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em;
}
.fund-rationale { font-size: 0.78rem; color: #475569; margin-top: 0.3rem; line-height: 1.55; }
.fund-pick { display: flex; align-items: center; gap: 0.45rem; padding: 0.28rem 0; font-size: 0.78rem; color: #64748B; }
.fund-rank { background: rgba(16,185,129,0.1); color: #10B981; font-size: 0.67rem; font-weight: 700; padding: 0.08rem 0.38rem; border-radius: 4px; flex-shrink:0; }

/* Next steps */
.next-step-card {
    display: flex; gap: 1rem; padding: 1rem 1.2rem;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px; margin-bottom: 0.6rem;
    transition: background 0.15s ease;
    animation: fadeUp 0.5s ease both;
}
.next-step-card:hover { background: rgba(255,255,255,0.04); }
.ns-num {
    width: 2rem; height: 2rem; border-radius: 50%;
    background: linear-gradient(135deg, #818CF8, #38BDF8);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.78rem; font-weight: 700; color: white; flex-shrink: 0;
}
.ns-title { font-size: 0.88rem; font-weight: 600; color: #E2E8F0; margin-bottom: 0.2rem; }
.ns-body  { font-size: 0.8rem; color: #64748B; line-height: 1.5; }

/* Demo banner */
.demo-banner {
    display: flex; align-items: center; gap: 0.6rem;
    background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.15);
    border-radius: 10px; padding: 0.65rem 1rem;
    font-size: 0.82rem; color: #7DD3FC; margin-bottom: 1rem;
}

/* Disclaimer */
.disclaimer {
    background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px; padding: 0.9rem 1.2rem;
    font-size: 0.74rem; color: #334155; line-height: 1.65; margin-top: 1.5rem;
}
.footer { text-align: center; margin-top: 1rem; font-size: 0.74rem; color: #334155; }
.footer a { color: #818CF8; text-decoration: none; }

/* Sidebar minimal */
[data-testid="stSidebar"] { background: rgba(15,23,42,0.98); }
/* Streamlit padding reset for wizard feel */
.block-container { padding-top: 2rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

ASSET_COLORS = {
    "equity":       "#818CF8",
    "debt":         "#10B981",
    "gold":         "#F59E0B",
    "alternatives": "#38BDF8",
}
ASSET_ICONS = {
    "equity":       "bi-graph-up-arrow",
    "debt":         "bi-shield-check",
    "gold":         "bi-gem",
    "alternatives": "bi-layers",
}
ASSET_GRAD = {
    "equity":       "linear-gradient(90deg,#818CF8,#A78BFA)",
    "debt":         "linear-gradient(90deg,#10B981,#34D399)",
    "gold":         "linear-gradient(90deg,#F59E0B,#FCD34D)",
    "alternatives": "linear-gradient(90deg,#38BDF8,#67E8F9)",
}
RISK_COLORS = {
    "Conservative":          ("#10B981", "rgba(16,185,129,0.1)",  "rgba(16,185,129,0.3)"),
    "Moderate Conservative": ("#F59E0B", "rgba(245,158,11,0.1)",  "rgba(245,158,11,0.3)"),
    "Moderate Aggressive":   ("#F97316", "rgba(249,115,22,0.1)",  "rgba(249,115,22,0.3)"),
    "Aggressive":            ("#EF4444", "rgba(239,68,68,0.1)",   "rgba(239,68,68,0.3)"),
}
TRANSPARENT = "rgba(0,0,0,0)"
CHART_FONT  = "#64748B"
PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color="#E2E8F0", bordercolor="#334155"),
)

# Wizard question definitions (more conversational than QUESTIONS defaults)
WIZARD_STEPS = [
    {
        "key":     "age",
        "icon":    "bi-person",
        "heading": "How old are you?",
        "hint":    "Your age determines how long your money can work for you — the single biggest factor in how much risk you can take.",
        "options": list(QUESTIONS["age"]["options"]),
    },
    {
        "key":     "horizon",
        "icon":    "bi-clock-history",
        "heading": "How long can you stay invested without touching this money?",
        "hint":    "Time is the most powerful compounding tool. A longer horizon means you can absorb short-term volatility for better long-term returns.",
        "options": list(QUESTIONS["horizon"]["options"]),
    },
    {
        "key":     "goal",
        "icon":    "bi-bullseye",
        "heading": "What matters most to you?",
        "hint":    "Your primary goal shapes the entire allocation. Wealth creation needs a fundamentally different strategy than capital preservation.",
        "options": list(QUESTIONS["goal"]["options"]),
    },
    {
        "key":     "reaction",
        "icon":    "bi-graph-down-arrow",
        "heading": "Your portfolio drops 20% overnight. What do you do?",
        "hint":    "Be honest — emotional discipline during downturns matters as much as the strategy itself. Markets recover; panic selling doesn't.",
        "options": list(QUESTIONS["reaction"]["options"]),
    },
    {
        "key":     "debt",
        "icon":    "bi-credit-card-2-back",
        "heading": "Do you have existing debt obligations?",
        "hint":    "High-interest debt reduces your real investable surplus. Clearing it first often delivers better risk-adjusted returns than investing.",
        "options": list(QUESTIONS["debt"]["options"]),
    },
]
TOTAL_Q_STEPS = len(WIZARD_STEPS)  # 5

# ── Session state ─────────────────────────────────────────────────────────────

if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "monthly_income" not in st.session_state:
    st.session_state.monthly_income = 20_000
if "result" not in st.session_state:
    st.session_state.result = None

# ── API key ───────────────────────────────────────────────────────────────────

def resolve_api_key() -> str | None:
    try:
        key = st.secrets.get("GROQ_API_KEY")
        if key:
            return key
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    return os.environ.get("GROQ_API_KEY") or None

API_KEY = resolve_api_key()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-size:0.95rem;font-weight:700;color:#E2E8F0;margin-bottom:0.2rem">'
        '<i class="bi bi-bar-chart-fill" style="color:#818CF8"></i> AI Asset Allocator</div>'
        '<div style="font-size:0.75rem;color:#334155">Groq · Llama 3.3 · Indian Markets</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    if not API_KEY:
        entered = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk-...",
            help="Free at [console.groq.com](https://console.groq.com). Leave blank for demo.",
        )
        if entered:
            API_KEY = entered
    else:
        st.markdown('<div style="font-size:0.78rem;color:#10B981"><i class="bi bi-check-circle-fill"></i> API key loaded</div>', unsafe_allow_html=True)

    if st.session_state.step > 0:
        st.divider()
        if st.button("Start Over", use_container_width=True):
            for k in ["step", "answers", "monthly_income", "result"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

# ── Helper ────────────────────────────────────────────────────────────────────

def centered():
    """Return the center column of a 3-column layout."""
    _, c, _ = st.columns([1, 2.2, 1])
    return c

def progress_dots(current_step: int):
    """Render wizard progress dots. current_step is 1-indexed question step."""
    dots = ""
    for i in range(1, TOTAL_Q_STEPS + 2):  # +2 for income step
        cls = "done" if i < current_step else ("active" if i == current_step else "prog-dot")
        if cls == "done":
            dots += f'<div class="prog-dot done"></div>'
        elif cls == "active":
            dots += f'<div class="prog-dot active"></div>'
        else:
            dots += f'<div class="prog-dot"></div>'
        if i < TOTAL_Q_STEPS + 1:
            dots += '<div class="prog-line"></div>'
    label = f'<span class="prog-label">{current_step} of {TOTAL_Q_STEPS + 1}</span>'
    st.markdown(f'<div class="progress-row">{dots}{label}</div>', unsafe_allow_html=True)

# ── Screens ───────────────────────────────────────────────────────────────────

def render_landing():
    with centered():
        st.markdown(
            '<div class="landing-wrap">'
            '  <div class="landing-eyebrow"><i class="bi bi-stars"></i> AI-Powered · Indian Markets</div>'
            '  <div class="landing-title">Find Your Perfect<br>Investment Mix</div>'
            '  <div class="landing-sub">Answer 6 questions. Get a personalised asset allocation '
            'built by AI — with clear reasoning for every decision.</div>'
            '  <div class="landing-pills">'
            '    <span class="pill"><i class="bi bi-shield-check"></i> CAPM-based scoring</span>'
            '    <span class="pill"><i class="bi bi-cpu"></i> Llama 3.3 · Groq</span>'
            '    <span class="pill"><i class="bi bi-bar-chart"></i> 2,000+ schemes analysed</span>'
            '    <span class="pill"><i class="bi bi-clock"></i> Under 2 minutes</span>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Get Started →", type="primary", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

        st.markdown(
            '<div class="trust-row">'
            '  <div class="trust-item"><div class="trust-num">5</div><div class="trust-label">Risk factors scored</div></div>'
            '  <div class="trust-item"><div class="trust-num">4</div><div class="trust-label">Asset classes</div></div>'
            '  <div class="trust-item"><div class="trust-num">0</div><div class="trust-label">Data stored</div></div>'
            '  <div class="trust-item"><div class="trust-num">100%</div><div class="trust-label">Free to use</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )


def render_question(step_idx: int):
    """Render a single question screen. step_idx is 0-indexed into WIZARD_STEPS."""
    q = WIZARD_STEPS[step_idx]
    q_step_num = step_idx + 1   # 1-indexed for display

    with centered():
        st.markdown('<div class="wizard-wrap">', unsafe_allow_html=True)
        progress_dots(q_step_num)

        st.markdown(
            f'<div class="q-icon-wrap"><i class="bi {q["icon"]}"></i></div>'
            f'<div class="q-heading">{q["heading"]}</div>'
            f'<div class="q-hint">{q["hint"]}</div>',
            unsafe_allow_html=True,
        )

        default_idx = 0
        if q["key"] in st.session_state.answers:
            try:
                default_idx = q["options"].index(st.session_state.answers[q["key"]])
            except ValueError:
                default_idx = 0

        choice = st.radio(
            "",
            q["options"],
            index=default_idx,
            key=f"radio_{q['key']}",
            label_visibility="collapsed",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        bcol, ncol = st.columns([1, 3])
        with bcol:
            if st.button("← Back", key=f"back_{step_idx}"):
                st.session_state.step -= 1
                st.rerun()
        with ncol:
            if st.button("Continue →", key=f"next_{step_idx}", type="primary", use_container_width=True):
                st.session_state.answers[q["key"]] = choice
                st.session_state.step += 1
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def render_income():
    """Step 6: monthly income + generate."""
    with centered():
        st.markdown('<div class="wizard-wrap">', unsafe_allow_html=True)
        progress_dots(TOTAL_Q_STEPS + 1)

        st.markdown(
            '<div class="q-icon-wrap"><i class="bi bi-currency-rupee"></i></div>'
            '<div class="income-label">How much can you invest each month?</div>'
            '<div class="income-hint">This helps calibrate your SIP recommendation. '
            'A general rule: invest at least 15–20% of your take-home income. '
            'You can always start smaller and step up annually.</div>',
            unsafe_allow_html=True,
        )

        income = st.number_input(
            "Monthly investable income (₹)",
            min_value=0, max_value=10_000_000,
            value=st.session_state.monthly_income,
            step=1_000, label_visibility="collapsed",
        )
        st.session_state.monthly_income = int(income)
        st.caption("Leave as 0 to skip the SIP recommendation.")

        st.markdown("<br>", unsafe_allow_html=True)
        bcol, ncol = st.columns([1, 3])
        with bcol:
            if st.button("← Back", key="back_income"):
                st.session_state.step -= 1
                st.rerun()
        with ncol:
            if st.button("Generate My Allocation →", key="generate", type="primary", use_container_width=True):
                st.session_state.result = None   # clear cached result
                st.session_state.step += 1
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


def render_results():
    """Final screen: full allocation results with tabs."""
    answers        = st.session_state.answers
    monthly_income = st.session_state.monthly_income or None

    age      = answers.get("age",      WIZARD_STEPS[0]["options"][0])
    horizon  = answers.get("horizon",  WIZARD_STEPS[1]["options"][1])
    goal     = answers.get("goal",     WIZARD_STEPS[2]["options"][3])
    reaction = answers.get("reaction", WIZARD_STEPS[3]["options"][1])
    debt     = answers.get("debt",     WIZARD_STEPS[4]["options"][2])

    risk_score  = compute_risk_score(age, horizon, goal, reaction, debt)
    risk_label  = get_risk_label(risk_score)
    gauge_color = score_to_gauge_color(risk_score)

    # Generate only once per session
    if st.session_state.result is None:
        with st.spinner("Building your allocation…"):
            st.session_state.result = get_allocation(
                age=age, horizon=horizon, goal=goal,
                reaction=reaction, debt=debt,
                risk_score=risk_score, risk_label=risk_label,
                monthly_income=monthly_income, api_key=API_KEY,
            )

    result     = st.session_state.result
    allocation = result.get("allocation", {})
    reasoning  = result.get("reasoning", {})
    is_demo    = result.get("_demo", False)
    has_error  = "_error" in result

    # Banners
    if has_error:
        st.warning(f"API error — showing demo allocation.\n\n`{result['_error']}`", icon="⚠️")
    elif is_demo:
        st.markdown(
            '<div class="demo-banner">'
            '<i class="bi bi-info-circle"></i>'
            '<span><strong>Demo mode</strong> — enter your Groq API key in the sidebar for a live personalised allocation.</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Risk profile hero ─────────────────────────────────────────────────────
    color, bg, border = RISK_COLORS.get(risk_label, ("#818CF8", "rgba(129,140,248,0.1)", "rgba(129,140,248,0.3)"))
    _, hcol, _ = st.columns([1, 1.5, 1])
    with hcol:
        st.markdown(
            '<div class="result-hero">'
            '  <div class="result-label">Your investor profile</div>'
            f' <div class="result-profile" style="color:{color};background:{bg};border:1px solid {border}">'
            f'   <i class="bi bi-activity"></i>{risk_label}'
            f' </div>'
            f' <div class="result-score">Risk score: <strong style="color:{color}">{risk_score}/100</strong></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["  Allocation  ", "  How You Compare  ", "  What's Next  "])

    # ── Tab 1: Allocation ─────────────────────────────────────────────────────
    with tab1:
        # 4 metric cards
        metric_html = '<div class="metric-row">'
        for i, (asset, pct) in enumerate(allocation.items()):
            c = ASSET_COLORS.get(asset, "#94A3B8")
            ic = ASSET_ICONS.get(asset, "bi-circle")
            d = f"{0.1*i:.1f}s"
            metric_html += (
                f'<div class="metric-card" style="animation-delay:{d};border-top:2px solid {c}22">'
                f'<div class="mc-icon"><i class="bi {ic}" style="color:{c}"></i></div>'
                f'<div class="mc-num" style="color:{c};animation-delay:{d}">{pct}%</div>'
                f'<div class="mc-label">{asset.capitalize()}</div>'
                f'</div>'
            )
        metric_html += '</div>'
        st.markdown(metric_html, unsafe_allow_html=True)

        # Donut + bars
        col_chart, col_bars = st.columns([1, 1])
        with col_chart:
            donut = go.Figure(go.Pie(
                labels=[k.capitalize() for k in allocation],
                values=list(allocation.values()),
                hole=0.62,
                marker=dict(
                    colors=[ASSET_COLORS.get(k, "#94A3B8") for k in allocation],
                    line=dict(color="#0F172A", width=3),
                ),
                textinfo="label+percent",
                textfont=dict(size=11),
                hovertemplate="<b>%{label}</b><br>%{value}%<extra></extra>",
                pull=[0.04]*len(allocation),
                direction="clockwise",
                sort=False,
            ))
            donut.update_layout(
                **PLOTLY_BASE, height=300, showlegend=False,
                margin=dict(t=10, b=10, l=0, r=0),
                annotations=[dict(
                    text=f'<b>{allocation.get("equity",0)}%</b><br>Equity',
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(color=ASSET_COLORS["equity"], size=18),
                )],
            )
            st.plotly_chart(donut, use_container_width=True)

        with col_bars:
            bars_html = '<div class="bar-section">'
            for i, (asset, pct) in enumerate(allocation.items()):
                c    = ASSET_COLORS.get(asset, "#94A3B8")
                ic   = ASSET_ICONS.get(asset, "bi-circle")
                grad = ASSET_GRAD.get(asset, f"linear-gradient(90deg,{c},{c})")
                rsn  = reasoning.get(asset, "")
                d    = f"{0.15+0.12*i:.2f}s"
                bars_html += (
                    f'<div class="bar-row">'
                    f'<div class="bar-label-row">'
                    f'  <span class="bar-name" style="color:{c}"><i class="bi {ic}"></i>{asset.capitalize()}</span>'
                    f'  <span class="bar-pct" style="color:{c}">{pct}%</span>'
                    f'</div>'
                    f'<div class="bar-bg"><div class="bar-fill" style="width:{pct}%;background:{grad};animation-delay:{d}"></div></div>'
                    f'<div class="bar-reason">{rsn}</div>'
                    f'</div>'
                )
            bars_html += '</div>'
            st.markdown(bars_html, unsafe_allow_html=True)

        # Key considerations inline (not a separate section)
        considerations = result.get("key_considerations", [])
        if considerations:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:600;text-transform:uppercase;'
                'letter-spacing:0.08em;color:#334155;margin-bottom:0.5rem">Things to keep in mind</div>',
                unsafe_allow_html=True,
            )
            items = "".join(
                f'<div class="consid-item"><i class="bi bi-check-circle-fill"></i><span>{c}</span></div>'
                for c in considerations
            )
            st.markdown(f'<div class="consid-wrap">{items}</div>', unsafe_allow_html=True)

    # ── Tab 2: Comparison ─────────────────────────────────────────────────────
    with tab2:
        st.markdown(
            '<div style="font-size:0.85rem;color:#475569;margin:0.5rem 0 1.2rem">'
            'See how your AI-generated allocation sits against the four standard risk profiles. '
            'Solid bars are yours — dimmed bars are benchmarks.'
            '</div>',
            unsafe_allow_html=True,
        )
        assets    = list(allocation.keys())
        pk_labels = ["Conservative", "Mod. Conservative", "Mod. Aggressive", "Aggressive"]
        pk_keys   = ["Conservative", "Moderate Conservative", "Moderate Aggressive", "Aggressive"]
        y_labels  = pk_labels + ["Your Profile"]

        comp = go.Figure()
        for asset in assets:
            c      = ASSET_COLORS.get(asset, "#94A3B8")
            values = [BASE_ALLOCATIONS[pk].get(asset, 0) for pk in pk_keys] + [allocation.get(asset, 0)]
            comp.add_trace(go.Bar(
                name=asset.capitalize(), y=y_labels, x=values, orientation="h",
                marker=dict(color=[c]*4 + [c], opacity=[0.3]*4+[1.0], line=dict(width=0)),
                hovertemplate=f"<b>{asset.capitalize()}</b>: %{{x}}%<extra></extra>",
                text=[f"{v}%" for v in values],
                textposition="inside", textfont=dict(size=10, color="white"),
                insidetextanchor="middle",
            ))
        comp.update_layout(
            **PLOTLY_BASE, barmode="stack", height=300,
            margin=dict(t=10, b=10, l=0, r=0),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11), bgcolor=TRANSPARENT),
            yaxis=dict(tickfont=dict(size=11),
                       categoryorder="array", categoryarray=list(reversed(y_labels))),
            xaxis=dict(range=[0,105], ticksuffix="%", gridcolor="#1E293B", tickfont=dict(size=10)),
            shapes=[dict(type="line", x0=0, x1=1, y0=0.56, y1=0.56,
                         xref="paper", yref="paper",
                         line=dict(color="#334155", width=1, dash="dot"))],
        )
        st.plotly_chart(comp, use_container_width=True)

        # Gauge for context
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_score,
            number={"font": {"color": gauge_color, "size": 40}, "suffix": "/100"},
            title={"text": "RISK SCORE", "font": {"color": "#334155", "size": 11}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#334155", "tickwidth": 1,
                         "tickvals": [0,30,55,70,100]},
                "bar": {"color": gauge_color, "thickness": 0.2},
                "steps": [
                    {"range": [0,  30], "color": "rgba(16,185,129,0.07)"},
                    {"range": [31, 55], "color": "rgba(245,158,11,0.07)"},
                    {"range": [56, 70], "color": "rgba(249,115,22,0.07)"},
                    {"range": [71,100], "color": "rgba(239,68,68,0.07)"},
                ],
                "threshold": {"line": {"color": gauge_color, "width": 2}, "value": risk_score},
                "bgcolor": TRANSPARENT, "borderwidth": 0,
            },
        ))
        gauge.update_layout(**PLOTLY_BASE, height=220, margin=dict(t=30, b=0, l=20, r=20))
        _, gc, _ = st.columns([1, 1, 1])
        with gc:
            st.plotly_chart(gauge, use_container_width=True)

    # ── Tab 3: What's Next ────────────────────────────────────────────────────
    with tab3:
        # SIP card
        sip = result.get("monthly_sip_suggestion")
        if sip:
            pct_str = f" — {sip/monthly_income*100:.0f}% of your income" if monthly_income else ""
            st.markdown(
                f'<div class="sip-card">'
                f'<div class="sip-icon"><i class="bi bi-currency-rupee"></i></div>'
                f'<div>'
                f'  <div class="sip-label">Suggested Monthly SIP</div>'
                f'  <div class="sip-amount">₹{sip:,}</div>'
                f'  <div class="sip-sub">Start here · Increase 10% annually{pct_str}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Actionable next steps
        st.markdown(
            '<div style="font-size:0.82rem;font-weight:600;text-transform:uppercase;'
            'letter-spacing:0.08em;color:#334155;margin:1rem 0 0.75rem">Action plan</div>',
            unsafe_allow_html=True,
        )
        equity_pct = allocation.get("equity", 0)
        debt_pct   = allocation.get("debt", 0)

        steps_list = [
            ("Build your emergency fund first",
             f"Keep 3–6 months of expenses in a liquid fund or high-yield savings account before investing. "
             f"This prevents you from redeeming your investments during a crisis."),
            ("Start your SIP on the 1st of next month",
             f"Set up an automatic SIP of ₹{sip:,}/month" if sip else
             "Set up a monthly SIP — automation removes the temptation to time the market."),
            (f"Invest {equity_pct}% in equity via Large Cap / Flexi Cap funds",
             "Choose direct plans (lower expense ratio) over regular plans. "
             "Platforms: Zerodha Coin, Groww, or directly through fund house websites."),
            (f"Invest {debt_pct}% in debt via short-duration or liquid funds",
             "Debt allocation provides stability. Short-duration funds offer better returns than FDs "
             "with similar liquidity. Avoid locking everything in long-duration funds."),
            ("Review once a year — not every day",
             "Checking your portfolio daily causes emotional decisions. Set a calendar reminder "
             "for an annual review to rebalance back to your target allocation."),
        ]
        for i, (title, body) in enumerate(steps_list, start=1):
            d = f"{0.1*i:.1f}s"
            st.markdown(
                f'<div class="next-step-card" style="animation-delay:{d}">'
                f'  <div class="ns-num">{i}</div>'
                f'  <div><div class="ns-title">{title}</div><div class="ns-body">{body}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Fund recommendations
        fund_recs = build_fund_recommendations(equity_pct, risk_label, goal)
        if fund_recs:
            st.markdown(
                '<div style="font-size:0.82rem;font-weight:600;text-transform:uppercase;'
                'letter-spacing:0.08em;color:#334155;margin:1.2rem 0 0.75rem">Fund categories for your equity allocation</div>',
                unsafe_allow_html=True,
            )
            for rec in fund_recs:
                top_funds = rec.get("top_funds", [])
                picks = ""
                if top_funds:
                    picks = "".join(
                        f'<div class="fund-pick">'
                        f'  <span class="fund-rank">#{f.get("category_rank","—")}</span>'
                        f'  <span style="flex:1">{f.get("scheme_name","—")}</span>'
                        f'  <span style="color:#334155;font-size:0.72rem">score {f.get("composite_score",0):.2f}</span>'
                        f'</div>'
                        for f in top_funds
                    )
                st.markdown(
                    f'<div class="fund-card">'
                    f'  <div class="fund-card-title">'
                    f'    <i class="bi bi-collection" style="color:#818CF8;font-size:0.85rem"></i>'
                    f'    {rec["category"]}'
                    f'    <span class="fund-badge">{rec["suggested_weight"]}</span>'
                    f'  </div>'
                    f'  <div class="fund-rationale">{rec["rationale"]}</div>'
                    f'  {picks}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="disclaimer">'
        '<strong>Disclaimer:</strong> This tool is for educational and portfolio demonstration purposes only. '
        'It does not constitute financial advice. Please consult a SEBI-registered investment advisor '
        'before making investment decisions. Mutual fund investments are subject to market risk. '
        'Read all scheme-related documents carefully before investing.'
        '</div>'
        '<div class="footer">Built by <strong>Veer Pratap Singh</strong> &nbsp;·&nbsp; '
        '<a href="https://github.com/VeerVVAPS-portfolio">GitHub</a> &nbsp;·&nbsp; '
        '<a href="https://linkedin.com/in/veer-pratap-singh-681a5530b">LinkedIn</a></div>',
        unsafe_allow_html=True,
    )

# ── Router ────────────────────────────────────────────────────────────────────

step = st.session_state.step

if step == 0:
    render_landing()
elif 1 <= step <= TOTAL_Q_STEPS:
    render_question(step - 1)
elif step == TOTAL_Q_STEPS + 1:
    render_income()
else:
    render_results()
