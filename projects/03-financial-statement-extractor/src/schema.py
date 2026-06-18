"""
schema.py
Standard line items and keyword synonym maps for P&L, Balance Sheet, Cash Flow.
"""

from __future__ import annotations

# ── Standard line items (display order) ──────────────────────────────────────

PNL_ITEMS = [
    "Revenue",
    "Cost of Revenue",
    "Gross Profit",
    "Other Operating Expenses",
    "EBITDA",
    "Depreciation & Amortization",
    "EBIT",
    "Interest Expense",
    "Other Income / Expense",
    "Profit Before Tax",
    "Tax",
    "Net Profit",
    "EPS (Basic)",
]

BS_ITEMS = [
    "Cash & Equivalents",
    "Inventories",
    "Trade Receivables",
    "Other Current Assets",
    "Current Assets",
    "Property, Plant & Equipment",
    "Goodwill & Intangibles",
    "Other Non-Current Assets",
    "Non-Current Assets",
    "Total Assets",
    "Trade Payables",
    "Short-term Borrowings",
    "Other Current Liabilities",
    "Current Liabilities",
    "Long-term Borrowings",
    "Other Non-Current Liabilities",
    "Non-Current Liabilities",
    "Total Liabilities",
    "Share Capital",
    "Retained Earnings / Reserves",
    "Total Equity",
]

CF_ITEMS = [
    "Operating Cash Flow",
    "Investing Cash Flow",
    "Financing Cash Flow",
    "Net Change in Cash",
    "Opening Cash Balance",
    "Closing Cash Balance",
]

# ── Keyword synonyms for row label matching ───────────────────────────────────
# Each key is the standard label; values are substrings to match (lowercase).

PNL_SYNONYMS: dict[str, list[str]] = {
    "Revenue": [
        "revenue from operations",
        "net revenue",
        "total revenue",
        "net sales",
        "total income from operations",
        "revenue from contract",
        "gross revenue",
        "total net revenue",
        "sales and services",
        "income from operations",
        "revenue from sale of products",  # Asian Paints: no combined "revenue
        "revenue from sale of goods",     # from operations" subtotal line —
                                           # products/services/other are shown
                                           # separately, so the products line
                                           # (the dominant figure) is used.
    ],
    "Cost of Revenue": [
        "cost of goods sold",
        "cost of revenue",
        "cost of sales",
        "cost of materials",
        "cost of products",
        "direct costs",
        "cost of services",
        "purchases of stock-in-trade",
    ],
    "Gross Profit": [
        "gross profit",
        "gross margin",
    ],
    "Other Operating Expenses": [
        "selling general and administrative",
        "sg&a",
        "operating expenses",
        "employee benefit",
        "staff costs",
        "selling and distribution",
        "research and development",
        "r&d",
    ],
    "EBITDA": [
        "ebitda",
        "earnings before interest tax depreciation",
    ],
    "Depreciation & Amortization": [
        "depreciation",
        "amortization",
        "depreciation and amortization",
        "d&a",
    ],
    "EBIT": [
        "ebit",
        "operating profit",
        "profit from operations",
        "earnings before interest and tax",
        "income from operations",
    ],
    "Interest Expense": [
        "interest expense",
        "finance costs",
        "finance cost",
        "interest cost",
        "interest charges",
        "borrowing costs",
        "interest on borrowings",
    ],
    "Other Income / Expense": [
        "other income",
        "other expense",
        "exceptional items",
        "extraordinary items",
        "non-operating",
    ],
    "Profit Before Tax": [
        "profit before tax",
        "income before tax",
        "earnings before tax",
        "pbt",
        "profit/(loss) before tax",
        "profit before income tax",
        "income before income taxes",
        "profit before exceptional",
    ],
    "Tax": [
        "tax expense",
        "income tax expense",
        "income tax",
        "provision for tax",
        "current tax",
        "total tax expense",
        "tax on income",
    ],
    "Net Profit": [
        "net profit",
        "profit after tax",
        "net income",
        "profit for the year",
        "profit/(loss) for",
        "pat",
        "net earnings",
        "profit for the period",
        "total profit for the year",
    ],
    "EPS (Basic)": [
        "basic earnings per share",
        "basic eps",
        "earnings per equity share",
        "earnings per share - basic",
        "basic net earnings per share",
    ],
}

BS_SYNONYMS: dict[str, list[str]] = {
    "Cash & Equivalents": [
        "cash and cash equivalents",
        "cash and bank",
        "cash equivalents",
        "bank balances",
    ],
    "Inventories": [
        "inventories",
        "inventory",
        "stock-in-trade",
        "raw materials",
    ],
    "Trade Receivables": [
        "trade receivables",
        "accounts receivable",
        "debtors",
        "trade and other receivables",
    ],
    "Other Current Assets": [
        "other current assets",
        "prepaid",
        "advance",
        "short-term loans",
    ],
    "Current Assets": [
        "total current assets",
        "current assets",
    ],
    "Property, Plant & Equipment": [
        "property, plant and equipment",     # with comma (standard Indian AR format)
        "property plant and equipment",      # without comma (US/other formats)
        "ppe",
        "tangible assets",
        "fixed assets",
        "right-of-use",
    ],
    "Goodwill & Intangibles": [
        "goodwill",
        "intangible assets",
        "intangibles",
    ],
    "Other Non-Current Assets": [
        "other non-current assets",
        "long-term investments",
        "deferred tax assets",
        "capital work-in-progress",
    ],
    "Non-Current Assets": [
        "total non-current assets",
        "non-current assets",
    ],
    "Total Assets": [
        "total assets",
        "total equity and liabilities",
        "total non-current assets and current assets",
    ],
    "Current Assets": [
        "total current assets",
        # "current assets" removed — it's a substring of "non-current assets"
        # and would cause false matches on non-current asset line items.
    ],
    "Trade Payables": [
        "trade payables",
        "accounts payable",
        "creditors",
        "trade and other payables",
    ],
    "Short-term Borrowings": [
        "short-term borrowings",
        "current portion of long-term",
        "short term debt",
    ],
    "Other Current Liabilities": [
        "other current liabilities",
        "accrued liabilities",
        "provisions",
        "current tax liabilities",
    ],
    "Current Liabilities": [
        "total current liabilities",
        # "current liabilities" removed — substring of "non-current liabilities".
    ],
    "Long-term Borrowings": [
        "long-term borrowings",
        "long term debt",
        "non-current borrowings",
        "long-term debt",
    ],
    "Other Non-Current Liabilities": [
        "other non-current liabilities",
        "deferred tax liabilities",
        "long-term provisions",
    ],
    "Non-Current Liabilities": [
        "total non-current liabilities",
        "non-current liabilities",
    ],
    "Total Liabilities": [
        "total liabilities",
    ],
    "Share Capital": [
        "share capital",
        "common stock",
        "equity share capital",
        "paid-up capital",
    ],
    "Retained Earnings / Reserves": [
        "retained earnings",
        "reserves and surplus",
        "other equity",
        "accumulated deficit",
        "other comprehensive income",
    ],
    "Total Equity": [
        "total equity",
        "shareholders equity",
        "stockholders equity",
        "total shareholders",
        "net worth",
    ],
}

CF_SYNONYMS: dict[str, list[str]] = {
    "Operating Cash Flow": [
        "net cash generated from operating",
        "net cash generated by operating",        # Infosys phrasing: "by" not "from"
        "net cash from operating",                 # Maruti: "Net Cash from Operating Activities"
        "net cash used in operating",
        "net cash provided by operating",
        "net cash inflow from operating",
        "net cash flows generated from operating", # TCS: "Net cash flows generated from..."
        "net cash flows from operating",
        "net cash flows used in operating",
        "net cash flow from/(used in) operating",  # ICICI's exact phrasing
        "net cash flow from/ (used in) operating", # Kotak: space after the slash
        "net cash flow used in operating",
        # Deliberately NOT matching bare "operating activities" or "cash
        # generated from operating" (without "net"): Indian CF statements
        # using the indirect method show a PRE-TAX subtotal first — e.g.
        # Maruti's "Cash generated from Operating Activities" (177,942) —
        # followed by the real total "Net Cash from Operating Activities"
        # (140,124, after tax). A synonym without "net" matches the wrong,
        # earlier row. Every real total line starts with "net cash".
    ],
    "Investing Cash Flow": [
        "net cash generated from investing",
        "net cash used in investing",
        "net cash from investing",
        "cash used in investing",
        "net cash inflow from investing",
        "investing activities",              # catches "used in from investing" PDF artifact
    ],
    "Financing Cash Flow": [
        "net cash generated from financing",
        "net cash used in financing",
        "net cash from financing",
        "cash from financing",
        "net cash inflow from financing",
        "financing activities",
    ],
    "Net Change in Cash": [
        "net increase",
        "net decrease",
        "net change in cash",
        "increase in cash",
        "decrease in cash",
        "net increase/(decrease)",
    ],
    "Opening Cash Balance": [
        "opening cash",
        "cash at beginning",
        "cash and cash equivalents at the beginning",
        "cash and cash equivalents at beginning",
        "balance at beginning",
        "at the beginning of the year",
        "cash and cash equivalents as at 1st april",  # Asian Paints phrasing
    ],
    "Closing Cash Balance": [
        "closing cash",
        "cash at end",
        "cash and cash equivalents at the end",
        "cash and cash equivalents at end",
        "balance at end",
        "at the end of the year",
        "cash and cash equivalents as at 31st march",  # Asian Paints phrasing
    ],
}

# ── Page search keywords (used to locate statement pages in PDF) ──────────────

PAGE_KEYWORDS = {
    "pnl": [
        "statement of profit and loss",
        "profit and loss account",
        "income statement",
        "statement of operations",
        "statement of income",
        "consolidated statement of profit",
        "standalone statement of profit",
    ],
    "bs": [
        "balance sheet",
        "statement of financial position",
        "consolidated balance sheet",
        "standalone balance sheet",
    ],
    "cf": [
        "cash flow statement",
        "statement of cash flows",
        "consolidated cash flow",
        "standalone cash flow",
    ],
}

# ── Bank-specific schema (Banking Regulation Act, 1949 — Third Schedule) ──────
# Banks don't have Trade Receivables, Inventories, or a Current/Non-Current
# split — their Balance Sheet is "Capital and Liabilities" vs "Assets" with
# items like Deposits and Advances, and the P&L is called a "Profit and Loss
# Account" with Income/Expenditure sections. Detected via _is_bank_statement()
# in statement_parser.py and routed to this schema instead of the default one.

BANK_PNL_ITEMS = [
    "Interest Earned",
    "Other Income",
    "Total Income",
    "Interest Expended",
    "Operating Expenses",
    "Provisions and Contingencies",
    "Total Expenditure",
    "Net Profit",
]

BANK_BS_ITEMS = [
    "Capital",
    "Reserves and Surplus",
    "Deposits",
    "Borrowings",
    "Other Liabilities and Provisions",
    "Total Capital and Liabilities",
    "Cash and Balances with RBI",
    "Balances with Banks and Money at Call",
    "Investments",
    "Advances",
    "Fixed Assets",
    "Other Assets",
    "Total Assets",
]

BANK_PNL_SYNONYMS: dict[str, list[str]] = {
    "Interest Earned": ["interest earned"],
    "Other Income": ["other income"],
    "Interest Expended": ["interest expended"],
    "Operating Expenses": ["operating expenses"],
    "Provisions and Contingencies": ["provisions and contingencies"],
    "Net Profit": [
        "net profit for the year attributable",
        "net profit for the year",
        "net profit/(loss) for the",   # ICICI: "Net profit/(loss) for the period/year"
        "profit for the year",
    ],
    # Some banks label these explicitly (ICICI: "TOTAL INCOME"); others use
    # a bare "Total" with nothing else to tell Income from Expenditure
    # (HDFC). Explicit synonyms here catch the former; the latter is
    # resolved positionally via BANK_SECTION_MAP in statement_parser.py,
    # which tracks whether we're currently under "I INCOME" or
    # "II EXPENDITURE" and assigns the next bare "Total" row accordingly.
    "Total Income": ["total income"],
    "Total Expenditure": ["total expenditure"],
}

BANK_BS_SYNONYMS: dict[str, list[str]] = {
    # "Total Capital and Liabilities" / "Total Assets" MUST be checked
    # before "Capital" — "capital" is trivially a substring of "total
    # capital and liabilities", and _match_label returns on the first dict
    # entry that matches, so the broader single-word synonym would win if
    # it came first. Some banks label these totals explicitly (ICICI:
    # "TOTAL CAPITAL AND LIABILITIES" / "TOTAL ASSETS"); others use a bare
    # "Total" for both sides of the Balance Sheet (HDFC), resolved
    # positionally via BANK_SECTION_MAP in statement_parser.py instead.
    "Total Capital and Liabilities": ["total capital and liabilities"],
    "Total Assets": ["total assets"],
    "Capital": ["capital"],
    "Reserves and Surplus": ["reserves and surplus"],
    "Deposits": ["deposits"],
    "Borrowings": ["borrowings"],
    "Other Liabilities and Provisions": ["other liabilities and provisions"],
    "Cash and Balances with RBI": [
        "cash and balances with reserve bank of india",
    ],
    "Balances with Banks and Money at Call": [
        "balances with banks and money at call",
    ],
    "Investments": ["investments"],
    "Advances": ["advances"],
    "Fixed Assets": ["fixed assets"],
    "Other Assets": ["other assets"],
}

# Maps a section-header line (lowercased) to the standard item that the next
# bare "Total" row belongs to. Order matters only in that a later section
# header overwrites the current one — rows are processed top-to-bottom.
BANK_SECTION_MAP: dict[str, dict[str, str]] = {
    "pnl": {
        "i income": "Total Income",
        "ii expenditure": "Total Expenditure",
    },
    "bs": {
        "capital and liabilities": "Total Capital and Liabilities",
        "assets": "Total Assets",
    },
}

# Strong signals that a statement page uses the bank format, not the
# standard one — checked against the page's raw text.
BANK_FORMAT_SIGNALS = {
    "pnl": ["interest earned", "interest expended"],
    "bs": ["capital and liabilities"],
}
