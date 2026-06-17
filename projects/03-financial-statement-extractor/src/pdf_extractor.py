"""
pdf_extractor.py
Uses pdfplumber to find financial statement pages and extract raw tables.
"""

from __future__ import annotations

import io
import re
from collections import defaultdict
from typing import BinaryIO

import pdfplumber

# ── More specific page keywords ───────────────────────────────────────────────
# These are tighter than schema.PAGE_KEYWORDS to avoid MD&A / overview sections.

_PAGE_KEYWORDS: dict[str, list[str]] = {
    "pnl": [
        "statement of profit and loss",
        "statement of profit & loss",
        "profit and loss account",
        "consolidated statement of profit",
        "standalone statement of profit",
        "statement of income",
        "income statement",
    ],
    "bs": [
        "balance sheet as at",
        "balance sheet as of",
        "statement of financial position",
        "consolidated balance sheet",
        "standalone balance sheet",
        "balance sheet",
    ],
    "cf": [
        "cash flow statement",
        "statement of cash flows",
        "cash flows from operating",
        "cash flows for the year",
    ],
}

# Phrases that strongly confirm a page is the ACTUAL financial statement
_CONFIRM_PHRASES = [
    "for the year ended",
    "for the period ended",
    "₹ in crore",
    "in crore",
    "in millions",
    "in lakhs",
    "rs. in",
    "inr in",
]


def _keyword_in_heading(lines: list[str], keywords: list[str]) -> bool:
    """True if any keyword appears as a short line in the first 10 lines of the page."""
    for line in lines[:10]:
        line_lower = line.lower().strip()
        if len(line_lower) < 5:
            continue
        for kw in keywords:
            # Keyword must make up most of the line (it's a heading, not body text)
            if kw in line_lower and len(line_lower) < len(kw) + 40:
                return True
    return False


def _score_page(text: str, lines: list[str]) -> int:
    """
    Score a page for likelihood of being an actual financial statement.
    Higher = more likely.
    """
    score = 0
    text_lower = text.lower()
    first_500 = text_lower[:500]

    # "Particulars" is the standard first-column header in Indian financial statements
    if "particulars" in text_lower:
        score += 25

    # Number count (thousands-formatted numbers like 1,62,990)
    numbers = re.findall(r'\b\d{1,3}(?:,\d{2,3})+\b', text)
    score += min(len(numbers), 30)

    # Year / period comparison header near top of page
    for phrase in ["for the year ended", "year ended march", "as at march", "as of march"]:
        if phrase in first_500:
            score += 15
            break

    # Currency unit notation
    for phrase in ["₹ in crore", "in crore", "in millions", "rs. in", "inr in"]:
        if phrase in text_lower:
            score += 10
            break

    # Year columns present (comparison table)
    years = re.findall(r'\b20\d{2}\b', text)
    score += min(len(set(years)), 3) * 4

    # Strong penalties: notes / policy / MD&A sections
    for bad in ["accounting policy", "accounting policies", "notes to",
                "note no.", "critical accounting", "management discussion",
                "about this report", "business highlights", "overview"]:
        if bad in first_500:
            score -= 25

    return score


def find_statement_pages(pdf_file: bytes | BinaryIO) -> dict[str, list[int]]:
    """
    Scan every page, score candidates, return best page indices per statement.
    Only accepts pages where the keyword appears as a heading (not buried in body text).
    Returns {"pnl": [...], "bs": [...], "cf": [...]}
    Each list = best matched page + up to 3 following pages.
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)

    candidates: dict[str, list[tuple[int, int]]] = {"pnl": [], "bs": [], "cf": []}
    found: dict[str, list[int]] = {"pnl": [], "bs": [], "cf": []}

    with pdfplumber.open(pdf_file) as pdf:
        total_pages = len(pdf.pages)

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

            for stmt_type, keywords in _PAGE_KEYWORDS.items():
                # Must be a heading — keyword in first 10 lines as a short line
                if not _keyword_in_heading(lines, keywords):
                    continue
                score = _score_page(text, lines)
                candidates[stmt_type].append((score, i))

        for stmt_type, scored in candidates.items():
            if not scored:
                continue
            best_score, best_idx = max(scored, key=lambda x: x[0])

            # Only look back if the best page is a continuation (not the statement start)
            best_text = (pdf.pages[best_idx].extract_text() or "").lower()
            is_contd = any(m in best_text[:200] for m in ["(contd.)", "(continued)", "continued..."])

            pages = []
            if is_contd and best_idx > 0:
                pages.append(best_idx - 1)
            pages.append(best_idx)
            for offset in (1, 2, 3):
                next_idx = best_idx + offset
                if next_idx >= total_pages:
                    break
                next_text = pdf.pages[next_idx].extract_text() or ""
                next_lines = [ln.strip() for ln in next_text.split('\n') if ln.strip()]
                # Stop if the next page opens a DIFFERENT type of financial statement.
                # This prevents consolidated + standalone versions from being merged.
                is_new_statement = any(
                    other_type != stmt_type and _keyword_in_heading(next_lines, other_kws)
                    for other_type, other_kws in _PAGE_KEYWORDS.items()
                )
                if is_new_statement:
                    break
                pages.append(next_idx)
            found[stmt_type] = pages

    return found


def _has_duplication_artifacts(tables: list[list[list[str]]]) -> bool:
    """
    Detect if pdfplumber returned cells with duplicated content.
    E.g. '162,990 162,990 153,670' or '2.18 2.18' — a known PDF rendering artifact.
    """
    dup = total = 0
    for table in tables:
        for row in table:
            for cell in row:
                if not cell or len(cell) < 4:
                    continue
                total += 1
                # Remove commas then split; check if first two tokens are identical
                parts = cell.replace(",", "").split()
                if len(parts) >= 2 and parts[0] == parts[1]:
                    dup += 1
    return total > 0 and (dup / total) > 0.06   # >6% of cells have duplication


def extract_tables_from_pages(
    pdf_file: bytes | BinaryIO,
    page_indices: list[int],
) -> list[list[list[str]]]:
    """
    Extract tables from the given page indices.
    Tries pdfplumber extract_tables() first; if it finds duplication artifacts
    (common in InDesign-generated annual report PDFs), falls back to parsing
    the raw page text with a financial regex instead.
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)

    all_tables: list[list[list[str]]] = []

    with pdfplumber.open(pdf_file) as pdf:
        for idx in page_indices:
            if idx >= len(pdf.pages):
                continue
            page = pdf.pages[idx]

            # Try standard table extraction
            tables = page.extract_tables() or []
            cleaned = [_clean_table(t) for t in tables if t]
            cleaned = [t for t in cleaned if t]

            if cleaned and not _has_duplication_artifacts(cleaned):
                all_tables.extend(cleaned)
            else:
                # Fallback: parse raw text line by line (clean for most annual reports)
                text_table = _text_to_table(page.extract_text() or "")
                if text_table:
                    all_tables.append(text_table)

    return all_tables


# ── Table cleaning ────────────────────────────────────────────────────────────

def _clean_table(raw_table: list[list]) -> list[list[str]]:
    """Normalise a raw pdfplumber table: strip whitespace, replace None with ''."""
    cleaned = []
    for row in raw_table:
        if row is None:
            continue
        clean_row = [
            re.sub(r"\s+", " ", str(cell)).strip() if cell is not None else ""
            for cell in row
        ]
        if any(c for c in clean_row):
            cleaned.append(clean_row)
    return cleaned


# ── Word-position table reconstruction ───────────────────────────────────────

def _words_to_table(page) -> list[list[str]]:
    """
    Reconstruct a table from word bounding boxes.
    Groups words into rows by y-coordinate, then into columns by x-position.
    Works for PDFs where columns are space-aligned (common in Indian annual reports).
    """
    try:
        words = page.extract_words()
    except Exception:
        return []

    if not words:
        return []

    page_width = float(page.width)

    # Group words by row (bucket y-coordinates into 4px bands)
    rows_dict: dict[int, list] = defaultdict(list)
    for w in words:
        y_key = int(w["top"] / 4) * 4
        rows_dict[y_key].append(w)

    # Detect column x-boundaries by clustering x0 values
    # Simple heuristic: label column is left 55% of page; value columns are right 45%
    label_boundary = page_width * 0.55

    result: list[list[str]] = []
    for y_key in sorted(rows_dict.keys()):
        row_words = sorted(rows_dict[y_key], key=lambda w: w["x0"])

        label_words = [w["text"] for w in row_words if w["x0"] < label_boundary]
        value_words = [w["text"] for w in row_words if w["x0"] >= label_boundary]

        label = " ".join(label_words).strip()

        # Split value_words into individual number columns
        # Cluster by x0 gaps > 15px
        value_columns: list[list[str]] = []
        if value_words:
            current: list[str] = [value_words[0]]
            prev_x = [w["x0"] for w in row_words if w["x0"] >= label_boundary][0]
            for wi, w in enumerate(row_words):
                if w["x0"] < label_boundary:
                    continue
                if wi == 0:
                    continue
                gap = w["x0"] - prev_x
                if gap > 30:
                    value_columns.append(" ".join(current))
                    current = [w["text"]]
                else:
                    current.append(w["text"])
                prev_x = w["x1"]
            value_columns.append(" ".join(current))

        row = [label] + value_columns
        if any(c.strip() for c in row):
            result.append(row)

    return result


# ── Text-line fallback ────────────────────────────────────────────────────────

# Matches financial numbers: comma-grouped integers like 162,990 or 1,62,990
# Also handles negative in parentheses: (12,345)
_FIN_NUM_RE = re.compile(r'\(?\b\d{1,3}(?:,\d{2,3})+(?:\.\d+)?\b\)?')

# Trailing note references like "2.18" or "2.1" that appear after the label
_NOTE_REF_RE = re.compile(r'\s+\d{1,2}\.\d{1,2}\s*$')


def _text_to_table(text: str) -> list[list[str]]:
    """
    Parse raw page text into a financial table.

    For each line:
    - Finds all comma-formatted numbers (financial values).
    - Strips trailing note references (e.g. "2.18") from the label.
    - Returns [label, value1, value2, ...] rows.

    This handles PDFs like Infosys where extract_tables() produces
    duplication artifacts but extract_text() is clean.
    """
    rows: list[list[str]] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        fin_nums = _FIN_NUM_RE.findall(line)

        if not fin_nums:
            # Section header or label-only row (no financial numbers)
            rows.append([line])
            continue

        # Label = everything before the first financial number
        first_match = _FIN_NUM_RE.search(line)
        label = line[: first_match.start()].strip()  # type: ignore[union-attr]
        # Strip trailing note reference (e.g. "2.18") from label
        label = _NOTE_REF_RE.sub("", label).strip()

        rows.append([label] + fin_nums)

    return rows
