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

## Project 3 — Financial Statement Extractor

**One-line pitch:**
Upload 1–5 annual report PDFs → automatically finds P&L, Balance Sheet, and Cash Flow statement pages → extracts tables using Python (no LLM) → outputs a formatted 4-sheet Excel with pre-calculated ratios, ready for DCF or peer analysis.

*(Infosys AR 2025 tested and verified)*

---

### The Key Decision — Why No LLM Here?

Explicitly chose NOT to use an LLM for extraction, for two reasons:

1. **Accuracy**: LLMs can hallucinate numbers. For financial analysis, a wrong Revenue or Total Assets figure corrupts every downstream calculation. The PDF text is the source of truth — we read it directly.
2. **Transparency**: Every extraction step is traceable. If a number is wrong, you can find exactly which line of the PDF it came from and which synonym map caused the mismatch.

This is the mature engineering decision: knowing *when not to use AI* is as important as knowing when to use it.

---

### Technical Architecture

```
PDF bytes
    ↓
find_statement_pages()    — keyword scoring to locate P&L/BS/CF pages
    ↓
extract_tables_from_pages() — pdfplumber extract_tables()
                              → if duplication artifacts detected, fall back to
                              → _text_to_table() (regex line parser)
    ↓
identify_statement_table()  — scores + merges all qualifying tables
                              (handles multi-page statements)
    ↓
normalize_table()           — synonym map matching → standard line items
    ↓
stitch_years()              — combines data across multiple PDFs
    ↓
build_excel()               — 4-sheet openpyxl output (P&L, BS, CF, Ratios)
```

---

### Real Problems Solved During Build

**Problem 1 — Wrong pages found initially**
Annual reports mention "Profit and Loss" in MD&A sections, overview pages, and notes — not just the actual statement. Fixed by requiring the keyword to appear in the first 10 lines of the page (as a heading), not buried in body text.

**Problem 2 — PDF duplication artifacts**
Infosys AR 2025 (InDesign-generated PDF) had cell content duplicated: `"162,990 162,990 153,670"` instead of `"162,990 153,670"`. `extract_tables()` was giving corrupted data. Fixed by detecting duplication artifacts (>6% of cells have identical adjacent tokens) and falling back to `extract_text()` + regex parsing, which was clean.

**Problem 3 — Multi-page statements**
Financial statements span 2–3 pages. Original code picked the single "best" table and missed the rest. Fixed by merging all qualifying tables from all pages in order — assets (page 193) + liabilities (page 194) both captured.

**Problem 4 — Continuation pages**
CF statement best-match was page 283 "(contd.)" — missing the operating activities section which started on page 282. Fixed by checking if the best page contains "(contd.)" in its first 200 characters; if so, also include the previous page.

**Problem 5 — 157-second page scan (the big one)**
Scanning the full 369-page PDF with pdfplumber's `extract_text()` to locate the three statement pages took 157 seconds — the Streamlit app appeared to hang. Profiling showed pdfplumber's layout analysis (character-level positioning, used for accurate table extraction) is overkill for a scan that only needs heading keywords and number counts. Switched to PyMuPDF (`fitz`) for this scan — same task in ~3 seconds, a ~50x speedup — while keeping pdfplumber for the actual table extraction on the small number of pages identified (where its table-structure accuracy matters). Added a second optimization: a cheap unsorted text pass filters 369 pages down to ~70 "candidate" pages (containing any statement keyword), and only those get the more expensive `sort=True` extraction needed for reliable heading detection. Final scan time: ~9 seconds. This is a "right tool for each sub-task" decision — fast+rough for the wide scan, slow+accurate for the narrow extraction.

---

### The Synonym Map — Domain Knowledge as Code

`schema.py` contains ~100 keyword synonyms mapping company-specific labels to a standard schema:

```python
"Operating Cash Flow": [
    "net cash generated from operating",   # Infosys phrasing
    "net cash from operating",              # Generic
    "net cash provided by operating",       # US GAAP phrasing
    ...
]
```

This is essentially encoding financial accounting knowledge into the system — the same concept that an analyst builds up over years. Every new company tested adds new synonyms.

---

### Ratios Calculated Automatically

| Ratio | Formula |
|---|---|
| Gross / Operating / Net Margin | Profit ÷ Revenue |
| ROE | Net Profit ÷ Total Equity |
| ROA | Net Profit ÷ Total Assets |
| Current Ratio | Current Assets ÷ Current Liabilities |
| D/E Ratio | Total Liabilities ÷ Total Equity |
| Interest Coverage | EBIT ÷ Interest Expense |

All division-by-zero cases handled → shows "—" rather than crashing.

---

### Likely Interview Questions

**Q: Why not use an LLM / ChatGPT to extract the numbers?**
LLMs hallucinate. For a revenue figure, 98% accuracy is not acceptable — one wrong number in a DCF changes your valuation entirely. Rule-based extraction is 100% traceable: every value comes directly from the PDF text.

**Q: What's the limitation of this approach?**
Works for text-based PDFs only. Scanned/image PDFs need OCR (AWS Textract, Google Document AI). Also, accuracy varies with unusual PDF layouts — the synonym map needs to be extended for each new company format tested.

**Q: How would you make this production-ready?**
Three things: (1) Switch table extraction to AWS Textract or Google Document AI for near-100% accuracy on any PDF. (2) Add a user correction interface — show extracted values, let user fix errors. (3) Store corrected extractions as training data to improve the synonym map over time.

**Q: What does this project demonstrate?**
Systems thinking — breaking a complex problem (PDF → structured data) into discrete, testable steps. Domain knowledge encoding. Iterative debugging on real data. And the judgment to know when rule-based systems are better than AI.

**Q: Tell me about a performance problem you solved.**
The page-locating scan took 157 seconds on a 369-page annual report because I was using pdfplumber's `extract_text()` for every page — a method optimized for accurate character-level layout reconstruction, which is expensive and unnecessary when you just need to check for heading keywords. Switched to PyMuPDF for that scan (50x faster), then added a cheap pre-filter pass (plain substring search) to cut the number of pages needing the more expensive sorted-text extraction from 369 to ~70. Final time: ~9 seconds. The lesson: profile before optimizing, and match the tool's cost to what the task actually needs — don't use a precision instrument for a coarse filter.

**Q: What are known limitations of the current extraction?**
Four, in order of how often they bite: (1) When a company breaks a line item into sub-components with no parent total (e.g. TCS shows "Trade receivables" as a bare header with "Billed"/"Unbilled" as the children), only the first matching sub-item is captured — one line per category, not a sum. (2) "Tax" captures current tax only; deferred tax shows separately under "Other". (3) Unusual column layouts can split a label column from its values at a boundary the two-column model doesn't expect (Page Industries' Cash Flow page). (4) Scanned PDFs need OCR — out of scope for this portfolio version.

**Q: Does this work on annual reports from companies other than Infosys?**
Tested against 9 companies spanning 6 sectors and 2 market-cap tiers: Infosys and TCS (IT services), Maruti Suzuki (auto manufacturing), Asian Paints (FMCG/paints), Dr. Reddy's (pharma), Page Industries (apparel, mid-cap), and three banks — HDFC, ICICI, and Kotak Mahindra. Results:

| Company | Sector | P&L | Balance Sheet | Cash Flow |
|---|---|---|---|---|
| Infosys | IT services | ✓ | ✓ balances | ✓ reconciles |
| TCS | IT services | ✓ | ✓ balances | ✓ reconciles |
| Maruti Suzuki | Auto manufacturing | ✓ | ✓ balances | ✓ reconciles |
| Asian Paints | FMCG/paints | ✓ | ✓ balances | ✓ reconciles |
| Dr. Reddy's | Pharma | ✓ | ✓ balances | ✓ reconciles (~16 Cr forex gap) |
| HDFC Bank | Banking | ✓ | ✓ balances | ✓ reconciles |
| ICICI Bank | Banking | ✓ | ✓ balances | ~ (5/6 — one value/label split across lines) |
| Kotak Mahindra Bank | Banking | ✓ | ✓ balances | ✓ reconciles |
| Page Industries | Apparel, mid-cap | ✓ | ✓ balances | ✗ — wide-label layout splits label/value columns at an unexpected boundary |

8 of 9 fully reconcile end to end. Banks were the one category flagged up front as high-risk ("different schema entirely — Advances/Deposits, not Trade Receivables/Payables") — and they did need real new work, not a tweak: a parallel `BANK_*` schema for the Banking Regulation Act format, section-position tracking to disambiguate the bare "Total" label banks use for both subtotals, and several more pdfplumber-corruption and heading-false-positive fixes. All three banks tested now reconcile.

**The recurring lesson across this whole round: most bugs weren't wrong synonyms, they were "this looks like a heading but isn't," or "this looks like a table but the columns are scrambled."** Annual reports are full of sentences that incidentally contain statement names, and pdfplumber has more failure modes than expected:

*Heading false positives* — auditor's reports describing what they audited ("comprise the Standalone Balance Sheet as at..."), notes about "on-balance sheet exposures" (a banking-specific securitisation note), CEO/CFO compliance certificates declaring "we have reviewed... the cash flow statement", company-specific Notes-section names ("Schedules to the..." / "Schedules forming part of..." / "Explanatory notes to..." — three different euphemisms for the same thing across three companies), a combined section title naming two statements at once outscoring the real, simpler heading, and even a statement's own title rendered **letter-spaced** in the PDF's text layer ("S TA N D A L O N E B A L A N C E S H E E T") so it never matched a plain substring check at all.

*pdfplumber table corruption* — six distinct modes found across 9 companies: duplicated cell values (Infosys), an entire column merged into one cell (TCS), all labels merged into one cell with an empty value (TCS), a blank label column (HDFC), a schedule-reference NUMBER where the label should be (ICICI), and — most severe — only one cell surviving per row at all, no label and no second year (Kotak). Each needed its own detector and a shared fallback to text-based parsing.

Each fix added a targeted exclusion or detector rather than a blanket rule — none of this generalizes from first principles; it has to be discovered company by company, which is exactly why testing broadly before calling something "done" matters.

**Verified extraction results (Infosys AR 2025):**
| Metric | Extracted | Correct |
|---|---|---|
| Revenue | ₹1,62,990 Cr | ✓ |
| Net Profit | ₹26,750 Cr | ✓ |
| Total Assets | ₹1,24,936 Cr | ✓ |
| Total Equity | ₹87,332 Cr | ✓ |
| Current Assets | ₹77,168 Cr | ✓ |
| Current Liabilities | ₹31,762 Cr | ✓ |
| Operating CF | ₹35,694 Cr | ✓ |
| Investing CF | ₹-1,946 Cr | ✓ |
| Financing CF | ₹-24,161 Cr | ✓ |

---

## General Interview Points Across All Projects

**On choosing Python:**
Finance + data = pandas. Python is the standard for financial data work — same tools used in quant funds, asset managers, fintech. Not a choice made for portfolio — it's the professional standard.

**On Streamlit:**
Fastest path from Python script to shareable tool. No frontend knowledge needed. Appropriate for internal analyst tools and portfolio demos — not for consumer-facing products (would use React/Next.js for that).

**On building real tools vs academic projects:**
All three projects use real data (AMFI, mfapi.in, actual company PDFs) and are deployed publicly. The decisions made (what to filter, how to score, which metrics to use) are the same decisions a working analyst would make — not textbook examples.

**On AI-assisted development:**
These projects were built using Claude Code. Worth being transparent about this in interviews — the financial methodology, design decisions, and domain logic are Veer's; Claude Code accelerated the implementation. This is increasingly standard in the industry.
