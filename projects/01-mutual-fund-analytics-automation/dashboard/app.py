"""
Streamlit dashboard for Project 1 - Mutual Fund Analytics Automation.

Run with: streamlit run dashboard/app.py  (from the project root)

Lets you explore the Stage 1 eligible funds per category and adjust the
Stage 2 composite-score weights (Sharpe / Jensen's Alpha / Consistency)
live - the table and chart recompute instantly using the same scoring
logic as src/scoring.py.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make src/ importable so the dashboard reuses the real scoring logic
# instead of duplicating it.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scoring import apply_eligibility_filter, compute_composite_score  # noqa: E402

st.set_page_config(page_title="Mutual Fund Rankings", layout="wide")


@st.cache_data
def load_eligible_funds() -> pd.DataFrame:
    schemes = pd.read_csv(PROJECT_ROOT / "data/processed/schemes.csv")
    metrics = pd.read_csv(PROJECT_ROOT / "data/processed/metrics.csv")
    metrics = metrics.drop(columns=["scheme_name", "category"])
    df = schemes.merge(metrics, on="scheme_code")
    return apply_eligibility_filter(df)


eligible = load_eligible_funds()

st.title("Mutual Fund Analytics — Ranked Picks")
st.caption(
    f"{len(eligible)} funds passed Stage 1 eligibility "
    f"(AUM ≥ ₹1,000cr and 5yr+ track record) across "
    f"{eligible['category'].nunique()} categories."
)

# --- Sidebar: composite score weights ---
st.sidebar.header("Stage 2: Composite Score Weights")
st.sidebar.write("Adjust how much each metric counts toward the ranking.")

sharpe_w = st.sidebar.slider("Sharpe Ratio", 0.0, 1.0, 1 / 3, step=0.05)
alpha_w = st.sidebar.slider("Jensen's Alpha", 0.0, 1.0, 1 / 3, step=0.05)
consistency_w = st.sidebar.slider("Consistency", 0.0, 1.0, 1 / 3, step=0.05)

total_w = sharpe_w + alpha_w + consistency_w
if total_w == 0:
    st.sidebar.error("At least one weight must be greater than 0.")
    st.stop()

weights = {
    "sharpe": sharpe_w / total_w,
    "alpha": alpha_w / total_w,
    "consistency": consistency_w / total_w,
}
st.sidebar.caption(
    f"Normalized: Sharpe {weights['sharpe']:.0%} · "
    f"Alpha {weights['alpha']:.0%} · "
    f"Consistency {weights['consistency']:.0%}"
)

scored = compute_composite_score(eligible, weights)

# --- Sidebar: category picker ---
categories = sorted(scored["category"].unique())
category = st.sidebar.selectbox(
    "Category", categories, format_func=lambda c: c.replace("Equity Scheme - ", "")
)

category_df = scored[scored["category"] == category].sort_values("category_rank")

st.subheader(f"{category.replace('Equity Scheme - ', '')} — {len(category_df)} eligible funds")

display_cols = {
    "category_rank": "Rank",
    "scheme_name": "Fund",
    "amc": "AMC",
    "total_aum_cr": "AUM (Cr)",
    "return_5y": "5Y Return",
    "beta": "Beta",
    "sharpe": "Sharpe",
    "alpha": "Alpha",
    "consistency": "Consistency",
    "composite_score": "Score",
}
table = category_df[list(display_cols.keys())].rename(columns=display_cols)


def highlight_top3(row):
    color = "background-color: #D1FAE5" if row["Rank"] <= 3 else ""
    return [color] * len(row)


styled = table.style.format({
    "AUM (Cr)": "{:,.0f}",
    "5Y Return": "{:.1%}",
    "Beta": "{:.2f}",
    "Sharpe": "{:.2f}",
    "Alpha": "{:.1%}",
    "Consistency": "{:.1%}",
    "Score": "{:.1%}",
}).apply(highlight_top3, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.subheader("Composite Score by Fund")
chart_data = category_df.set_index("scheme_name")["composite_score"].sort_values(ascending=False)
st.bar_chart(chart_data)
