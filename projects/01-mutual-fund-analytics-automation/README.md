# Mutual Fund Analytics Automation

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Streamlit-FF4B4B?logo=streamlit)](https://mutual-fund-analytics-nrcwcuthktrxzca5golsnn.streamlit.app/)

Automates the manual process of screening and ranking Indian equity mutual funds — a task typically done by hand across multiple sources. Replaces ad-hoc Excel scoring with a reproducible Python pipeline and an interactive dashboard.

## The Problem with Standard Fund Rankings

Most fund comparison tools rank by raw 1Y / 3Y / 5Y returns. This has two issues:
- **Double-counting:** Sharpe Ratio already captures return relative to risk. Adding raw returns on top counts the same thing twice.
- **Snapshot bias:** A fund that did well in one 3-year window looks identical to one that consistently beat peers across every rolling window.

## Design: Two-Stage (Filter → Score)

**Stage 1 — Eligibility (pass/fail, not scored):**
- AUM ≥ ₹1,000 Cr — liquidity and stability gate
- 5-year track record — enough history for meaningful risk metrics

93 of 184 funds pass.

**Stage 2 — Composite score from three independent dimensions, each as a percentile rank within category:**
1. **Sharpe Ratio** — return per unit of volatility
2. **Jensen's Alpha** (`Actual Return − [Risk-free + Beta × (Market Return − Risk-free)]`) — manager skill beyond market exposure
3. **Consistency** — % of rolling 3-year windows where the fund beat its category average

Percentile-rank normalisation (Morningstar-style) is robust to outliers. Weights across the three dimensions are user-configurable.

## Dashboard

**[Open Live Dashboard](https://mutual-fund-analytics-nrcwcuthktrxzca5golsnn.streamlit.app/)**

- Pick a fund category and investor style preset (Balanced / Safety First / Return Seeker / Risk-Adjusted)
- Rankings recompute live as you adjust weights
- Top-pick banner, ranked table with top-3 highlighted, bar chart, and radar chart for head-to-head top-3 comparison

## Data Sources
- **Scheme list, categories & AUM:** [InertExpert2911/Mutual_Fund_Data](https://github.com/InertExpert2911/Mutual_Fund_Data) (AMFI-derived)
- **Historical NAV:** `mfapi.in` (free AMFI mirror, daily NAV per scheme)
- **Benchmark (NIFTY 50):** `yfinance` (`^NSEI`)

## Pipeline

```
src/
  fetch_raw_data.py    # downloads scheme/AUM data from GitHub
  fetch_schemes.py     # builds scheme universe (184 funds, 10 categories)
  fetch_nav_history.py # fetches full NAV history per scheme, cached locally
  fetch_benchmark.py   # downloads NIFTY 50 history via yfinance
  metrics.py           # computes CAGR, Beta, Sharpe, Jensen's Alpha, Consistency
  scoring.py           # eligibility filter + composite score + category ranking
  report.py            # writes output/fund_rankings.xlsx (multi-sheet, formatted)
  main.py              # pipeline entrypoint — runs all steps in order
```

Run everything with one command (from the project root):
```
python src/main.py
```
Fetch steps are skipped automatically if cached data already exists.

## Run the Dashboard Locally

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Assumptions
- **Risk-free rate:** 7% (India 10Y G-Sec proxy) for Sharpe and Alpha
- **Lookback window:** Trailing 3 years of daily returns vs NIFTY 50 for Beta / Sharpe / Alpha
- **Eligibility:** AUM ≥ ₹1,000 Cr and 5-year track record

## Results
93 of 184 funds pass eligibility across 10 categories. Every category has at least 3 eligible funds. Multi Cap is the tightest (4 eligible) — most funds in that category were restructured after SEBI's 2020 category redefinition, resetting their track records.

---

*Methodology, financial parameters, and domain logic designed by Veer Pratap Singh. Built with Python and Claude Code (AI-assisted development).*
