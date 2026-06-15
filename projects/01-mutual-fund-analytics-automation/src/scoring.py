"""
Step 4 of the pipeline: filter funds by eligibility, then score and rank
the rest.

Input:  data/processed/schemes.csv, data/processed/metrics.csv
Output: data/processed/scored_funds.csv

Stage 1 - Eligibility (pass/fail, not scored):
  - Total AUM >= AUM_THRESHOLD_CR (liquidity/stability gate - confirmed at
    1,000cr after checking the original 10,000cr threshold would zero out
    smaller categories like Dividend Yield)
  - 5-year track record (return_5y is not null)

Stage 2 - Composite score (eligible funds only):
  Each of Sharpe, Jensen's Alpha, and Consistency is converted to a
  percentile rank WITHIN its category (0-1, "beats X% of category peers"),
  then combined using WEIGHTS below. Funds are ranked within category by
  this composite score.
"""

import pandas as pd

AUM_THRESHOLD_CR = 1000

# Must sum to 1. Adjust to reflect what matters most.
WEIGHTS = {
    "sharpe": 1 / 3,
    "alpha": 1 / 3,
    "consistency": 1 / 3,
}


def apply_eligibility_filter(df: pd.DataFrame) -> pd.DataFrame:
    big_enough = df["total_aum_cr"] >= AUM_THRESHOLD_CR
    has_track_record = df["return_5y"].notna()
    return df[big_enough & has_track_record].copy()


def compute_composite_score(df: pd.DataFrame, weights: dict = WEIGHTS) -> pd.DataFrame:
    df = df.copy()

    # Percentile rank within category: 1.0 = best in category, 0.0 = worst.
    for metric in weights:
        df[f"{metric}_pct"] = df.groupby("category")[metric].rank(pct=True)

    df["composite_score"] = sum(weights[m] * df[f"{m}_pct"] for m in weights)

    # Rank 1 = highest composite score within its category.
    df["category_rank"] = (
        df.groupby("category")["composite_score"].rank(ascending=False, method="min").astype(int)
    )
    return df


def main():
    schemes = pd.read_csv("data/processed/schemes.csv")
    metrics = pd.read_csv("data/processed/metrics.csv")

    # metrics.csv also has scheme_name/category - drop the duplicates before merging.
    metrics = metrics.drop(columns=["scheme_name", "category"])
    df = schemes.merge(metrics, on="scheme_code")

    eligible = apply_eligibility_filter(df)
    scored = compute_composite_score(eligible)
    scored = scored.sort_values(["category", "category_rank"])

    scored.to_csv("data/processed/scored_funds.csv", index=False)

    print(f"Eligible funds: {len(scored)} / {len(df)}")
    print("\nEligible funds per category:")
    print(scored.groupby("category").size())

    print("\n=== Top 3 per category ===")
    for cat, group in scored.groupby("category"):
        print(f"\n{cat} ({len(group)} eligible):")
        top3 = group[group["category_rank"] <= 3]
        print(top3[["category_rank", "scheme_name", "composite_score", "sharpe", "alpha", "consistency"]]
              .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
