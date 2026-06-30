# Interview Prep — Veer Pratap Singh Portfolio Projects

Quick-reference for interviews. Each section covers: what it does, key decisions, tradeoffs made, and likely interview questions with answers.

---

## Project 1 — Mutual Fund Analytics Automation

**One-line pitch:**
Python pipeline that screens 2,000+ Indian equity mutual funds using CAPM-based metrics (Sharpe, Jensen's Alpha, Consistency), ranks them by category, and serves the results through a live Streamlit dashboard with user-configurable weights.

**Live:** https://mutual-fund-analytics-nrcwcuthktrxzca5golsnn.streamlit.app

---

### The Core Design Decision — Why NOT raw returns?

Most fund ranking tools use 1Y/3Y/5Y raw returns. Two problems:
- **Double-counting**: Sharpe Ratio already measures return per unit of risk. Adding raw returns alongside Sharpe counts the same thing twice.
- **Snapshot bias**: A fund that did well in one 3-year window looks identical to a fund that consistently beat peers across *every* rolling 3-year window.

The fix: three *independent* dimensions — Sharpe (risk-adjusted return), Jensen's Alpha (manager skill beyond market exposure), and Consistency (% of rolling windows beating category average).

---

### Two-Stage Architecture

**Stage 1 — Eligibility filter (pass/fail, not scored):**
- AUM ≥ ₹1,000 Cr → liquidity and institutional confidence signal
- 5-year track record → enough NAV history for meaningful rolling windows
- Result: 93 of 184 funds pass

**Stage 2 — Composite score:**
Each metric is percentile-ranked *within category* (Morningstar-style), then combined via user-configurable weights. Percentile ranking makes scores comparable across categories and robust to outliers — a fund with an unusually high Sharpe doesn't distort everyone else's score.

---

### Key Metrics Explained

| Metric | Formula | What it measures |
|---|---|---|
| Sharpe Ratio | (Portfolio Return − Risk-free) / Std Dev | Return per unit of total risk |
| Jensen's Alpha | Actual Return − [Rf + β × (Rm − Rf)] | Manager skill beyond what market exposure explains |
| Consistency | % of rolling 3Y windows where fund > category avg | Track record stability, not just peak performance |

**Risk-free rate used:** 7% (India 10Y G-Sec proxy)
**Benchmark:** NIFTY 50 (^NSEI via yfinance)
**Lookback window:** Trailing 3 years of daily NAV returns

---

### Data Pipeline

```
AMFI/GitHub → fetch_raw_data → fetch_schemes (184 funds, 10 categories)
yfinance    → fetch_benchmark (NIFTY 50 daily)
mfapi.in    → fetch_nav_history (daily NAV per scheme, cached locally)
                    ↓
               metrics.py → scoring.py → report.xlsx + dashboard
```

All fetch steps are skip-if-cached — NAV history takes ~30 mins first run, then instant.

---

### Likely Interview Questions

**Q: Why Sharpe and not Sortino?**
Sharpe penalises both upside and downside volatility equally. For a retail investor screener, this is a reasonable simplification — Sortino requires specifying a target return, which adds subjectivity. Can be added as a configuration parameter.

**Q: Why percentile rank instead of raw scores?**
Raw metrics have different scales and distributions. Percentile rank normalises everything to 0–1 within category, making weights interpretable: "50% Sharpe" means exactly 50% of the score comes from risk-adjusted return.

**Q: Why AUM ≥ ₹1,000 Cr as the filter?**
Below ₹1,000 Cr, funds have lower liquidity, are more vulnerable to redemption pressure, and are more likely to be closed or restructured. This is the standard institutional threshold.

**Q: How does this differ from Screener.in or Morningstar?**
Those tools rank by raw returns. This tool ranks by three independent risk-adjusted dimensions with user-configurable weights, so an investor focused on capital preservation can weight Consistency higher.

---

## Project 2 — AI-Powered Financial Profile & Asset Allocation Tool

**One-line pitch:**
A 6-question wizard that scores a user's risk profile (0–100), sends it to Groq's Llama 3.3 LLM with a structured prompt, and returns a personalised asset allocation across Equity/Debt/Gold/Alternatives — with full reasoning for each decision.

**Live:** https://mutual-fund-analytics-fyzzfwjnnmo9nmkcnxae3e.streamlit.app

---

### The Key LLM Pattern — Structured Output

The most important engineering decision: don't use the LLM as a text generator. Use it as a **structured reasoning engine**.

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[system_prompt, user_message],
    response_format={"type": "json_object"},  # forces valid JSON
    temperature=0.3,                           # low temp = consistent output
)
allocation = json.loads(response.choices[0].message.content)
```

The LLM returns a fixed schema: allocation percentages + per-asset reasoning + SIP suggestion + key considerations. This is production LLM pattern — predictable, parseable, testable.

---

### Risk Scoring System

5 questions, each weighted differently:

| Question | Max weight | Rationale |
|---|---|---|
| Investment horizon | 30 | Time is the biggest risk determinant |
| Age | 25 | Younger = more recovery time |
| Goal | 20 | Capital preservation vs wealth creation |
| Reaction to 20% drop | 15 | Behavioural/emotional risk |
| Existing debt | 10 | Reduces real investable surplus |

Weighted sum → 0–100 score → mapped to Conservative / Moderate Conservative / Moderate Aggressive / Aggressive.

---

### Graceful Degradation (Demo Mode)

The app works without an API key — shows a hardcoded allocation with a "Demo mode" banner. This is critical for a portfolio tool: visitors see a live, functional product even without a Groq key.

API key resolution order:
1. `st.secrets["GROQ_API_KEY"]` — Streamlit Cloud deployment
2. `.env` file — local development
3. User-entered key via sidebar input
4. Demo mode fallback

---

### Cross-Project Dependency

Project 2 reads Project 1's output (`scored_funds.csv`) to surface top-ranked equity funds for the user's specific risk profile and goal. If Project 1 hasn't been run, fund recommendations are skipped silently — graceful degradation.

---

### Likely Interview Questions

**Q: Why Groq instead of OpenAI?**
Free tier, fast inference (Llama 3.3 70B in ~1–2 seconds). For a portfolio demo tool, cost matters — OpenAI would charge per call. Groq's API is OpenAI-compatible so switching is a one-line change.

**Q: What if the LLM returns wrong percentages (not summing to 100)?**
The code validates and corrects: if the allocation sums to anything other than 100, the difference is added/subtracted from the debt allocation. Debt is chosen because it's the most flexible asset class.

**Q: Why low temperature (0.3)?**
Financial recommendations should be consistent, not creative. Temperature 0 would be too rigid (same output every time), 0.3 gives slight variation while keeping the allocation sensible.

**Q: How does this demonstrate GenAI skills for the AmEx role?**
It shows the full production LLM pattern: prompt engineering → structured output → validation → fallback → deployment. Not a chatbot — a tool where AI is one component in a larger system.

---

## General Interview Points Across All Projects

**On choosing Python:**
Finance + data = pandas. Python is the standard for financial data work — same tools used in quant funds, asset managers, fintech. Not a choice made for portfolio — it's the professional standard.

**On Streamlit:**
Fastest path from Python script to shareable tool. No frontend knowledge needed. Appropriate for internal analyst tools and portfolio demos — not for consumer-facing products (would use React/Next.js for that).

**On building real tools vs academic projects:**
Both projects use real data (AMFI, mfapi.in) and are deployed publicly. The decisions made (what to filter, how to score, which metrics to use) are the same decisions a working analyst would make — not textbook examples.

**On AI-assisted development:**
These projects were built using Claude Code. Worth being transparent about this in interviews — the financial methodology, design decisions, and domain logic are Veer's; Claude Code accelerated the implementation. This is increasingly standard in the industry.
