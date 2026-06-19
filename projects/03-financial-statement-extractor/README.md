# Financial Statement Extractor

Extracts P&L, Balance Sheet, and Cash Flow statements from annual report PDFs and outputs a formatted, analysis-ready Excel file — no copy-pasting required.

## What It Does

1. Upload 1–5 annual report PDFs (one per financial year — name files with the full 4-digit year, e.g. `infosys-ar-2025.pdf`, so the year is detected correctly)
2. The tool automatically finds the financial statement pages (PyMuPDF scans the full document fast; pdfplumber extracts the actual tables on just those pages)
3. Tables are extracted and normalized to a standard schema
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

## Tested Against

Validated against 9 Indian companies across 6 sectors: Infosys, TCS, Maruti Suzuki, Asian Paints, Dr. Reddy's, Page Industries, and three banks (HDFC Bank, ICICI Bank, Kotak Mahindra Bank). P&L and Balance Sheet extraction reconciles exactly (Assets = Liabilities + Equity, or Total Capital and Liabilities = Total Assets for banks) for all 9. Cash Flow reconciles for 8 of 9.

Banks use a completely different statement structure (Banking Regulation Act format — Capital/Deposits/Advances instead of Trade Receivables/Inventories, no Current/Non-Current split) and are detected automatically and routed to a separate schema.

## Limitations

- Works with **text-based PDFs** only (not scanned/image PDFs)
- Complex merged-cell tables may partially extract — always verify numbers against the source
- Works best with Indian company annual reports (Ind AS / Banking Regulation Act format)
- Unusual column layouts (a label column that overflows past where the value columns start) can occasionally split a label from its value — seen once, on Page Industries' Cash Flow page
- **Known issue (open as of 2026-06-19):** headline totals (Revenue, Net Profit, Total Assets/Equity, CF subtotals) are verified correct, but detail rows underneath can contain noise — auditor signature-block text (DIN/membership numbers, signing dates) occasionally gets captured as a line item, and Cash Flow detail rows can pull in rows from the adjacent Statement of Changes in Equity table. See `INTERVIEW_PREP.md` for the full repro notes. Not yet fixed.

## Tech Stack

- Python · Streamlit · PyMuPDF · pdfplumber · pandas · openpyxl

---

*Built by Veer Pratap Singh as part of a Finance + Python portfolio.*
