# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo Purpose

Finance + GenAI portfolio for Veer Pratap Singh. Each subfolder under `projects/` is an independent, deployable project with its own `src/`, `dashboard/`, `requirements.txt`, and `README.md`.

## Running Projects

All commands run from the **project subdirectory**, not the repo root.

### Project 1 — Mutual Fund Analytics Automation
```bash
cd projects/01-mutual-fund-analytics-automation

# Run the full pipeline (fetch → metrics → score → Excel report)
python src/main.py

# Run the dashboard
streamlit run dashboard/app.py
```
Pipeline steps are skipped automatically if their output files already exist. Delete `data/raw/` or `data/processed/` files to force a re-fetch.

### Project 2 — AI Asset Allocator
```bash
cd projects/02-ai-financial-profile-asset-allocation

# Run the dashboard
streamlit run dashboard/app.py
```
Requires `GROQ_API_KEY` in `.env` (local) or Streamlit secrets (deployed). Works in demo mode without a key.

## Architecture

### Project 1 pipeline flow
```
fetch_raw_data → fetch_schemes → fetch_benchmark
                                      ↓
fetch_nav_history → metrics → scoring → report → output/fund_rankings.xlsx
```
`main.py` orchestrates all steps in order with skip-if-cached logic. The dashboard (`dashboard/app.py`) bypasses the pipeline entirely — it imports `scoring.py` directly and recomputes scores live from `data/processed/scored_funds.csv` as the user adjusts weights.

### Project 2 module roles
- `risk_profiler.py` — questionnaire scoring (0–100 risk score) and base allocation weights per risk label
- `prompts.py` — Groq system prompt and user message builder
- `allocation_engine.py` — Groq API call with structured JSON output (`response_format={"type": "json_object"}`); falls back to `_demo_allocation()` when no key is present
- `fund_recommender.py` — reads Project 1's `scored_funds.csv` to surface top-ranked equity funds; gracefully degrades if the file doesn't exist
- `dashboard/app.py` — full Streamlit wizard; `resolve_api_key()` checks `st.secrets` first then `.env`

### Cross-project dependency
Project 2's `fund_recommender.py` reads from Project 1's output at a relative path:
```
../01-mutual-fund-analytics-automation/data/processed/scored_funds.csv
```
If Project 1 has never been run, fund recommendations are skipped silently.

## Design Conventions
- Both dashboards share the same dark CSS design system: `#0A0A0E` background, `#818CF8` accent, Space Grotesk headings, Inter body, Bootstrap Icons via CDN.
- All `sys.path` manipulation is done at the top of `dashboard/app.py` to keep `src/` importable without installing as a package.
- Data files in `data/raw/` and `data/processed/` are gitignored (large/auto-generated). `output/` is also gitignored.

## Deployment
Both projects are deployed on Streamlit Community Cloud pointing to this GitHub repo:
- Project 1 main file: `projects/01-mutual-fund-analytics-automation/dashboard/app.py`
- Project 2 main file: `projects/02-ai-financial-profile-asset-allocation/dashboard/app.py`

Each project's `requirements.txt` is picked up automatically by Streamlit Cloud (it walks up from the main file's directory).
