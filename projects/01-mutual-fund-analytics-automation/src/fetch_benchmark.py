"""
Fetches historical NIFTY 50 prices - our market benchmark for Beta and
Jensen's Alpha. Cached the same way as fund NAV history, so metrics.py
can run repeatedly without re-downloading.

Output: data/raw/nifty50.csv (Date, Close)
"""

import yfinance as yf

OUTPUT_PATH = "data/raw/nifty50.csv"
START_DATE = "2005-01-01"


def main():
    # yfinance returns a DataFrame with a MultiIndex column (Price, Ticker)
    # even for a single ticker - we only need the daily closing price.
    data = yf.download("^NSEI", start=START_DATE, progress=False)
    closes = data["Close"]["^NSEI"]
    closes.name = "nifty_close"

    closes.to_csv(OUTPUT_PATH)
    print(f"Saved {len(closes)} days of NIFTY 50 data to {OUTPUT_PATH}")
    print(f"Date range: {closes.index.min().date()} to {closes.index.max().date()}")


if __name__ == "__main__":
    main()
