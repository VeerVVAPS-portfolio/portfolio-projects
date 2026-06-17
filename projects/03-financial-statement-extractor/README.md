# Financial Statement Extractor

Extracts P&L, Balance Sheet, and Cash Flow statements from annual report PDFs and outputs a formatted, analysis-ready Excel file — no copy-pasting required.

## What It Does

1. Upload 1–5 annual report PDFs (one per financial year)
2. The tool automatically finds the financial statement pages
3. Tables are extracted using `pdfplumber` and normalized to a standard schema
4. A 4-sheet Excel is generated: P&L · Balance Sheet · Cash Flow · Ratios

## Ratios Calculated Automatically

| Ratio | Category |
|---|---|
| Gross Margin, Operating Margin, Net Margin | Profitability |
| ROE, ROA | Profitability |
| Current Ratio | Liquidity |
| D/E Ratio | Leverage |
| Interest Coverage | Coverage |

## Run Locally

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Limitations

- Works with **text-based PDFs** only (not scanned/image PDFs)
- Complex merged-cell tables may partially extract — always verify numbers against the source
- Works best with Indian company annual reports (Ind AS format) and major global companies

## Tech Stack

- Python · Streamlit · pdfplumber · pandas · openpyxl

---

*Built by Veer Pratap Singh as part of a Finance + Python portfolio.*
