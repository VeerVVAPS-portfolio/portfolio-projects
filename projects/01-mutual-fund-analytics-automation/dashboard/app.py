"""
Streamlit dashboard — Mutual Fund Analytics Automation (Project 1).

Run: streamlit run dashboard/app.py  (from the project root)
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scoring import apply_eligibility_filter, compute_composite_score  # noqa: E402

st.set_page_config(page_title="Fund Rankings", layout="wide", page_icon="📊")

# ── Data ────────────────────────────────────────────────────────────────────

@st.cache_data
def load_eligible_funds() -> pd.DataFrame:
    schemes = pd.read_csv(PROJECT_ROOT / "data/processed/schemes.csv")
    metrics = pd.read_csv(PROJECT_ROOT / "data/processed/metrics.csv").drop(
        columns=["scheme_name", "category"]
    )
    return apply_eligibility_filter(schemes.merge(metrics, on="scheme_code"))

eligible = load_eligible_funds()

# ── Investor profiles ────────────────────────────────────────────────────────
# Each preset translates a plain-English investing priority into metric weights.

PROFILES = {
    "⚖️ Balanced (Default)": {
        "weights": {"sharpe": 1 / 3, "alpha": 1 / 3, "consistency": 1 / 3},
        "desc": "Equal weight across all three metrics — a sensible starting point.",
    },
    "🛡️ Safety First": {
        "weights": {"sharpe": 0.20, "alpha": 0.10, "consistency": 0.70},
        "desc": (
            "Heavily weights **Consistency** — funds that repeatedly beat peers "
            "over rolling 3-year windows. Good for investors who value steady, "
            "predictable performance over raw returns."
        ),
    },
    "📈 Return Seeker": {
        "weights": {"sharpe": 0.20, "alpha": 0.70, "consistency": 0.10},
        "desc": (
            "Heavily weights **Jensen's Alpha** — the extra return a fund manager "
            "earns beyond what its market risk alone would predict. "
            "Suits growth-focused investors comfortable with variance."
        ),
    },
    "🎯 Risk-Adjusted": {
        "weights": {"sharpe": 0.70, "alpha": 0.20, "consistency": 0.10},
        "desc": (
            "Heavily weights **Sharpe Ratio** — return earned per unit of volatility. "
            "Suits investors who worry about drawdowns and want the smoothest ride "
            "for the return they receive."
        ),
    },
    "🔧 Custom": {
        "weights": None,
        "desc": "Set your own weights using the sliders below.",
    },
}

SHARPE_HELP = (
    "Return earned per unit of risk (volatility) taken. "
    "A Sharpe Ratio of 1.0 means you earn 1% excess return for every 1% of volatility — "
    "higher is better. Computed over the trailing 3 years vs a 7% risk-free rate (India G-Sec)."
)
ALPHA_HELP = (
    "The 'manager skill' score. It measures how much extra return the fund earned "
    "beyond what its market sensitivity (Beta) alone would predict using the CAPM formula. "
    "A positive Alpha means the manager added value; negative means they lagged behind "
    "even accounting for risk. Computed over the trailing 3 years vs NIFTY 50."
)
CONSISTENCY_HELP = (
    "The % of rolling 3-year windows where this fund beat its category average return. "
    "60% means the fund outperformed peers in 6 out of every 10 three-year periods — "
    "a more reliable signal than a single snapshot return."
)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("📂 Browse Category")
    short_name = lambda c: c.replace("Equity Scheme - ", "").replace(" Fund", "")
    categories = sorted(eligible["category"].unique())
    category = st.selectbox(
        "Fund category",
        categories,
        format_func=short_name,
        label_visibility="collapsed",
    )

    st.divider()

    st.header("🎯 What Matters to You?")
    profile_name = st.selectbox(
        "Investor style",
        list(PROFILES.keys()),
        label_visibility="collapsed",
    )
    profile = PROFILES[profile_name]
    st.caption(profile["desc"])

    if profile["weights"] is None:
        # Custom mode — show sliders
        st.markdown("**Adjust weights** (they'll be auto-normalised to 100%)")
        sharpe_w = st.slider(
            "Sharpe Ratio",
            0.0, 1.0, 1 / 3, 0.05,
            help=SHARPE_HELP,
        )
        alpha_w = st.slider(
            "Jensen's Alpha",
            0.0, 1.0, 1 / 3, 0.05,
            help=ALPHA_HELP,
        )
        consistency_w = st.slider(
            "Consistency",
            0.0, 1.0, 1 / 3, 0.05,
            help=CONSISTENCY_HELP,
        )
        total = sharpe_w + alpha_w + consistency_w
        if total == 0:
            st.error("At least one weight must be > 0.")
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

    with st.expander("📖 What do these metrics mean?"):
        st.markdown(
            """
**Sharpe Ratio**
Return earned per unit of risk (volatility). Higher = better.
A ratio above 1 is generally considered strong.

---

**Jensen's Alpha**
The fund manager's "skill score" — extra return beyond what the
fund's market sensitivity alone explains. Positive = manager adds value.

---

**Consistency**
% of rolling 3-year windows where the fund beat its category average.
More reliable than a single return snapshot because it tests performance
across multiple market cycles.

---

**Beta**
How much the fund moves relative to NIFTY 50.
Beta of 1.2 → the fund is 20% more volatile than the index.

---

**5Y Return (CAGR)**
Compounded Annual Growth Rate over 5 years — the annualised return if you had
invested 5 years ago and held to today.
            """
        )

# ── Scoring ──────────────────────────────────────────────────────────────────

scored = compute_composite_score(eligible, weights)
category_df = scored[scored["category"] == category].sort_values("category_rank")
top = category_df.iloc[0]
cat_label = short_name(category)

# ── Main area ────────────────────────────────────────────────────────────────

st.title(f"📊 {cat_label} Funds — Ranked Picks")
st.caption(
    f"{len(eligible)} funds eligible across {eligible['category'].nunique()} categories "
    f"(AUM ≥ ₹1,000 Cr · 5yr+ track record) · "
    f"Showing **{len(category_df)} eligible** in {cat_label}"
)

# ── Top-pick banner ───────────────────────────────────────────────────────────

st.subheader("🥇 Top Pick")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Fund", top["scheme_name"].replace("Fund", "").strip())
c2.metric("AMC", top["amc"])
c3.metric("5Y Return", f"{top['return_5y']:.1%}")
c4.metric("Sharpe", f"{top['sharpe']:.2f}", help=SHARPE_HELP)
c5.metric("Consistency", f"{top['consistency']:.0%}", help=CONSISTENCY_HELP)

st.divider()

# ── Ranked table ─────────────────────────────────────────────────────────────

st.subheader("All Eligible Funds — Ranked")

display_cols = {
    "category_rank": "Rank",
    "scheme_name": "Fund",
    "amc": "AMC",
    "total_aum_cr": "AUM (₹Cr)",
    "return_5y": "5Y Return",
    "beta": "Beta",
    "sharpe": "Sharpe",
    "alpha": "Alpha",
    "consistency": "Consistency",
    "composite_score": "Score",
}
table = category_df[list(display_cols.keys())].rename(columns=display_cols)


def highlight_top3(row):
    color = "background-color: #D1FAE5; font-weight: 600" if row["Rank"] <= 3 else ""
    return [color] * len(row)


styled = table.style.format({
    "AUM (₹Cr)": "{:,.0f}",
    "5Y Return": "{:.1%}",
    "Beta": "{:.2f}",
    "Sharpe": "{:.2f}",
    "Alpha": "{:.1%}",
    "Consistency": "{:.1%}",
    "Score": "{:.1%}",
}).apply(highlight_top3, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ── Plotly bar chart ──────────────────────────────────────────────────────────

st.subheader("Composite Score — All Funds")

chart_df = category_df.copy()
chart_df["short_name"] = chart_df["scheme_name"].str.replace(
    r"Equity Scheme\s*-\s*", "", regex=True
).str.replace(" Fund", "").str.strip()
chart_df["is_top3"] = chart_df["category_rank"] <= 3
chart_df["score_label"] = (chart_df["composite_score"] * 100).round(1).astype(str) + "%"
chart_df["rank_label"] = "#" + chart_df["category_rank"].astype(str) + " · " + chart_df["short_name"]

chart_df_sorted = chart_df.sort_values("composite_score")

colors = ["#10B981" if t else "#818CF8" for t in chart_df_sorted["is_top3"]]

fig = go.Figure(go.Bar(
    x=chart_df_sorted["composite_score"],
    y=chart_df_sorted["rank_label"],
    orientation="h",
    text=chart_df_sorted["score_label"],
    textposition="outside",
    cliponaxis=False,
    marker_color=colors,
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Score: %{x:.1%}<br>"
        "<extra></extra>"
    ),
))

fig.update_layout(
    xaxis=dict(
        tickformat=".0%",
        range=[0, 1.15],
        showgrid=True,
        gridcolor="#F1F5F9",
        title="Composite Score (percentile rank vs category peers)",
        title_font_size=12,
    ),
    yaxis=dict(autorange=True, tickfont_size=12),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=10, r=60, t=10, b=40),
    height=max(320, len(chart_df) * 38),
    hoverlabel=dict(bgcolor="white", font_size=13),
)

# Annotation: "Top 3" label on the legend proxy
fig.add_annotation(
    x=0.99, y=0.01, xref="paper", yref="paper",
    text="🟢 Top 3   🟣 Others",
    showarrow=False,
    font=dict(size=11, color="#374151"),
    align="right",
)

st.plotly_chart(fig, use_container_width=True)

# ── Radar chart for top 3 ─────────────────────────────────────────────────────

st.subheader("Top 3 — Head-to-Head Comparison")
st.caption(
    "Each axis shows the fund's percentile rank within the category for that metric. "
    "Outer edge = 100th percentile (best in category)."
)

top3 = category_df[category_df["category_rank"] <= 3].copy()
radar_metrics = ["sharpe_pct", "alpha_pct", "consistency_pct"]
radar_labels = ["Sharpe", "Alpha", "Consistency"]

radar_fig = go.Figure()
colors_radar = ["#10B981", "#6366F1", "#F59E0B"]

for i, (_, row) in enumerate(top3.iterrows()):
    values = [row[m] for m in radar_metrics]
    values.append(values[0])  # close the polygon
    radar_fig.add_trace(go.Scatterpolar(
        r=values,
        theta=radar_labels + [radar_labels[0]],
        fill="toself",
        name=f"#{int(row['category_rank'])} {row['scheme_name'].replace('Equity Scheme - ','').replace(' Fund','')}",
        line_color=colors_radar[i],
        fillcolor=colors_radar[i],
        opacity=0.25 + i * 0.05,
    ))

radar_fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 1],
            tickformat=".0%",
            tickfont_size=9,
            gridcolor="#E2E8F0",
        ),
        angularaxis=dict(tickfont_size=13),
        bgcolor="white",
    ),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    paper_bgcolor="white",
    margin=dict(l=40, r=40, t=20, b=60),
    height=400,
)

st.plotly_chart(radar_fig, use_container_width=True)
