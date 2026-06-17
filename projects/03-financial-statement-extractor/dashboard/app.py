"""
app.py — Financial Statement Extractor
Upload annual report PDFs → extract P&L, Balance Sheet, Cash Flow → download Excel.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pdf_extractor import extract_tables_from_pages, find_statement_pages
from statement_parser import identify_statement_table, normalize_table, stitch_years
from excel_builder import build_excel

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial Statement Extractor",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0A0A0E !important;
    color: #E4E4E7 !important;
}

:root {
    --bg:    #0A0A0E;
    --surf:  #111116;
    --surf2: #18181F;
    --bdr:   rgba(255,255,255,0.06);
    --bdr2:  rgba(255,255,255,0.12);
    --rule:  rgba(255,255,255,0.05);
    --t1:    #F4F4F5;
    --t2:    #A1A1AA;
    --t3:    #71717A;
    --t4:    #52525B;
    --acc:   #818CF8;
    --green: #10B981;
    --amber: #F59E0B;
    --red:   #EF4444;
    --sky:   #38BDF8;
}

@keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }

.block-container { padding-top: 2.5rem !important; }
[data-testid="stSidebar"] {
    background: var(--surf) !important;
    border-right: 1px solid var(--bdr) !important;
}

/* ── Hero ── */
.hero-wrap {
    max-width: 680px; margin: 2rem auto 0; text-align: center;
    animation: fadeUp 0.7s ease both;
}
.hero-eyebrow {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--acc); margin-bottom: 1rem;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3rem; font-weight: 700; line-height: 1.05;
    letter-spacing: -0.03em; color: var(--t1); margin-bottom: 0.8rem;
}
.hero-title span { color: var(--acc); }
.hero-sub {
    font-size: 1rem; color: var(--t3); max-width: 480px;
    margin: 0 auto 2rem; line-height: 1.7;
}
.hero-pills {
    display: flex; justify-content: center; flex-wrap: wrap;
    gap: 0.45rem; margin-bottom: 2rem;
}
.pill {
    display: inline-flex; align-items: center; gap: 0.3rem;
    background: var(--surf2); border: 1px solid var(--bdr);
    border-radius: 999px; padding: 0.28rem 0.8rem;
    font-size: 0.75rem; color: var(--t3);
}
.pill i { color: var(--acc); }

/* ── Upload card ── */
.upload-card {
    background: var(--surf); border: 1px solid var(--bdr);
    border-radius: 12px; padding: 1.5rem 1.5rem 1rem;
    max-width: 720px; margin: 0 auto 1.5rem;
    animation: fadeUp 0.5s ease both;
}
.card-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--t4); margin-bottom: 0.6rem;
}

/* ── Status badges ── */
.badge {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem;
    border-radius: 4px;
}
.badge-ok     { background: rgba(16,185,129,0.1); color: var(--green); border: 1px solid rgba(16,185,129,0.2); }
.badge-warn   { background: rgba(245,158,11,0.1); color: var(--amber); border: 1px solid rgba(245,158,11,0.2); }
.badge-error  { background: rgba(239,68,68,0.1);  color: var(--red);   border: 1px solid rgba(239,68,68,0.2); }

/* ── Result summary row ── */
.summary-row {
    display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.2rem;
    animation: fadeUp 0.4s ease both;
}
.summary-card {
    flex: 1; min-width: 140px;
    background: var(--surf); border: 1px solid var(--bdr);
    border-radius: 10px; padding: 0.9rem 1rem; text-align: center;
}
.sc-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.6rem; font-weight: 700; color: var(--acc); line-height: 1;
}
.sc-label { font-size: 0.65rem; color: var(--t4); text-transform: uppercase; letter-spacing: 0.07em; margin-top: 0.2rem; }

/* ── Disclaimer / footer ── */
.disclaimer {
    border-top: 1px solid var(--rule); padding-top: 1rem;
    font-size: 0.72rem; color: var(--t4); line-height: 1.7; margin-top: 2rem;
}
.footer { text-align: center; margin-top: 0.75rem; font-size: 0.72rem; color: var(--t4); }
.footer a { color: var(--acc); text-decoration: none; }

/* ── Warning banner ── */
.warn-banner {
    display: flex; align-items: flex-start; gap: 0.6rem;
    border: 1px solid rgba(245,158,11,0.15); border-left: 2px solid var(--amber);
    border-radius: 0 6px 6px 0; padding: 0.7rem 1rem;
    font-size: 0.8rem; color: var(--amber); margin-bottom: 0.8rem;
    background: rgba(245,158,11,0.03);
}
.info-banner {
    display: flex; align-items: flex-start; gap: 0.6rem;
    border: 1px solid rgba(56,189,248,0.12); border-left: 2px solid var(--sky);
    border-radius: 0 6px 6px 0; padding: 0.7rem 1rem;
    font-size: 0.8rem; color: var(--sky); margin-bottom: 1rem;
    background: rgba(56,189,248,0.03);
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "results" not in st.session_state:
    st.session_state.results = None
if "excel_bytes" not in st.session_state:
    st.session_state.excel_bytes = None

# ── Hero ──────────────────────────────────────────────────────────────────────

_, hero_col, _ = st.columns([1, 2.4, 1])
with hero_col:
    st.markdown(
        '<div class="hero-wrap">'
        '  <div class="hero-eyebrow"><i class="bi bi-file-earmark-text"></i> Annual Report → Excel</div>'
        '  <div class="hero-title">Extract <span>Financial Statements</span><br>from Annual Reports</div>'
        '  <div class="hero-sub">Upload up to 5 annual report PDFs. '
        'Get P&amp;L, Balance Sheet, Cash Flow, and pre-built ratios — ready for DCF or ratio analysis.</div>'
        '  <div class="hero-pills">'
        '    <span class="pill"><i class="bi bi-filetype-pdf"></i> PDF → Excel</span>'
        '    <span class="pill"><i class="bi bi-bar-chart-steps"></i> P&amp;L · BS · CF</span>'
        '    <span class="pill"><i class="bi bi-calculator"></i> 8 key ratios</span>'
        '    <span class="pill"><i class="bi bi-layers"></i> Up to 5 years</span>'
        '    <span class="pill"><i class="bi bi-shield-check"></i> No data sent to any server</span>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Upload section ────────────────────────────────────────────────────────────

_, upload_col, _ = st.columns([1, 2.4, 1])
with upload_col:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)

    st.markdown('<div class="card-label">Company name (optional)</div>', unsafe_allow_html=True)
    company_name = st.text_input(
        "Company name", placeholder="e.g. Infosys, TCS, Reliance",
        label_visibility="collapsed", key="company_name_input"
    )
    company_name = company_name.strip() or "Company"

    st.markdown('<div class="card-label" style="margin-top:1rem">Upload annual report PDFs (1–5 files)</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Text-based PDFs only. One PDF per financial year.",
    )

    if uploaded_files and len(uploaded_files) > 5:
        st.warning("Maximum 5 files supported. Only the first 5 will be processed.")
        uploaded_files = uploaded_files[:5]

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="info-banner">'
        '<i class="bi bi-info-circle" style="flex-shrink:0;margin-top:0.1rem"></i>'
        '<span>Works best with text-based PDFs (not scanned). '
        'Each PDF should be one company\'s annual report for one financial year.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    extract_btn = st.button(
        "Extract Statements →",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    )

# ── Extraction ────────────────────────────────────────────────────────────────

if extract_btn and uploaded_files:
    st.session_state.results = None
    st.session_state.excel_bytes = None

    per_year_pnl: list[tuple[str, dict]] = []
    per_year_bs:  list[tuple[str, dict]] = []
    per_year_cf:  list[tuple[str, dict]] = []
    warnings: list[str] = []

    progress_bar = st.progress(0, text="Starting extraction…")

    for file_idx, uploaded_file in enumerate(uploaded_files):
        file_bytes = uploaded_file.read()
        file_label = uploaded_file.name

        progress_bar.progress(
            int((file_idx / len(uploaded_files)) * 80),
            text=f"Processing {file_label}…",
        )

        try:
            pages = find_statement_pages(file_bytes)
        except Exception as e:
            warnings.append(f"{file_label}: Could not read PDF — {e}")
            continue

        # Determine year label from filename or fallback
        import re
        year_match = re.search(r"20\d{2}", file_label)
        year_label = year_match.group() if year_match else f"Year {file_idx + 1}"

        for stmt_key, year_list, per_year_list in [
            ("pnl", per_year_pnl, per_year_pnl),
            ("bs",  per_year_bs,  per_year_bs),
            ("cf",  per_year_cf,  per_year_cf),
        ]:
            stmt_pages = pages.get(stmt_key, [])
            if not stmt_pages:
                warnings.append(f"{file_label}: Could not locate {'P&L' if stmt_key=='pnl' else 'Balance Sheet' if stmt_key=='bs' else 'Cash Flow'} section.")
                continue

            try:
                raw_tables = extract_tables_from_pages(file_bytes, stmt_pages)
                best_table = identify_statement_table(raw_tables, stmt_key)
                if best_table is None:
                    warnings.append(f"{file_label}: Found {'P&L' if stmt_key=='pnl' else 'Balance Sheet' if stmt_key=='bs' else 'Cash Flow'} page but could not extract a table.")
                    continue
                normalized = normalize_table(best_table, stmt_key, year_label)
                per_year_list.append((year_label, normalized))
            except Exception as e:
                warnings.append(f"{file_label} ({'P&L' if stmt_key=='pnl' else 'BS' if stmt_key=='bs' else 'CF'}): {e}")

    progress_bar.progress(85, text="Stitching multi-year data…")

    pnl_stitched = stitch_years(per_year_pnl, "pnl") if per_year_pnl else {}
    bs_stitched  = stitch_years(per_year_bs,  "bs")  if per_year_bs  else {}
    cf_stitched  = stitch_years(per_year_cf,  "cf")  if per_year_cf  else {}

    progress_bar.progress(92, text="Building Excel…")

    excel_bytes = None
    if pnl_stitched or bs_stitched or cf_stitched:
        try:
            excel_bytes = build_excel(
                pnl_stitched, bs_stitched, cf_stitched,
                company_name=company_name,
            )
        except Exception as e:
            warnings.append(f"Excel build failed: {e}")

    progress_bar.progress(100, text="Done!")

    st.session_state.results = {
        "pnl": pnl_stitched,
        "bs":  bs_stitched,
        "cf":  cf_stitched,
        "warnings": warnings,
        "company": company_name,
        "n_years": len(uploaded_files),
    }
    st.session_state.excel_bytes = excel_bytes
    st.rerun()

# ── Results ───────────────────────────────────────────────────────────────────

if st.session_state.results:
    res = st.session_state.results
    pnl = res["pnl"]
    bs  = res["bs"]
    cf  = res["cf"]
    warnings = res["warnings"]
    company  = res["company"]

    _, res_col, _ = st.columns([1, 2.4, 1])
    with res_col:
        # Warnings
        for w in warnings:
            st.markdown(
                f'<div class="warn-banner"><i class="bi bi-exclamation-triangle" style="flex-shrink:0;margin-top:0.1rem"></i><span>{w}</span></div>',
                unsafe_allow_html=True,
            )

        # Summary cards
        years = []
        for d in [pnl, bs, cf]:
            for item_data in d.values():
                for y in item_data:
                    if y not in years:
                        years.append(y)

        pnl_rows = sum(1 for v in pnl.values() if any(x is not None for x in v.values()))
        bs_rows  = sum(1 for v in bs.values()  if any(x is not None for x in v.values()))
        cf_rows  = sum(1 for v in cf.values()  if any(x is not None for x in v.values()))

        st.markdown(
            f'<div class="summary-row">'
            f'  <div class="summary-card"><div class="sc-num">{len(years)}</div><div class="sc-label">Years extracted</div></div>'
            f'  <div class="summary-card"><div class="sc-num">{pnl_rows}</div><div class="sc-label">P&L line items</div></div>'
            f'  <div class="summary-card"><div class="sc-num">{bs_rows}</div><div class="sc-label">Balance sheet items</div></div>'
            f'  <div class="summary-card"><div class="sc-num">{cf_rows}</div><div class="sc-label">Cash flow items</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Download button
        if st.session_state.excel_bytes:
            filename = f"{company.replace(' ', '_')}_financials.xlsx"
            st.download_button(
                label="⬇ Download Excel",
                data=st.session_state.excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

    # ── Preview tabs ──────────────────────────────────────────────────────────
    def stmts_to_df(data: dict) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        rows = []
        for label, year_vals in data.items():
            row = {"Line Item": label}
            row.update({y: v for y, v in year_vals.items()})
            rows.append(row)
        return pd.DataFrame(rows).set_index("Line Item")

    tab1, tab2, tab3 = st.tabs(["  P&L  ", "  Balance Sheet  ", "  Cash Flow  "])

    with tab1:
        if pnl:
            df = stmts_to_df(pnl)
            st.dataframe(df, use_container_width=True, height=500)
        else:
            st.info("P&L statement could not be extracted from the uploaded files.")

    with tab2:
        if bs:
            df = stmts_to_df(bs)
            st.dataframe(df, use_container_width=True, height=500)
        else:
            st.info("Balance Sheet could not be extracted from the uploaded files.")

    with tab3:
        if cf:
            df = stmts_to_df(cf)
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("Cash Flow statement could not be extracted from the uploaded files.")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="disclaimer">'
        '<strong>Note:</strong> Extraction accuracy depends on PDF quality and table structure. '
        'Always verify extracted numbers against the source document before use in analysis. '
        'Works with text-based PDFs — scanned/image-only PDFs are not supported.'
        '</div>'
        '<div class="footer">Built by <strong>Veer Pratap Singh</strong> &nbsp;·&nbsp; '
        '<a href="https://github.com/VeerVVAPS-portfolio">GitHub</a> &nbsp;·&nbsp; '
        '<a href="https://linkedin.com/in/veer-pratap-singh-681a5530b">LinkedIn</a></div>',
        unsafe_allow_html=True,
    )
