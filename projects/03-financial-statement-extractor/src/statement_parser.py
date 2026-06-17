"""
statement_parser.py
Identifies the correct financial statement table from raw pdfplumber output
and normalises row labels to the standard schema.
"""

from __future__ import annotations

import re

from schema import (
    BS_SYNONYMS,
    CF_SYNONYMS,
    PNL_SYNONYMS,
)

SYNONYMS_MAP = {
    "pnl": PNL_SYNONYMS,
    "bs":  BS_SYNONYMS,
    "cf":  CF_SYNONYMS,
}

# ── Year detection ────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"20\d{2}")


def _extract_year_label(header_cell: str) -> str:
    """Pull a 4-digit year from a header string; fallback to the raw text."""
    m = _YEAR_RE.search(header_cell)
    if m:
        return m.group()
    cleaned = header_cell.strip()
    return cleaned if cleaned else "Year"


# ── Number cleaning ───────────────────────────────────────────────────────────

def _parse_number(raw: str) -> float | None:
    """
    Convert a raw cell string to float.
    Handles: commas, parentheses for negatives, trailing notes/footnotes.
    Returns None for blank or non-numeric cells.
    """
    if not raw:
        return None
    s = raw.strip()
    # Remove common footnote markers (single letters/digits at end)
    s = re.sub(r"\s+[a-zA-Z]$", "", s)
    # Parentheses = negative
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    # Remove commas and spaces
    s = s.replace(",", "").replace(" ", "")
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


# ── Table identification ──────────────────────────────────────────────────────

def _count_numeric_columns(table: list[list[str]]) -> int:
    """Count columns (excluding first) that contain mostly numeric values."""
    if len(table) < 2:
        return 0
    n_cols = max(len(row) for row in table)
    numeric_cols = 0
    for col_idx in range(1, n_cols):
        numeric_cells = 0
        total_cells = 0
        for row in table[1:]:
            if col_idx < len(row) and row[col_idx]:
                total_cells += 1
                if _parse_number(row[col_idx]) is not None:
                    numeric_cells += 1
        if total_cells > 0 and numeric_cells / total_cells >= 0.4:
            numeric_cols += 1
    return numeric_cols


def _table_score(table: list[list[str]], stmt_type: str) -> int:
    """
    Score a table for likelihood of being the target financial statement.
    Higher is better.
    """
    if len(table) < 4:
        return 0

    score = 0
    synonyms = SYNONYMS_MAP[stmt_type]
    all_keywords = [kw for kws in synonyms.values() for kw in kws]

    # Row count bonus
    score += min(len(table), 30)

    # Keyword match bonus
    for row in table:
        label = row[0].lower() if row else ""
        if any(kw in label for kw in all_keywords):
            score += 3

    # Numeric column bonus
    score += _count_numeric_columns(table) * 5

    return score


def identify_statement_table(
    raw_tables: list[list[list[str]]],
    stmt_type: str,
) -> list[list[str]] | None:
    """
    Merge all qualifying tables into one.
    Financial statements often span multiple pages — merging captures all rows
    (assets + liabilities on BS, top + bottom of PnL, full CF statement).
    """
    if not raw_tables:
        return None

    # Score every table
    scored = [(t, _table_score(t, stmt_type)) for t in raw_tables]

    # Use the max score as a baseline; keep tables within 40% of it
    max_score = max(s for _, s in scored) if scored else 0

    qualifying = [
        t for t, s in scored
        if s >= max(5, max_score * 0.4) and _count_numeric_columns(t) >= 1
    ]

    if not qualifying:
        # Fall back: just use the single highest-scoring table
        best = max(raw_tables, key=lambda t: _table_score(t, stmt_type))
        return best if _count_numeric_columns(best) >= 1 else None

    # Merge all qualifying tables — preserves page order since extract_tables_from_pages
    # processes pages in order
    merged: list[list[str]] = []
    for table in qualifying:
        merged.extend(table)

    return merged


# ── Normalisation ─────────────────────────────────────────────────────────────

def _match_label(label: str, stmt_type: str) -> str | None:
    """Match a raw row label to a standard line item. Returns None if no match."""
    label_lower = label.lower()
    synonyms = SYNONYMS_MAP[stmt_type]
    for standard_label, keywords in synonyms.items():
        if any(kw in label_lower for kw in keywords):
            return standard_label
    return None


def normalize_table(
    raw_table: list[list[str]],
    stmt_type: str,
    year_label: str = "",
) -> dict[str, float | None]:
    """
    Convert a raw pdfplumber table into {standard_line_item: value}.

    - Extracts the first numeric column as the current year's values.
    - year_label is prepended to "Other" rows to help identify them.
    - Returns a flat dict suitable for building a DataFrame column.
    """
    if not raw_table:
        return {}

    result: dict[str, float | None] = {}
    other_counter = 1

    # Find first column index that has numeric data
    n_cols = max(len(row) for row in raw_table)
    value_col = None
    for col_idx in range(1, n_cols):
        numeric = sum(
            1 for row in raw_table[1:]
            if col_idx < len(row) and _parse_number(row[col_idx]) is not None
        )
        if numeric >= 2:
            value_col = col_idx
            break

    if value_col is None:
        return {}

    for row in raw_table:
        if not row or not row[0]:
            continue
        raw_label = row[0].strip()
        if not raw_label:
            continue

        # Skip header rows (all-caps short strings, or year-like)
        if _YEAR_RE.search(raw_label) and len(raw_label) < 15:
            continue

        value = _parse_number(row[value_col]) if value_col < len(row) else None

        standard = _match_label(raw_label, stmt_type)
        if standard:
            # Only record if value is non-None and key not already set.
            # Skipping None prevents section headers (no value) from blocking
            # the actual total row that appears later with a real number.
            if standard not in result and value is not None:
                result[standard] = value
        else:
            # Keep unmatched rows under "Other" with a counter
            if value is not None:
                result[f"Other: {raw_label[:50]}"] = value

    return result


# ── Multi-PDF stitching ───────────────────────────────────────────────────────

def stitch_years(
    per_year_data: list[tuple[str, dict[str, float | None]]],
    stmt_type: str,
) -> dict[str, dict[str, float | None]]:
    """
    Combine per-year dicts into a single dict keyed by standard line item.
    per_year_data: [(year_label, {line_item: value}), ...]
    Returns: {line_item: {year_label: value, ...}}
    """
    from schema import PNL_ITEMS, BS_ITEMS, CF_ITEMS
    ordered_items = {"pnl": PNL_ITEMS, "bs": BS_ITEMS, "cf": CF_ITEMS}[stmt_type]

    # Collect all line items seen across all years
    all_items: list[str] = list(ordered_items)  # standard items first
    for _, data in per_year_data:
        for item in data:
            if item not in all_items:
                all_items.append(item)

    result: dict[str, dict[str, float | None]] = {}
    for item in all_items:
        result[item] = {}
        for year_label, data in per_year_data:
            result[item][year_label] = data.get(item)

    # Drop rows that are all None
    result = {
        item: years
        for item, years in result.items()
        if any(v is not None for v in years.values())
    }

    return result
