"""
pdf_extractor.py
Finds financial statement pages and extracts raw tables.

Two libraries, two jobs:
- PyMuPDF (fitz): fast plain-text extraction, used to scan every page of the
  document (can be 300+ pages) to locate P&L/BS/CF. ~50x faster than
  pdfplumber for this — pdfplumber's layout analysis is overkill for a page
  scoring pass that only needs heading keywords and number counts.
- pdfplumber: used only on the small set of pages found above, for its
  superior table-structure extraction.
"""

from __future__ import annotations

import io
import re
from collections import defaultdict
from typing import BinaryIO

import fitz  # PyMuPDF
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

# Headings for OTHER report sections that commonly follow the three core
# statements (Statement of Changes in Equity, then Notes). These aren't one
# of our three statement types, so the PNL/BS/CF keyword check alone won't
# catch them — without this, a continuation-page scan can run straight
# through Changes in Equity and into the Notes section, merging unrelated
# data into the statement being extracted.
_OTHER_SECTION_KEYWORDS = [
    "statement of changes in equity",
    "notes to the",
    "notes to standalone",
    "notes to consolidated",
    "schedules to the",          # HDFC Bank's name for its Notes section
    "schedules forming part",    # ICICI Bank's name for its Notes section
    "explanatory notes",         # Page Industries' name for supplementary notes
]

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


# Compound terms that contain "balance sheet" (or other statement keywords)
# as a substring without being the statement itself — e.g. bank annual
# reports have extensive notes on "on-balance sheet exposures" / "off-balance
# sheet exposures" (securitisation, contingent liabilities) that would
# otherwise pass the heading check (short line, keyword near the start).
_HEADING_FALSE_POSITIVES = [
    "on-balance sheet",
    "off-balance sheet",
    "on balance sheet",
    "off balance sheet",
]

# One representative phrase per statement type, used to detect a COMBINED
# section title that names more than one statement — e.g. Kotak Mahindra
# Bank's running header "Consolidated Balance Sheet and Profit and Loss
# Account" (a navigation label for the whole Financial Statements section,
# not the Balance Sheet's own heading). A line naming 2+ of these is a
# section-level title, not a single statement's heading, regardless of
# position/length — and rejecting it matters because such a combined-title
# page can score HIGHER than the real, simpler heading (more numbers
# visible from data on the page) and win the page-selection.
_STATEMENT_TYPE_SIGNALS = ["balance sheet", "profit and loss", "cash flow"]


def _keyword_in_heading(lines: list[str], keywords: list[str]) -> bool:
    """
    True if any keyword appears as a short line in the first 10 lines of the page,
    AND starts near the beginning of that line.
    The position check matters: a sentence like "Balance outstanding as at
    balance sheet date" (a note about loans) is short enough to pass a pure
    length check, but the keyword appears mid-sentence (idx=27), not as a
    title. Real headings start with "Consolidated "/"Standalone " (idx ≤ 13)
    or the bare keyword (idx = 0) — 20 leaves margin for both while still
    excluding the false positive.
    """
    for line in lines[:10]:
        line_lower = line.lower().strip()
        if len(line_lower) < 5:
            continue
        if any(fp in line_lower for fp in _HEADING_FALSE_POSITIVES):
            continue
        if sum(sig in line_lower for sig in _STATEMENT_TYPE_SIGNALS) >= 2:
            continue
        # Auditor's reports enumerate findings as "(a) ...", "(b) ...", and
        # routinely name all three statements in one sentence — e.g.
        # "(c) The Standalone Balance Sheet, the Standalone Profit and Loss
        # Account...". A line starting with a lettered/numbered list marker
        # is prose, never an actual statement title.
        if re.match(r'^\(?[a-z0-9ivx]{1,4}[\)\.]\s', line_lower):
            continue
        for kw in keywords:
            idx = line_lower.find(kw)
            # Keyword must make up most of the line (it's a heading, not body text)
            # and start near the beginning (allowing "Consolidated "/"Standalone ").
            if idx != -1 and idx <= 20 and len(line_lower) < len(kw) + 40:
                return True

        # Letter-spaced stylised titles (HDFC Bank renders major statement
        # headings as "S TA N D A L O N E B A L A N C E S H E E T" — likely
        # a font/kerning artifact in the PDF's text layer). A normal
        # substring check never matches "balance sheet" against that, so the
        # real heading page never even becomes a candidate while body-text
        # mentions elsewhere keep winning instead. Detected by: most tokens
        # on the line are short (<=2 chars) — true sentences don't look
        # like that — then compare with all spaces removed.
        tokens = line_lower.split()
        if tokens and (sum(len(t) <= 2 for t in tokens) / len(tokens)) >= 0.7:
            despaced = line_lower.replace(" ", "")
            for kw in keywords:
                if kw.replace(" ", "") in despaced:
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

    # Bank statements use "Schedule" instead of "Particulars" as the
    # first-column header, so they don't get the bonus above. "Capital and
    # Liabilities" / "Interest Earned"+"Interest Expended" are strong,
    # distinctive markers of the REAL regulatory-format Balance Sheet/P&L —
    # added because an MD&A summary table titled just "Balance Sheet" (with
    # narrative composition breakdowns, not the actual statement) was
    # outscoring the real one on number-count alone.
    if "capital and liabilities" in text_lower:
        score += 25
    if "interest earned" in text_lower and "interest expended" in text_lower:
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


PageRef = tuple[int, str]


def _get_page_text(doc, idx: int, column: str, sort: bool = True) -> str:
    page = doc[idx]
    if column == "full":
        return page.get_text(sort=sort) if sort else page.get_text()
    rect = page.rect
    if column == "left":
        clip = fitz.Rect(0, 0, rect.width / 2, rect.height)
    else:
        clip = fitz.Rect(rect.width / 2, 0, rect.width, rect.height)
    return page.get_text(sort=sort, clip=clip) if sort else page.get_text(clip=clip)


def find_statement_pages(pdf_file: bytes | BinaryIO) -> dict[str, list[int]]:
    """
    Scan every page, score candidates, return best page indices per statement.
    Only accepts pages where the keyword appears as a heading (not buried in body text).
    Returns {"pnl": [...], "bs": [...], "cf": [...]}
    Each list = best matched page + up to 3 following pages.

    Uses PyMuPDF for text extraction (see module docstring) — on a 369-page
    annual report a single sort=True pass over every page took 26s. Cut to
    ~8s with a two-pass approach: a cheap unsorted scan filters ~370 pages
    down to the ~70 that mention a statement keyword anywhere; only those
    get the more expensive sort=True extraction needed for heading detection.
    """
    pdf_bytes = pdf_file if isinstance(pdf_file, bytes) else pdf_file.read()

    candidates: dict[str, list[tuple[int, int, str]]] = {"pnl": [], "bs": [], "cf": []}
    found: dict[str, list[tuple[int, str]]] = {"pnl": [], "bs": [], "cf": []}

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_pages = len(doc)

    all_keywords = [kw for kws in _PAGE_KEYWORDS.values() for kw in kws]
    unsorted_texts = [page.get_text() for page in doc]

    # sort=True orders text by visual top-to-bottom position rather than the
    # PDF's internal content-stream order — without it, page titles placed in
    # a separate text block (common in InDesign exports) can end up last.
    # Cached lazily since most pages never need it.
    sorted_cache: dict[tuple[int, str], str] = {}

    def get_sorted_text(idx: int, column: str = "full") -> str:
        key = (idx, column)
        if key not in sorted_cache:
            sorted_cache[key] = _get_page_text(doc, idx, column, sort=True)
        return sorted_cache[key]

    candidate_pages = [
        i for i, t in enumerate(unsorted_texts)
        if any(kw in t.lower() for kw in all_keywords)
    ]

    # Check each candidate page in three views: full page, left half, right
    # half. Some reports run two statements side by side on one physical
    # page (e.g. Maruti's Balance Sheet + P&L) — the unsplit text is too long
    # to pass the heading-length check, but each half on its own reads clean.
    for i in candidate_pages:
        # Running-header check: if the page's own header announces it's part
        # of the Notes/Schedules section, skip the WHOLE page (all column
        # views) — no individual line should be able to override that, since
        # accounting-policy prose routinely contains short, early-starting
        # lines like "Consolidated Balance Sheet when they are sold..." that
        # would otherwise pass the heading check below. Checked on the FULL,
        # uncropped page text: a page-wide title can straddle the left/right
        # crop boundary and come out garbled in either half alone (seen on
        # HDFC Bank's "SCHEDULES TO THE..." header, which is titled this way
        # rather than the more common "Notes to the ...").
        full_text = get_sorted_text(i, "full")
        full_lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]
        # 5 lines, not 3: ICICI's running header splits "SCHEDULES" and
        # "forming part of the Accounts" across a line boundary that a
        # narrower window would miss.
        header_zone = " ".join(full_lines[:5]).lower()
        if any(kw in header_zone for kw in _OTHER_SECTION_KEYWORDS):
            continue
        # CEO/CFO "Compliance Certificate" (a standard SEBI corporate-
        # governance filing) declares "We have reviewed financial statements
        # and the cash flow statement for the year ended..." as boilerplate —
        # passes the heading check on its own despite not being the actual
        # statement. Page Industries titles this section "CORPORATE
        # GOVERNANCE / COMPLIANCE CERTIFICATE".
        if "compliance certificate" in header_zone:
            continue
        # Auditor's reports ("Independent Auditor's Report") describe what
        # they audited in full sentences — "comprise the Standalone Balance
        # Sheet as at March 31, ... and the Standalone Cash Flow Statement
        # for the year then ended" — which routinely passes the heading
        # check below despite being prose, not a title. Every Indian
        # auditor's report opens "To the Members of [Company]" within its
        # first ~10 lines; broader window than the 3-line check above since
        # the report's own title is sometimes rendered as letter-spaced
        # stylised text ("I N D E P E N D E N T A U...") that doesn't match
        # a plain "independent auditor" substring check.
        wide_header_zone = " ".join(full_lines[:10]).lower()
        if "to the members of" in wide_header_zone:
            continue

        for column in ("full", "left", "right"):
            text = get_sorted_text(i, column)
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            if not lines:
                continue

            for stmt_type, keywords in _PAGE_KEYWORDS.items():
                # Must be a heading — keyword in first 10 lines as a short line
                if not _keyword_in_heading(lines, keywords):
                    continue
                score = _score_page(text, lines)
                candidates[stmt_type].append((score, i, column))

    for stmt_type, scored in candidates.items():
        if not scored:
            continue
        best_score, best_idx, best_col = max(scored, key=lambda x: x[0])

        # Only look back if the best page is a continuation (not the statement start)
        best_text = get_sorted_text(best_idx, best_col).lower()
        is_contd = any(m in best_text[:200] for m in ["(contd.)", "(continued)", "continued..."])

        # If the OPPOSITE column of a page has the SAME statement's heading
        # too, it's one statement flowing across both halves (e.g. Maruti's
        # Cash Flow: operating activities in the left column, investing/
        # financing in the right — both columns say "Standalone Statement of
        # Cash Flows"; Asian Paints' financing section sits in the left
        # column of a page where we matched via the right). Different
        # statements sharing a page (Balance Sheet left / P&L right) have
        # DIFFERENT headings per side, so this only fires for genuine
        # continuations. Checked for every page added, not just the first —
        # the opposite column can hold the continuation on ANY page, not
        # only the one where the statement was first found.
        def add_with_opposite_column(idx: int, col: str) -> None:
            pages.append((idx, col))
            if col not in ("left", "right"):
                return
            opposite_col = "right" if col == "left" else "left"
            opp_text = get_sorted_text(idx, opposite_col)
            opp_lines = [ln.strip() for ln in opp_text.split('\n') if ln.strip()]
            if opp_lines and _keyword_in_heading(opp_lines, _PAGE_KEYWORDS[stmt_type]):
                pages.append((idx, opposite_col))

        pages: list[tuple[int, str]] = []
        if is_contd and best_idx > 0:
            add_with_opposite_column(best_idx - 1, best_col)
        add_with_opposite_column(best_idx, best_col)

        for offset in (1, 2, 3):
            next_idx = best_idx + offset
            if next_idx >= total_pages:
                break
            # Continuation pages are checked in the SAME column as the match —
            # in side-by-side layouts, a statement keeps its column position
            # across pages rather than switching sides.
            next_text = get_sorted_text(next_idx, best_col)
            next_lines = [ln.strip() for ln in next_text.split('\n') if ln.strip()]
            # Stop if the next page opens a DIFFERENT type of financial statement,
            # OR a different report section entirely (Changes in Equity, Notes).
            # This prevents consolidated + standalone versions — and unrelated
            # sections — from being merged into the statement being extracted.
            is_new_statement = any(
                other_type != stmt_type and _keyword_in_heading(next_lines, other_kws)
                for other_type, other_kws in _PAGE_KEYWORDS.items()
            ) or _keyword_in_heading(next_lines, _OTHER_SECTION_KEYWORDS)
            if is_new_statement:
                break
            add_with_opposite_column(next_idx, best_col)
        found[stmt_type] = pages

    doc.close()
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


def _has_merged_row_artifacts(tables: list[list[list[str]]]) -> bool:
    """
    Detect a different pdfplumber corruption mode (seen in TCS's PDF, distinct
    from the Infosys duplication artifact): instead of duplicating values,
    pdfplumber merges an entire column's worth of numbers into a single cell
    on one row, leaving the following rows with empty labels and one orphaned
    value each. Symptom: a cell containing many space-separated number-like
    tokens (a real value cell has at most 2-3; a merged cell has dozens).
    """
    for table in tables:
        for row in table:
            for cell in row:
                if not cell:
                    continue
                tokens = cell.split()
                numericish = sum(1 for t in tokens if re.match(r'^\(?-?[\d,]+\)?$', t))
                if numericish >= 4:
                    return True
    return False


def _has_merged_label_artifacts(tables: list[list[list[str]]]) -> bool:
    """
    Detect the inverse of _has_merged_row_artifacts (seen in TCS's Cash Flow
    page): instead of numbers merging into one cell, many distinct line-item
    LABELS merge into a single oversized label cell, while the value column
    for that row ends up empty. A real label is well under 100 characters;
    a row that absorbed a dozen line items runs several hundred.
    """
    for table in tables:
        for row in table:
            if row and row[0] and len(row[0]) > 150:
                return True
    return False


# A schedule-reference-only "label" — e.g. "1", "1A", "17 & 18" — seen on
# ICICI Bank's Balance Sheet, where pdfplumber put the Schedule column's
# number into the label cell instead of the real line-item text (which got
# dropped entirely, the same underlying column-boundary misjudgement as the
# fully-blank case, just with the wrong column surviving instead of none).
_SCHEDULE_REF_ONLY_RE = re.compile(r'^\d{1,2}[a-zA-Z]?(\s*&\s*\d{1,2})?$')


def _has_blank_label_artifacts(tables: list[list[list[str]]]) -> bool:
    """
    Detect a fourth corruption mode (seen on HDFC Bank's Balance Sheet):
    pdfplumber misjudges the column boundary and drops the label column
    entirely, leaving every row's first cell blank (or, on ICICI Bank, just
    the Schedule reference number) while the value columns are intact.
    Symptom: most data rows (excluding the header row) have no usable label
    but at least one numeric value.
    """
    for table in tables:
        if len(table) < 4:
            continue
        data_rows = table[1:]
        unusable_label_with_value = sum(
            1 for row in data_rows
            if row
            and (not (row[0] or "").strip() or _SCHEDULE_REF_ONLY_RE.match((row[0] or "").strip()))
            and any(_parse_number_loose(c) is not None for c in row[1:])
        )
        if data_rows and unusable_label_with_value / len(data_rows) > 0.5:
            return True
    return False


def _has_single_column_artifacts(tables: list[list[list[str]]]) -> bool:
    """
    Detect a sixth corruption mode (seen on Kotak Mahindra Bank's P&L):
    pdfplumber drops BOTH the label column and one of the two value columns,
    keeping only a single numeric cell per row — e.g. ['656,688,252'] with
    no label and no second year's figure at all. More severe than the
    blank-label case (#4), where at least the value columns survived intact.
    Symptom: most data rows have exactly one cell, and it's numeric.
    """
    for table in tables:
        if len(table) < 4:
            continue
        data_rows = table[1:]
        single_numeric_cell = sum(
            1 for row in data_rows
            if row and len(row) == 1 and _parse_number_loose(row[0]) is not None
        )
        if data_rows and single_numeric_cell / len(data_rows) > 0.5:
            return True
    return False


def _parse_number_loose(cell: str) -> float | None:
    if not cell:
        return None
    try:
        return float(cell.strip().strip("()").replace(",", ""))
    except ValueError:
        return None


def extract_tables_from_pages(
    pdf_file: bytes | BinaryIO,
    page_indices: list[int | tuple[int, str]],
) -> list[list[list[str]]]:
    """
    Extract tables from the given page references.
    Each entry is either a plain page index (ordinary single-column page) or
    an (index, column) tuple where column is "left"/"right" — for pages
    where two statements sit side by side, only that half is extracted, so
    the table data isn't a mix of both statements' columns.

    Tries pdfplumber extract_tables() first; if it finds duplication artifacts
    (common in InDesign-generated annual report PDFs) or merged-row artifacts
    (seen in TCS's PDF — see _has_merged_row_artifacts), falls back to parsing
    the raw page text with a financial regex instead.
    """
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)

    all_tables: list[list[list[str]]] = []

    with pdfplumber.open(pdf_file) as pdf:
        for ref in page_indices:
            idx, column = ref if isinstance(ref, tuple) else (ref, "full")
            if idx >= len(pdf.pages):
                continue
            page = pdf.pages[idx]
            if column == "left":
                page = page.crop((0, 0, page.width / 2, page.height))
            elif column == "right":
                page = page.crop((page.width / 2, 0, page.width, page.height))

            # pdfplumber's extract_tables() is unreliable on cropped half-pages
            # (seen on Maruti's column-split BS: it dropped the entire label
            # column, keeping only "Page No." and the value column). Skip
            # straight to the text fallback for those; full pages still try
            # extract_tables() first since it's usually more accurate there.
            cleaned: list[list[list[str]]] = []
            if column == "full":
                tables = page.extract_tables() or []
                cleaned = [_clean_table(t) for t in tables if t]
                cleaned = [t for t in cleaned if t]

            is_corrupted = cleaned and (
                _has_duplication_artifacts(cleaned)
                or _has_merged_row_artifacts(cleaned)
                or _has_merged_label_artifacts(cleaned)
                or _has_blank_label_artifacts(cleaned)
                or _has_single_column_artifacts(cleaned)
            )
            if cleaned and not is_corrupted:
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

# A single numeric token: comma-grouped (162,990 or 1,62,990), plain (416),
# parenthesised for negative (12,345) or (848), with an optional decimal
# suffix (29,270.69 — Asian Paints reports to 2 decimal places, unlike
# Infosys/TCS/Maruti which round to whole crores). The decimal suffix MUST
# be part of the same token: without "(?:\.\d+)?" here, "29,270.69" matches
# only "29,270" and the ".69" becomes a second, spurious token ("69"),
# corrupting which two tokens get picked as the year-column values.
# One regex for everything — see _text_to_table for why a single unified
# pass beats separate "comma vs plain" paths.
_NUM_TOKEN_RE = re.compile(r'\(?-?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?')

# Cosmetic only: strips a trailing decimal-style note ref from a label after
# slicing, so "Other:" rows don't show leftover digits.
_NOTE_REF_RE = re.compile(r'\s+\d{1,2}\.\d{1,2}\s*$')


def _text_to_table(text: str) -> list[list[str]]:
    """
    Parse raw page text into a financial table.

    Finds ALL numeric tokens on a line and takes the LAST one or two as the
    year-column values — financial statements always show the current/prior
    year as the rightmost columns, whatever comes before (note references,
    in any format: Infosys's "2.18", TCS's "16" or "15(a)") is label text.

    This single pass replaces what used to be two separate paths (comma-only,
    then a plain-integer fallback) after a bug surfaced on TCS's PDF: a row
    with one comma value and one small plain value — e.g.
    "Net change in cash and cash equivalents (848) 1,828" — has exactly one
    comma-formatted number, so the old comma-only path treated "(848)" as
    part of the label and only captured "1,828", silently dropping the
    current-year figure. Taking the last two tokens by position, regardless
    of which format each one uses, fixes this and is simpler than maintaining
    two diverging code paths.

    An earlier version pre-stripped decimal-shaped note refs ("2.18") before
    tokenizing, to stop a lone note ref from being mistaken for a value. That
    broke on Asian Paints, which reports to 2 decimal places: a real value
    like "95.92" (Share Capital) has the exact same shape as a note ref and
    got stripped too. Removed — the magnitude >= 100 guard on single-token
    rows below already rejects small note-ref-like numbers, without needing
    to special-case their format.
    """
    rows: list[list[str]] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        matches = [m for m in _NUM_TOKEN_RE.finditer(line) if any(c.isdigit() for c in m.group())]

        def make_row(val_matches: list[re.Match]) -> list[str]:
            label = line[: val_matches[0].start()].strip()
            label = _NOTE_REF_RE.sub("", label).strip()
            return [label] + [m.group() for m in val_matches]

        def magnitude(token: str) -> float:
            try:
                return abs(float(token.strip("()").replace(",", "")))
            except ValueError:
                return 0.0

        if len(matches) >= 2:
            rows.append(make_row(matches[-2:]))
        elif len(matches) == 1 and magnitude(matches[0].group()) >= 100:
            # Single number with value >= 100 — large enough to be a real
            # financial figure, not a stray note-reference number. A header
            # line like "Trade Receivables" can have its OWN note ref ("10")
            # land on its own line with no real value beside it (the actual
            # figures appear on a separate following row); without this
            # threshold, "10" gets treated as the value and blocks the
            # correct row from matching afterward.
            rows.append(make_row(matches[-1:]))
        else:
            # No usable numbers — section header or label-only row.
            rows.append([line])

    return rows
