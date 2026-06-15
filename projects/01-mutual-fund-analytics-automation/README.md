# Mutual Fund Analytics Automation

Automates the mutual fund screening & ranking process Veer originally did manually during the Bajaj Capital internship (sourcing data from MoneyControl, filtering, and scoring funds by hand in Excel).

## Original Manual Process (`Redesigned_portfolio.xlsx` → "Scheme Recommendation" sheet)

- **Universe:** Equity mutual funds across 4 categories — Large Cap, Mid Cap, Small Cap, ELSS
- **Pre-filters (applied manually):** AUM > ₹10,000 Cr, MoneyControl star rating ≥ 4
- **Score:** `AUM × 3Y return × 5Y return × 10Y return` (Beta and Sharpe Ratio were captured but not actually used in the score)
- **Ranking:** `RANK.EQ` within each category — top-ranked fund = recommendation

## Automated, Improved Version (this project)

**Scope:** All diversified equity mutual fund schemes across **10 categories** — Large Cap, Large & Mid Cap, Mid Cap, Small Cap, Multi Cap, Flexi Cap, Value, Focused, Dividend Yield, and ELSS (184 active funds as of June 2026). Originally limited to the 4 categories in the manual template (Large/Mid/Small Cap, ELSS); expanded to cover all diversified equity categories that share NIFTY 50 as a benchmark. Sectoral/thematic, debt, hybrid, and index funds are excluded since they need different benchmarks or scoring logic — candidates for a future extension.

### Why not just "normalize everything and weight it"?

An earlier draft of this design proposed normalizing AUM, 1Y/3Y/5Y/10Y returns, Beta, and Sharpe Ratio to 0-100 and combining them all with configurable weights. On review, this has real problems:
- **Double-counting**: Sharpe Ratio is *already* `(return − risk-free) / volatility`. Weighting raw returns, Beta, *and* Sharpe separately counts the same return/risk relationship multiple times.
- **Min-max normalization is fragile**: one outlier fund skews the 0-100 scale for everyone else in its category.
- **Mixes "eligibility" with "quality"**: AUM and track-record length aren't things where "more is always better on a sliding scale" — they're gates ("is this fund viable to recommend?"), not performance signals.

### Final Design: Two-Stage (Filter → Score)

**Stage 1 — Eligibility filters (pass/fail, not scored):**
- AUM ≥ threshold (liquidity/stability gate)
- Fund track record ≥ 5 years (so 5Y return is meaningful)

**Stage 2 — Composite score from three independent dimensions, each as a percentile rank within category:**
1. **Sharpe Ratio** — total risk-adjusted return
2. **Jensen's Alpha** (CAPM-based: `Actual Return − [Risk-free + Beta × (Market Return − Risk-free)]`) — measures manager skill beyond what the fund's market risk exposure (Beta) would predict
3. **Consistency** — % of rolling 3-year periods the fund beat its category average (vs. a single static snapshot)

Percentile-rank normalization (Morningstar-style: "beats X% of peers on this metric") is robust to outliers and easy to explain. **User-configurable weights** apply across these three dimensions — this is where the original "give weight based on preference" idea actually lands well, since the three inputs are largely independent.

Rank within each category; output top N per category plus full ranked list.

## Data Sources
- **Scheme list & categories:** AMFI `NAVAll.txt`
- **Historical NAV (for returns/Beta/Sharpe):** `mfapi.in` (free, mirrors AMFI data)
- **Benchmark (NIFTY 50, for Beta):** `yfinance` (`^NSEI`)
- **AUM:** TBD — researching a scheme-wise source (AMFI average AUM reports)

## Pipeline
```
src/
  fetch_schemes.py     # scheme list + category classification (184 funds, 10 categories)
  fetch_nav_history.py # historical NAV per scheme, cached to data/raw/nav_history/
  fetch_benchmark.py   # NIFTY 50 history, cached to data/raw/nifty50.csv
  metrics.py            # returns (CAGR), Beta, Sharpe, Jensen's Alpha, Consistency
  scoring.py            # eligibility filter + weighted composite score + ranking
  report.py             # multi-sheet Excel output (TODO)
  main.py               # pipeline entrypoint (TODO)
```

## Assumptions
- **Risk-free rate**: 7% (proxy for India 10Y G-Sec yield), used for Sharpe/Alpha.
- **Beta/Sharpe/Alpha window**: trailing 3 years of daily returns vs NIFTY 50.
- **Eligibility (Stage 1)**: AUM >= ₹1,000cr (liquidity/stability gate - the original ₹10,000cr would have zeroed out smaller categories like Dividend Yield) and 5-year+ track record.

## Results (current)
93 of 184 funds pass eligibility. Every category retains at least 3 eligible funds (Multi Cap is the tightest at 4, due to SEBI's 2020 category redefinition creating mostly newer funds in that category). See `data/processed/scored_funds.csv` for the full ranked list.

## Status
In progress — see [PROJECTS.md](C:\Users\VEER\.claude\PROJECTS.md) for overall tracker.
