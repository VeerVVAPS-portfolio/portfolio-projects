"""
Streamlit dashboard — Mutual Fund Analytics Automation (Project 1).

Run: streamlit run dashboard/app.py  (from the project root)
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scoring import apply_eligibility_filter, compute_composite_score  # noqa: E402

st.set_page_config(page_title="Fund Rankings | Mutual Fund Analytics", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0A0A0E !important;
    color: #E4E4E7 !important;
}

/* ── Colour system ── */
:root {
    --bg:      #0A0A0E;
    --surf:    #111116;
    --surf2:   #18181F;
    --bdr:     rgba(255,255,255,0.06);
    --bdr2:    rgba(255,255,255,0.12);
    --rule:    rgba(255,255,255,0.05);
    --t1:      #F4F4F5;
    --t2:      #A1A1AA;
    --t3:      #71717A;
    --t4:      #52525B;
    --acc:     #818CF8;
    --gold:    #E4C76B;
    --green:   #10B981;
    --amber:   #F59E0B;
    --sky:     #38BDF8;
}

/* ── Animations ── */
@keyframes fadeUp   { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn   { from{opacity:0} to{opacity:1} }
@keyframes countUp  { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

/* Modern Streamlit (1.4x+) renamed its CSS-module classnames from
   "css-xxxxx" to "st-emotion-cache-xxxxx", which silently broke the old
   [class*="css"] trick for the main content panel and header — only the
   explicitly-targeted [data-testid="stSidebar"] still picked up the dark
   theme, leaving the main panel on Streamlit's default white background.
   Target the stable data-testid hooks directly instead. */
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
    background-color: var(--bg) !important;
}
[data-testid="stHeader"] { background-color: transparent !important; }

/* Streamlit's native widget labels (slider/radio captions) render with the
   framework's own light-theme text color and aren't reliably caught by the
   global override above — force them to the readable muted tone. */
[data-testid="stWidgetLabel"] p, .stRadio label p, .stSlider label p {
    color: var(--t2) !important;
}

/* st.caption() renders its container at 60% opacity by default, which
   combined with an already-muted text color drops effective contrast well
   below WCAG AA — these captions carry real explanatory content, not
   decorative chrome, so force full opacity and a legible color. */
[data-testid="stCaptionContainer"] {
    opacity: 1 !important;
}
[data-testid="stCaptionContainer"] p {
    color: var(--t2) !important;
}

/* ── Global overrides ── */
.block-container { padding-top: 2.5rem !important; max-width: 1100px !important; }
[data-testid="stSidebar"] {
    background: var(--surf) !important;
    border-right: 1px solid var(--bdr) !important;
}

/* ── Sidebar ── */
.sb-brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1rem; font-weight: 700; color: var(--t1);
    letter-spacing: -0.01em; margin-bottom: 0.15rem;
}
.sb-sub { font-size: 0.7rem; color: var(--t4); letter-spacing: 0.04em; text-transform: uppercase; }
.sb-section {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--t4); margin-bottom: 0.5rem;
}

/* ── Page header ── */
.ph-wrap { padding: 1rem 0 2.5rem; animation: fadeUp 0.6s ease both; }
.ph-eyebrow {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--acc); margin-bottom: 1rem;
}
.ph-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.8rem; font-weight: 700; line-height: 1.0;
    letter-spacing: -0.03em; color: var(--t1); margin-bottom: 1.2rem;
}
.ph-title span { color: var(--acc); }
.ph-stats {
    display: flex; align-items: center; gap: 2rem; flex-wrap: wrap;
    padding: 1.2rem 0;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
}
.ph-stat-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem; font-weight: 700; color: var(--t1); line-height: 1;
}
.ph-stat-label { font-size: 0.68rem; color: var(--t3); margin-top: 0.2rem; letter-spacing: 0.04em; }
.ph-divider { width: 1px; height: 2rem; background: var(--rule); }

/* ── Section heading ── */
.sec-head {
    display: flex; align-items: center; gap: 0.6rem;
    padding: 2rem 0 1rem;
    border-top: 1px solid var(--rule);
    animation: fadeUp 0.5s ease both;
}
.sec-head-label {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--t4);
}
.sec-head-line { flex: 1; height: 1px; background: var(--rule); }

/* ── Top pick — content on canvas, no card box ── */
.tp-wrap { padding: 0.5rem 0 1.5rem; animation: fadeUp 0.5s ease both; }
.tp-rank {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--green); margin-bottom: 0.9rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.tp-rank::before {
    content: '';
    display: inline-block; width: 6px; height: 6px;
    background: var(--green); border-radius: 50%;
}
.tp-fund-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
    color: var(--t1); line-height: 1.2; margin-bottom: 0.4rem;
}
.tp-amc {
    font-size: 0.82rem; color: var(--t3); margin-bottom: 2rem;
}
.tp-stats {
    display: flex; gap: 3rem; flex-wrap: wrap;
    padding-top: 1.5rem;
    border-top: 1px solid var(--rule);
}
.tp-stat { }
.tp-stat-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.2rem; font-weight: 700; letter-spacing: -0.03em; line-height: 1;
    animation: countUp 0.6s ease both;
}
.tp-stat-label {
    font-size: 0.68rem; color: var(--t3); margin-top: 0.35rem;
    letter-spacing: 0.06em; text-transform: uppercase;
}

/* ── Method row ── */
.method-row {
    display: flex; gap: 0; flex-wrap: nowrap;
    border: 1px solid var(--bdr); border-radius: 12px; overflow: hidden;
    margin: 0.5rem 0 1rem; animation: fadeIn 0.7s ease both;
}
.method-cell {
    flex: 1; padding: 1rem 1.2rem;
    border-right: 1px solid var(--bdr);
}
.method-cell:last-child { border-right: none; }
.method-cell-title {
    font-size: 0.72rem; font-weight: 600; color: var(--t1);
    letter-spacing: 0.03em; margin-bottom: 0.25rem;
    display: flex; align-items: center; gap: 0.35rem;
}
.method-cell-title i { color: var(--acc); font-size: 0.75rem; }
.method-cell-body { font-size: 0.73rem; color: var(--t3); line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ── Shared style constants ────────────────────────────────────────────────────

CHART_FONT    = "#71717A"       # zinc-500 — subtle axis labels on dark bg
HOVER_FONT    = "#F4F4F5"       # near-white text inside hover tooltip
HOVER_BG      = "#18181F"       # dark tooltip bg
GRID_COLOR    = "#27272A"       # zinc-800 — barely-visible grid lines
ACCENT_GREEN  = "#10B981"
ACCENT_PURPLE = "#818CF8"
TOP3_BG = "#052e16"             # dark green row highlight for dark theme
TOP3_FG = "#6ee7b7"             # light green text on dark — WCAG AA
TRANSPARENT = "rgba(0,0,0,0)"

PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT,
    plot_bgcolor=TRANSPARENT,
    font=dict(color=CHART_FONT, family="Space Grotesk, Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor=HOVER_BG, font_size=13, font_color=HOVER_FONT, bordercolor="#27272A"),
)

# ── Data ─────────────────────────────────────────────────────────────────────

@st.cache_data
def load_eligible_funds() -> pd.DataFrame:
    schemes = pd.read_csv(PROJECT_ROOT / "data/processed/schemes.csv")
    metrics = pd.read_csv(PROJECT_ROOT / "data/processed/metrics.csv").drop(
        columns=["scheme_name", "category"]
    )
    return apply_eligibility_filter(schemes.merge(metrics, on="scheme_code"))

eligible = load_eligible_funds()

# ── Investor profiles ─────────────────────────────────────────────────────────

PROFILES = {
    "Balanced (Default)": {
        "weights": {"sharpe": 1 / 3, "alpha": 1 / 3, "consistency": 1 / 3},
        "desc": "Equal weight across all three metrics — a sensible starting point for most investors.",
    },
    "Safety First": {
        "weights": {"sharpe": 0.20, "alpha": 0.10, "consistency": 0.70},
        "desc": (
            "Prioritises **Consistency** — funds that repeatedly beat peers "
            "across multiple 3-year windows. Suits conservative investors who value "
            "steady, predictable performance over raw returns."
        ),
    },
    "Return Seeker": {
        "weights": {"sharpe": 0.20, "alpha": 0.70, "consistency": 0.10},
        "desc": (
            "Prioritises **Jensen's Alpha** — the extra return a manager earns beyond "
            "what the fund's market risk alone would predict. "
            "Suits growth-focused investors comfortable with variance."
        ),
    },
    "Risk-Adjusted": {
        "weights": {"sharpe": 0.70, "alpha": 0.20, "consistency": 0.10},
        "desc": (
            "Prioritises **Sharpe Ratio** — return earned per unit of volatility. "
            "Suits investors who want the smoothest ride for the return they receive."
        ),
    },
    "Custom": {
        "weights": None,
        "desc": "Set your own weights using the sliders below.",
    },
}

SHARPE_HELP = (
    "Return earned per unit of risk (volatility) taken. "
    "A Sharpe of 1.0 means you earn 1% excess return for every 1% of volatility — "
    "higher is better. Computed over the trailing 3 years vs a 7% risk-free rate (India G-Sec)."
)
ALPHA_HELP = (
    "The manager's 'skill score'. It measures how much extra return the fund earned "
    "beyond what its market sensitivity (Beta) alone predicts via CAPM. "
    "Positive = manager added value; negative = lagged behind even accounting for risk."
)
CONSISTENCY_HELP = (
    "Percentage of rolling 3-year windows where this fund beat its category average. "
    "60% means the fund outperformed peers in 6 out of every 10 three-year periods — "
    "more reliable than a single snapshot return."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sb-brand">Fund Analytics</div>'
        '<div class="sb-sub">AMFI &nbsp;·&nbsp; Indian Equity</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown('<div class="sb-section">Category</div>', unsafe_allow_html=True)
    short_name = lambda c: c.replace("Equity Scheme - ", "").replace(" Fund", "")
    categories = sorted(eligible["category"].unique())
    category = st.selectbox(
        "Fund category",
        categories,
        format_func=short_name,
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown('<div class="sb-section">Investor Style</div>', unsafe_allow_html=True)
    profile_name = st.selectbox(
        "Profile",
        list(PROFILES.keys()),
        label_visibility="collapsed",
    )
    profile = PROFILES[profile_name]
    st.caption(profile["desc"])

    if profile["weights"] is None:
        st.markdown("**Adjust weights** — auto-normalised to 100%")
        sharpe_w     = st.slider("Sharpe Ratio",    0.0, 1.0, 1/3, 0.05, help=SHARPE_HELP)
        alpha_w      = st.slider("Jensen's Alpha",  0.0, 1.0, 1/3, 0.05, help=ALPHA_HELP)
        consistency_w = st.slider("Consistency",    0.0, 1.0, 1/3, 0.05, help=CONSISTENCY_HELP)
        total = sharpe_w + alpha_w + consistency_w
        if total == 0:
            st.error("At least one weight must be greater than 0.")
            st.stop()
        weights = {
            "sharpe": sharpe_w / total,
            "alpha": alpha_w / total,
            "consistency": consistency_w / total,
        }
    else:
        weights = profile["weights"]

    st.caption(
        f"Effective weights — "
        f"Sharpe **{weights['sharpe']:.0%}** · "
        f"Alpha **{weights['alpha']:.0%}** · "
        f"Consistency **{weights['consistency']:.0%}**"
    )

    st.divider()

    with st.expander("What do these metrics mean?"):
        st.markdown(
            """
**Sharpe Ratio**
Return per unit of volatility. Higher is better. Above 1.0 is considered strong.

---
**Jensen's Alpha**
Manager skill score. Extra return beyond what market risk alone predicts.
Positive = manager adds value.

---
**Consistency**
% of rolling 3-year windows where the fund beat its category average.
More reliable than a single snapshot return.

---
**Beta**
Fund movement relative to NIFTY 50. Beta 1.2 = 20% more volatile than the index.

---
**5Y Return (CAGR)**
Compounded annual growth over 5 years — the annualised return from a lump-sum 5 years ago.
            """
        )

# ── Scoring ───────────────────────────────────────────────────────────────────

scored      = compute_composite_score(eligible, weights)
category_df = scored[scored["category"] == category].sort_values("category_rank")
top         = category_df.iloc[0]
cat_label   = short_name(category)

# ── Page header ───────────────────────────────────────────────────────────────

def short_fund_name(name: str, max_len: int = 32) -> str:
    name = name.replace("Equity Scheme - ", "").replace("(Direct Plan)", "").strip()
    return name if len(name) <= max_len else name[:max_len].rstrip() + "..."

top_display = short_fund_name(top["scheme_name"])

st.markdown(
    f'<div class="ph-wrap">'
    f'  <div class="ph-eyebrow">Mutual Fund Analytics</div>'
    f'  <div class="ph-title">{cat_label}<br><span>Funds.</span></div>'
    f'  <div class="ph-stats">'
    f'    <div><div class="ph-stat-num">{len(eligible)}</div><div class="ph-stat-label">Funds screened</div></div>'
    f'    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">{eligible["category"].nunique()}</div><div class="ph-stat-label">Categories</div></div>'
    f'    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">{len(category_df)}</div><div class="ph-stat-label">Eligible in {cat_label}</div></div>'
    f'    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">₹1,000 Cr+</div><div class="ph-stat-label">Min AUM threshold</div></div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# Methodology row
st.markdown(
    '<div class="method-row">'
    '  <div class="method-cell">'
    '    <div class="method-cell-title"><i class="bi bi-graph-up-arrow"></i> Sharpe Ratio</div>'
    '    <div class="method-cell-body">Return earned per unit of volatility, trailing 3Y vs 7% G-Sec rate.</div>'
    '  </div>'
    '  <div class="method-cell">'
    '    <div class="method-cell-title"><i class="bi bi-bullseye"></i> Jensen\'s Alpha</div>'
    '    <div class="method-cell-body">Manager skill — extra return beyond what market Beta alone predicts.</div>'
    '  </div>'
    '  <div class="method-cell">'
    '    <div class="method-cell-title"><i class="bi bi-shield-check"></i> Consistency</div>'
    '    <div class="method-cell-body">% of rolling 3Y windows where the fund beat its category average.</div>'
    '  </div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Top pick ──────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head">'
    '  <div class="sec-head-label">Top Pick</div>'
    '  <div class="sec-head-line"></div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="tp-wrap">'
    f'  <div class="tp-rank">Ranked #1 in {cat_label}</div>'
    f'  <div class="tp-fund-name">{top_display}</div>'
    f'  <div class="tp-amc">{top["amc"]}</div>'
    f'  <div class="tp-stats">'
    f'    <div class="tp-stat"><div class="tp-stat-val" style="color:var(--green)">{top["return_5y"]:.1%}</div><div class="tp-stat-label">5Y Return (CAGR)</div></div>'
    f'    <div class="tp-stat"><div class="tp-stat-val" style="color:var(--acc)">{top["sharpe"]:.2f}</div><div class="tp-stat-label">Sharpe Ratio</div></div>'
    f'    <div class="tp-stat"><div class="tp-stat-val" style="color:var(--gold)">{top["consistency"]:.0%}</div><div class="tp-stat-label">Consistency</div></div>'
    f'    <div class="tp-stat"><div class="tp-stat-val" style="color:var(--sky)">{top["composite_score"]:.0%}</div><div class="tp-stat-label">Composite Score</div></div>'
    f'  </div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Ranked table ──────────────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head">'
    '  <div class="sec-head-label">All Eligible Funds</div>'
    '  <div class="sec-head-line"></div>'
    '</div>',
    unsafe_allow_html=True,
)

display_cols = {
    "category_rank": "Rank",
    "scheme_name":   "Fund",
    "amc":           "AMC",
    "total_aum_cr":  "AUM (Cr)",
    "return_5y":     "5Y Return",
    "beta":          "Beta",
    "sharpe":        "Sharpe",
    "alpha":         "Alpha",
    "consistency":   "Consistency",
    "composite_score": "Score",
}
table = category_df[list(display_cols.keys())].rename(columns=display_cols)


def highlight_top3(row):
    if row["Rank"] <= 3:
        style = f"background-color: {TOP3_BG}; color: {TOP3_FG}; font-weight: 600"
    else:
        style = ""
    return [style] * len(row)


styled = (
    table.style
    .format({
        "AUM (Cr)":  "{:,.0f}",
        "5Y Return": "{:.1%}",
        "Beta":      "{:.2f}",
        "Sharpe":    "{:.2f}",
        "Alpha":     "{:.1%}",
        "Consistency": "{:.1%}",
        "Score":     "{:.1%}",
    })
    .apply(highlight_top3, axis=1)
)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Horizontal bar chart ──────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head">'
    '  <div class="sec-head-label">Composite Score — All Funds</div>'
    '  <div class="sec-head-line"></div>'
    '</div>',
    unsafe_allow_html=True,
)

chart_df = category_df.copy()
chart_df["label"] = (
    "#" + chart_df["category_rank"].astype(str)
    + "  " + chart_df["scheme_name"]
              .str.replace(r"Equity Scheme\s*-\s*", "", regex=True)
              .str.replace(" Fund", "")
              .str.strip()
              .str[:38]
)
chart_df["score_pct"] = (chart_df["composite_score"] * 100).round(1).astype(str) + "%"
chart_df_sorted = chart_df.sort_values("composite_score")

bar_colors = [ACCENT_GREEN if r <= 3 else ACCENT_PURPLE
              for r in chart_df_sorted["category_rank"]]

bar_fig = go.Figure(go.Bar(
    x=chart_df_sorted["composite_score"],
    y=chart_df_sorted["label"],
    orientation="h",
    text=chart_df_sorted["score_pct"],
    textposition="outside",
    cliponaxis=False,
    marker_color=bar_colors,
    marker_line_width=0,
    hovertemplate="<b>%{y}</b><br>Score: %{x:.1%}<extra></extra>",
))

bar_fig.update_layout(
    **PLOTLY_BASE,
    margin=dict(l=10, r=60, t=10, b=40),
    height=max(320, len(chart_df) * 38),
    xaxis=dict(
        tickformat=".0%",
        range=[0, 1.18],
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=CHART_FONT, size=11),
        title=dict(text="Composite Score (percentile rank vs category peers)",
                   font=dict(color=CHART_FONT, size=11)),
    ),
    yaxis=dict(
        autorange=True,
        tickfont=dict(color=CHART_FONT, size=11),
        showgrid=False,
    ),
)

# Legend annotation
bar_fig.add_annotation(
    x=1.15, y=0.02, xref="paper", yref="paper",
    text=(
        f"<span style='color:{ACCENT_GREEN}'>&#9632;</span> Top 3  "
        f"<span style='color:{ACCENT_PURPLE}'>&#9632;</span> Others"
    ),
    showarrow=False,
    font=dict(size=11, color=CHART_FONT),
    align="right",
    xanchor="right",
)

st.plotly_chart(bar_fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Radar chart (top 3) ───────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head">'
    '  <div class="sec-head-label">Top 3 — Head-to-Head Comparison</div>'
    '  <div class="sec-head-line"></div>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="font-size:0.78rem;color:var(--t3);margin-bottom:0.75rem">'
    'Each axis shows the fund\'s percentile rank within the category. '
    'Outer edge = 100th percentile (best in category).'
    '</div>',
    unsafe_allow_html=True,
)

top3 = category_df[category_df["category_rank"] <= 3].copy()
radar_metrics = ["sharpe_pct", "alpha_pct", "consistency_pct"]
radar_labels  = ["Sharpe", "Alpha", "Consistency"]
radar_colors  = [ACCENT_GREEN, ACCENT_PURPLE, "#F59E0B"]

radar_fig = go.Figure()
for i, (_, row) in enumerate(top3.iterrows()):
    vals = [row[m] for m in radar_metrics] + [row[radar_metrics[0]]]
    short = short_fund_name(row["scheme_name"], max_len=28)
    radar_fig.add_trace(go.Scatterpolar(
        r=vals,
        theta=radar_labels + [radar_labels[0]],
        fill="toself",
        name=f"#{int(row['category_rank'])}  {short}",
        line=dict(color=radar_colors[i], width=2),
        fillcolor=radar_colors[i],
        opacity=0.18,
    ))

radar_fig.update_layout(
    **PLOTLY_BASE,
    margin=dict(l=40, r=40, t=20, b=60),
    height=400,
    polar=dict(
        bgcolor=TRANSPARENT,
        radialaxis=dict(
            visible=True,
            range=[0, 1],
            tickformat=".0%",
            tickfont=dict(size=10, color=CHART_FONT),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
        ),
        angularaxis=dict(
            tickfont=dict(size=13, color=CHART_FONT),
            linecolor=GRID_COLOR,
            gridcolor=GRID_COLOR,
        ),
    ),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=-0.28,
        xanchor="center", x=0.5,
        font=dict(color=CHART_FONT, size=11),
    ),
)

st.plotly_chart(radar_fig, use_container_width=True)
