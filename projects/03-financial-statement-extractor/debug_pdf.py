"""Quick debug script — place PDF in this folder then run: python debug_pdf.py"""
import sys, io, re
sys.path.insert(0, "src")
import pdfplumber
from pdf_extractor import find_statement_pages, extract_tables_from_pages
from statement_parser import identify_statement_table, normalize_table

PDF_PATH = "infosys-ar-25.pdf"

with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()

pages = find_statement_pages(pdf_bytes)
print("Pages found:", pages)

with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
    for stmt, page_list in pages.items():
        if not page_list:
            continue
        print(f"\n{'='*60}")
        print(f"{stmt.upper()} — pages {page_list}")

        for pg_idx in page_list[:2]:
            pg = pdf.pages[pg_idx]
            text = pg.extract_text() or ""
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            print(f"\n  Page {pg_idx} — first 6 lines:")
            for l in lines[:6]:
                print(f"    {l}")
            nums = re.findall(r'\b\d{1,3}(?:,\d{2,3})+\b', text)
            print(f"  Formatted numbers: {len(nums)} | examples: {nums[:5]}")

        raw_tables = extract_tables_from_pages(pdf_bytes, page_list)
        print(f"\n  Raw tables extracted: {len(raw_tables)}")
        best = identify_statement_table(raw_tables, stmt)
        if best:
            print(f"  Merged table: {len(best)} rows x {max(len(r) for r in best)} cols")
            print("  First 8 rows:")
            for row in best[:8]:
                print(f"    {row}")
            result = normalize_table(best, stmt)
            print(f"\n  Normalized ({len(result)} items):")
            for k, v in result.items():
                print(f"    {k}: {v}")
        else:
            print("  No suitable table found.")
