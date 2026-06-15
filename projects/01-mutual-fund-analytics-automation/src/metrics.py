"""
Step 3 of the pipeline (part 1): compute per-fund return/risk metrics.

Input:  data/raw/nav_history/{scheme_code}.json (from fetch_nav_history.py)
        data/raw/nifty50.csv (from fetch_benchmark.py)
Output: data/processed/metrics.csv

Metrics computed:
  - return_1y / return_3y / return_5y / return_10y: CAGR over the trailing
    N years (None if the fund doesn't have that much history yet).
  - beta, sharpe, alpha: computed over the trailing LOOKBACK_YEARS of daily
    returns (separate from the CAGR figures above, which are point-in-time
    snapshots used mainly for the eligibility filter / display).

Risk-free rate: 7% (proxy for the India 10Y G-Sec yield), held as a constant.
"""

import json

import pandas as pd

RISK_FREE_RATE = 0.07
TRADING_DAYS_PER_YEAR = 252
LOOKBACK_YEARS = 3  # window for Beta / Sharpe / Alpha


def load_nav_series(scheme_code: int) -> pd.Series:
    """Load a fund's cached NAV history into a Series indexed by date, oldest first."""
    with open(f"data/raw/nav_history/{scheme_code}.json") as f:
        data = json.load(f)

    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = df["nav"].astype(float)
    df = df.sort_values("date").set_index("date")
    return df["nav"]


def load_nifty_returns() -> pd.Series:
    """Load NIFTY 50 daily returns, indexed by date."""
    nifty = pd.read_csv("data/raw/nifty50.csv", parse_dates=["Date"], index_col="Date")
    return nifty["nifty_close"].pct_change().dropna()


def cagr(nav: pd.Series, years: float) -> float | None:
    """Compound annual growth rate over the trailing `years`, or None if the
    fund's history doesn't go back that far."""
    end_date = nav.index.max()
    start_date = end_date - pd.DateOffset(years=years)

    if nav.index.min() > start_date:
        return None

    start_nav = nav.loc[:start_date].iloc[-1]
    end_nav = nav.iloc[-1]
    return (end_nav / start_nav) ** (1 / years) - 1


def compute_fund_metrics(scheme_code: int, nifty_returns: pd.Series) -> dict:
    nav = load_nav_series(scheme_code)
    daily_returns = nav.pct_change().dropna()

    metrics = {
        "return_1y": cagr(nav, 1),
        "return_3y": cagr(nav, 3),
        "return_5y": cagr(nav, 5),
        "return_10y": cagr(nav, 10),
    }

    # Restrict to the trailing LOOKBACK_YEARS for Beta / Sharpe / Alpha
    cutoff = daily_returns.index.max() - pd.DateOffset(years=LOOKBACK_YEARS)
    recent_fund_returns = daily_returns.loc[daily_returns.index > cutoff]

    # Align fund and market returns on shared dates - pandas matches rows by
    # index (date) here, and dropna() removes any date where either series
    # is missing a value.
    aligned = pd.DataFrame({"fund": recent_fund_returns, "market": nifty_returns}).dropna()

    if len(aligned) < 100:
        metrics.update({"beta": None, "sharpe": None, "alpha": None})
        return metrics

    beta = aligned["fund"].cov(aligned["market"]) / aligned["market"].var()

    fund_annual_return = aligned["fund"].mean() * TRADING_DAYS_PER_YEAR
    fund_annual_vol = aligned["fund"].std() * (TRADING_DAYS_PER_YEAR ** 0.5)
    sharpe = (fund_annual_return - RISK_FREE_RATE) / fund_annual_vol

    market_annual_return = aligned["market"].mean() * TRADING_DAYS_PER_YEAR
    expected_return = RISK_FREE_RATE + beta * (market_annual_return - RISK_FREE_RATE)
    alpha = fund_annual_return - expected_return

    metrics.update({"beta": beta, "sharpe": sharpe, "alpha": alpha})
    return metrics


def compute_consistency_table(schemes: pd.DataFrame) -> pd.Series:
    """
    For each fund, find the % of trailing-3-year windows (sampled monthly)
    where its 3-year return beat its category's average 3-year return in
    that same window.

    Returns a Series of consistency scores (0-1) indexed by scheme_code.
    Funds with less than 3 years of history get no rows at all (NaN after
    merging back in main()).
    """
    rows = []
    for row in schemes.itertuples():
        nav = load_nav_series(row.scheme_code)
        monthly_nav = nav.resample("ME").last()

        # 3-year CAGR ending at each month-end, using the NAV from 36 months
        # earlier. shift(36) lines up "now" with "36 months ago" so we can
        # divide them directly.
        rolling_3y = (monthly_nav / monthly_nav.shift(36)) ** (1 / 3) - 1
        rolling_3y = rolling_3y.dropna()

        for date, value in rolling_3y.items():
            rows.append({
                "scheme_code": row.scheme_code,
                "category": row.category,
                "date": date,
                "rolling_3y_return": value,
            })

    long_df = pd.DataFrame(rows)

    # For every (date, category) group, compute the average return and
    # broadcast it back onto every row in that group - transform() keeps
    # the original row count, unlike agg()/mean() which collapses to one
    # row per group.
    long_df["category_avg"] = long_df.groupby(["date", "category"])["rolling_3y_return"].transform("mean")
    long_df["beat_category"] = long_df["rolling_3y_return"] > long_df["category_avg"]

    consistency = long_df.groupby("scheme_code")["beat_category"].mean()
    consistency.name = "consistency"
    return consistency


def main():
    schemes = pd.read_csv("data/processed/schemes.csv")
    nifty_returns = load_nifty_returns()

    records = []
    for row in schemes.itertuples():
        m = compute_fund_metrics(row.scheme_code, nifty_returns)
        m["scheme_code"] = row.scheme_code
        m["scheme_name"] = row.scheme_name
        m["category"] = row.category
        records.append(m)

    result = pd.DataFrame(records)

    consistency = compute_consistency_table(schemes)
    result = result.merge(consistency, left_on="scheme_code", right_index=True, how="left")

    result.to_csv("data/processed/metrics.csv", index=False)
    print(f"Saved metrics for {len(result)} funds to data/processed/metrics.csv")
    print(f"\nFunds missing 10Y return: {result['return_10y'].isna().sum()}")
    print(f"Funds missing 5Y return: {result['return_5y'].isna().sum()}")
    print(f"Funds with no Beta/Sharpe/Alpha: {result['beta'].isna().sum()}")
    print(f"Funds with no Consistency score: {result['consistency'].isna().sum()}")


if __name__ == "__main__":
    main()
