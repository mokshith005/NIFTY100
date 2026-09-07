"""
Sprint 5 - Day 33
Company Tearsheet Generator

Generates 2-page company tearsheets for:
TCS, HDFCBANK, RELIANCE, SUNPHARMA, TATASTEEL
"""

from pathlib import Path
import sqlite3
import math
import os
import tempfile

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output" / "tearsheets"

PROS_CONS_PATH = ROOT / "output" / "pros_cons_generated.csv"
CAPITAL_ALLOCATION_PATH = ROOT / "output" / "capital_allocation.csv"


# ============================================================================
# COLORS
# ============================================================================

NAVY = colors.HexColor("#0B1F3A")
LIGHT_BLUE = colors.HexColor("#EAF1F8")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
MID_GRAY = colors.HexColor("#D9DEE5")
DARK_GRAY = colors.HexColor("#444444")

GREEN = colors.HexColor("#16803C")
RED = colors.HexColor("#B42318")

WHITE = colors.white


PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN_LEFT = 14 * mm
MARGIN_RIGHT = 14 * mm
MARGIN_TOP = 25 * mm
MARGIN_BOTTOM = 15 * mm


# ============================================================================
# STYLES
# ============================================================================

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TearsheetTitle",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=19,
    leading=22,
    textColor=NAVY,
    spaceAfter=4,
)

SUBTITLE_STYLE = ParagraphStyle(
    "TearsheetSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=DARK_GRAY,
)

SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    textColor=NAVY,
    spaceBefore=5,
    spaceAfter=5,
)

BODY_STYLE = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7.8,
    leading=10,
    textColor=DARK_GRAY,
)

SMALL_STYLE = ParagraphStyle(
    "Small",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=6.8,
    leading=8.5,
    textColor=DARK_GRAY,
)

TABLE_STYLE = ParagraphStyle(
    "Table",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=7,
    leading=8.5,
    textColor=DARK_GRAY,
)

TABLE_HEADER_STYLE = ParagraphStyle(
    "TableHeader",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=7,
    leading=8.5,
    textColor=WHITE,
)

GOOD_STYLE = ParagraphStyle(
    "Good",
    parent=BODY_STYLE,
    textColor=GREEN,
)

BAD_STYLE = ParagraphStyle(
    "Bad",
    parent=BODY_STYLE,
    textColor=RED,
)


# ============================================================================
# HELPERS
# ============================================================================

def safe_float(value):
    try:
        if value is None:
            return None

        if isinstance(value, str):
            value = (
                value
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

        if value in ("", "-", "NA", "N/A", "None", "nan"):
            return None

        result = float(value)

        if math.isnan(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def fmt_number(value, decimals=1):
    value = safe_float(value)

    if value is None:
        return "N/A"

    if abs(value) >= 1000:
        return f"{value:,.0f}"

    return f"{value:,.{decimals}f}"


def fmt_pct(value, decimals=1):
    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}%"


def first_existing(columns, candidates):
    lookup = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def latest_row(df):
    if df is None or df.empty:
        return None

    if "year" not in df.columns:
        return df.iloc[-1]

    temp = df.copy()

    temp["_year_num"] = pd.to_numeric(
        temp["year"],
        errors="coerce",
    )

    temp = temp.sort_values("_year_num")

    return temp.iloc[-1]


# ============================================================================
# DATABASE
# ============================================================================

class Database:

    def __init__(self, path):
        self.path = path

    def connect(self):
        return sqlite3.connect(self.path)

    def query(self, sql, params=()):
        """
        Execute parameterized SQL query.

        IMPORTANT:
        params MUST be passed to pandas so SQLite can bind '?' values.
        """
        with self.connect() as conn:
            return pd.read_sql_query(
                sql,
                conn,
                params=params,
            )


# ============================================================================
# LOAD DATABASE DATA
# ============================================================================

def load_company(db, company_id):

    return db.query(
        """
        SELECT *
        FROM companies
        WHERE id = ?
        """,
        (company_id,),
    )


def load_profit_loss(db, company_id):

    return db.query(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        """,
        (company_id,),
    )


def load_balance_sheet(db, company_id):

    return db.query(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        """,
        (company_id,),
    )


def load_cash_flow(db, company_id):

    return db.query(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        """,
        (company_id,),
    )


def load_ratios(db, company_id):

    return db.query(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        """,
        (company_id,),
    )


# ============================================================================
# PROS / CONS
# ============================================================================

def load_pros_cons(company_id):

    if not PROS_CONS_PATH.exists():
        return [], []

    try:
        df = pd.read_csv(PROS_CONS_PATH)
    except Exception:
        return [], []

    company_col = first_existing(
        df.columns,
        [
            "company_id",
            "id",
            "ticker",
        ],
    )

    if company_col is None:
        return [], []

    temp = df[
        df[company_col]
        .astype(str)
        .str.upper()
        == str(company_id).upper()
    ].copy()

    if temp.empty:
        return [], []

    type_col = first_existing(
        temp.columns,
        [
            "signal_type",
            "type",
            "category",
            "kind",
        ],
    )

    text_col = first_existing(
        temp.columns,
        [
            "signal",
            "text",
            "description",
            "reason",
            "message",
            "rule",
        ],
    )

    confidence_col = first_existing(
        temp.columns,
        [
            "confidence",
            "confidence_score",
        ],
    )

    if text_col is None:
        return [], []

    pros = []
    cons = []

    for _, row in temp.iterrows():

        text = clean_text(
            row.get(text_col)
        )

        if not text:
            continue

        kind = ""

        if type_col:
            kind = clean_text(
                row.get(type_col)
            ).lower()

        confidence = None

        if confidence_col:
            confidence = safe_float(
                row.get(confidence_col)
            )

        if confidence is not None:
            text = f"{text} ({confidence:.0f}%)"

        if "pro" in kind:
            pros.append(text)

        elif "con" in kind:
            cons.append(text)

        else:
            positive_words = [
                "strong",
                "growth",
                "healthy",
                "improved",
                "positive",
                "high",
                "good",
                "efficient",
            ]

            if any(
                word in text.lower()
                for word in positive_words
            ):
                pros.append(text)
            else:
                cons.append(text)

    return pros[:6], cons[:6]


# ============================================================================
# CAPITAL ALLOCATION
# ============================================================================

def load_capital_allocation(company_id):

    if not CAPITAL_ALLOCATION_PATH.exists():
        return "N/A"

    try:
        df = pd.read_csv(
            CAPITAL_ALLOCATION_PATH
        )
    except Exception:
        return "N/A"

    company_col = first_existing(
        df.columns,
        [
            "company_id",
            "id",
            "ticker",
        ],
    )

    if company_col is None:
        return "N/A"

    temp = df[
        df[company_col]
        .astype(str)
        .str.upper()
        == str(company_id).upper()
    ].copy()

    if temp.empty:
        return "N/A"

    pattern_col = first_existing(
        temp.columns,
        [
            "pattern_label",
            "pattern",
            "capital_allocation",
        ],
    )

    if pattern_col is None:
        return "N/A"

    year_col = first_existing(
        temp.columns,
        [
            "year",
            "financial_year",
        ],
    )

    if year_col:

        temp["_year_num"] = pd.to_numeric(
            temp[year_col],
            errors="coerce",
        )

        temp = temp.sort_values(
            "_year_num"
        )

    result = clean_text(
        temp.iloc[-1][pattern_col]
    )

    return result or "N/A"


# ============================================================================
# KPI EXTRACTION
# ============================================================================

def get_latest_kpis(pl, ratios):

    latest_pl = latest_row(pl)
    latest_ratio = latest_row(ratios)

    def ratio_value(candidates):

        if latest_ratio is None:
            return None

        col = first_existing(
            latest_ratio.index,
            candidates,
        )

        if col is None:
            return None

        return safe_float(
            latest_ratio.get(col)
        )

    def pl_value(candidates):

        if latest_pl is None:
            return None

        col = first_existing(
            latest_pl.index,
            candidates,
        )

        if col is None:
            return None

        return safe_float(
            latest_pl.get(col)
        )

    revenue = pl_value(
        [
            "sales",
            "revenue",
            "total_revenue",
        ]
    )

    net_profit = pl_value(
        [
            "net_profit",
            "profit_after_tax",
            "pat",
        ]
    )

    roe = ratio_value(
        [
            "return_on_equity_pct",
            "roe_pct",
            "roe",
        ]
    )

    roce = ratio_value(
        [
            "roce_pct",
            "roce_percentage",
            "roce",
        ]
    )

    debt_equity = ratio_value(
        [
            "debt_to_equity",
            "debt_equity",
        ]
    )

    fcf = ratio_value(
        [
            "free_cash_flow_cr",
            "free_cash_flow",
            "fcf",
        ]
    )

    return {
        "Revenue": revenue,
        "Net Profit": net_profit,
        "ROE": roe,
        "ROCE": roce,
        "Debt/Equity": debt_equity,
        "Free Cash Flow": fcf,
    }


# ============================================================================
# TREND DATA
# ============================================================================

def build_profit_trend(pl):

    if pl is None or pl.empty:
        return []

    year_col = first_existing(
        pl.columns,
        [
            "year",
            "financial_year",
        ],
    )

    revenue_col = first_existing(
        pl.columns,
        [
            "sales",
            "revenue",
            "total_revenue",
        ],
    )

    profit_col = first_existing(
        pl.columns,
        [
            "net_profit",
            "profit_after_tax",
            "pat",
        ],
    )

    if year_col is None:
        return []

    temp = pl.copy()

    temp["_year_num"] = pd.to_numeric(
        temp[year_col],
        errors="coerce",
    )

    temp = (
        temp
        .sort_values("_year_num")
        .tail(5)
    )

    rows = []

    for _, row in temp.iterrows():

        rows.append(
            {
                "year": clean_text(
                    row.get(year_col)
                ),
                "revenue": (
                    safe_float(
                        row.get(revenue_col)
                    )
                    if revenue_col
                    else None
                ),
                "profit": (
                    safe_float(
                        row.get(profit_col)
                    )
                    if profit_col
                    else None
                ),
            }
        )

    return rows


def build_roe_roce_trend(ratios):

    if ratios is None or ratios.empty:
        return []

    year_col = first_existing(
        ratios.columns,
        [
            "year",
            "financial_year",
        ],
    )

    roe_col = first_existing(
        ratios.columns,
        [
            "return_on_equity_pct",
            "roe_pct",
            "roe",
        ],
    )

    roce_col = first_existing(
        ratios.columns,
        [
            "roce_pct",
            "roce_percentage",
            "roce",
        ],
    )

    if year_col is None:
        return []

    temp = ratios.copy()

    temp["_year_num"] = pd.to_numeric(
        temp[year_col],
        errors="coerce",
    )

    temp = (
        temp
        .sort_values("_year_num")
        .tail(5)
    )

    rows = []

    for _, row in temp.iterrows():

        rows.append(
            {
                "year": clean_text(
                    row.get(year_col)
                ),
                "roe": (
                    safe_float(
                        row.get(roe_col)
                    )
                    if roe_col
                    else None
                ),
                "roce": (
                    safe_float(
                        row.get(roce_col)
                    )
                    if roce_col
                    else None
                ),
            }
        )

    return rows


# ============================================================================
# BALANCE SHEET
# ============================================================================

def build_balance_snapshot(bs):

    if bs is None or bs.empty:
        return []

    latest = latest_row(bs)

    if latest is None:
        return []

    mapping = [
        (
            "Total Assets",
            [
                "total_assets",
                "assets",
                "total_asset",
            ],
        ),
        (
            "Total Liabilities",
            [
                "total_liabilities",
                "liabilities",
                "total_liability",
            ],
        ),
        (
            "Borrowings",
            [
                "borrowings",
                "total_borrowings",
                "debt",
            ],
        ),
        (
            "Cash",
            [
                "cash",
                "cash_and_bank",
                "cash_equivalents",
            ],
        ),
        (
            "Net Worth",
            [
                "net_worth",
                "networth",
                "shareholders_funds",
                "equity",
            ],
        ),
    ]

    result = []

    for label, candidates in mapping:

        col = first_existing(
            latest.index,
            candidates,
        )

        value = (
            safe_float(
                latest.get(col)
            )
            if col
            else None
        )

        result.append(
            [
                label,
                fmt_number(value),
            ]
        )

    return result


# ============================================================================
# CASH FLOW
# ============================================================================

def build_cashflow_snapshot(cf):

    if cf is None or cf.empty:
        return []

    latest = latest_row(cf)

    if latest is None:
        return []

    mapping = [
        (
            "Operating Cash Flow",
            [
                "operating_activity",
                "cfo",
                "cash_from_operations",
            ],
        ),
        (
            "Investing Cash Flow",
            [
                "investing_activity",
                "cfi",
                "cash_from_investing",
            ],
        ),
        (
            "Financing Cash Flow",
            [
                "financing_activity",
                "cff",
                "cash_from_financing",
            ],
        ),
        (
            "Net Cash Flow",
            [
                "net_cash_flow",
                "net_cash",
            ],
        ),
    ]

    result = []

    for label, candidates in mapping:

        col = first_existing(
            latest.index,
            candidates,
        )

        value = (
            safe_float(
                latest.get(col)
            )
            if col
            else None
        )

        result.append(
            [
                label,
                fmt_number(value),
            ]
        )

    return result



# ============================================================================
# CHARTS
# ============================================================================

def _save_chart(fig, path):
    fig.savefig(
        path,
        dpi=170,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def make_profit_chart(rows, path):
    """Revenue / net profit grouped bar chart for the recent annual trend."""
    valid = [
        r for r in rows
        if r.get("revenue") is not None or r.get("profit") is not None
    ]

    if not valid:
        return False

    years = [str(r["year"]) for r in valid]
    revenue = [
        r["revenue"] if r.get("revenue") is not None else 0
        for r in valid
    ]
    profit = [
        r["profit"] if r.get("profit") is not None else 0
        for r in valid
    ]

    fig, ax = plt.subplots(figsize=(7.0, 2.45))
    x = list(range(len(years)))
    width = 0.36

    ax.bar(
        [i - width / 2 for i in x],
        revenue,
        width,
        label="Revenue",
    )
    ax.bar(
        [i + width / 2 for i in x],
        profit,
        width,
        label="Net Profit",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=7)
    ax.set_ylabel("₹ crore", fontsize=7)
    ax.set_title("Revenue vs Net Profit", fontsize=9, fontweight="bold")
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", alpha=0.20)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()

    _save_chart(fig, path)
    return True


def make_roe_roce_chart(rows, path):
    """Dual-axis ROE / ROCE trend chart."""
    valid = [
        r for r in rows
        if r.get("roe") is not None or r.get("roce") is not None
    ]

    if not valid:
        return False

    years = [str(r["year"]) for r in valid]
    roe = [r.get("roe") for r in valid]
    roce = [r.get("roce") for r in valid]

    fig, ax1 = plt.subplots(figsize=(7.0, 2.45))
    x = list(range(len(years)))

    roe_plot = [v if v is not None else float("nan") for v in roe]
    roce_plot = [v if v is not None else float("nan") for v in roce]

    line1 = ax1.plot(
        x, roe_plot, marker="o", linewidth=1.8, label="ROE"
    )
    ax1.set_ylabel("ROE (%)", fontsize=7)
    ax1.tick_params(axis="y", labelsize=7)
    ax1.tick_params(axis="x", labelsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years)

    ax2 = ax1.twinx()
    line2 = ax2.plot(
        x, roce_plot, marker="s", linewidth=1.8, label="ROCE"
    )
    ax2.set_ylabel("ROCE (%)", fontsize=7)
    ax2.tick_params(axis="y", labelsize=7)

    ax1.set_title(
        "ROE vs ROCE — Dual-Axis Trend",
        fontsize=9,
        fontweight="bold",
    )
    ax1.grid(axis="y", alpha=0.20)

    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, fontsize=7, frameon=False, loc="upper left")

    fig.tight_layout()
    _save_chart(fig, path)
    return True


def build_balance_chart_data(bs):
    """Return numeric balance-sheet components for the latest year."""
    if bs is None or bs.empty:
        return None

    latest = latest_row(bs)
    if latest is None:
        return None

    def val(candidates):
        col = first_existing(latest.index, candidates)
        return safe_float(latest.get(col)) if col else None

    total_assets = val(["total_assets", "assets", "total_asset"])
    cash = val(["cash", "cash_and_bank", "cash_equivalents"])
    borrowings = val(["borrowings", "total_borrowings", "debt"])
    net_worth = val(
        ["net_worth", "networth", "shareholders_funds", "equity"]
    )
    total_liabilities = val(
        ["total_liabilities", "liabilities", "total_liability"]
    )

    if total_assets is None:
        return None

    cash = cash or 0
    borrowings = borrowings or 0
    net_worth = net_worth or 0

    other_assets = max(total_assets - cash, 0)

    if total_liabilities is not None:
        other_liabilities = max(total_liabilities - borrowings, 0)
    else:
        other_liabilities = max(total_assets - borrowings - net_worth, 0)

    return {
        "Cash": cash,
        "Other Assets": other_assets,
        "Borrowings": borrowings,
        "Other Liabilities": other_liabilities,
        "Net Worth": net_worth,
    }


def make_balance_chart(bs, path):
    """Stacked balance-sheet composition chart."""
    data = build_balance_chart_data(bs)
    if not data:
        return False

    fig, ax = plt.subplots(figsize=(7.0, 2.45))

    assets = [data["Cash"], data["Other Assets"]]
    liabilities = [
        data["Borrowings"],
        data["Other Liabilities"],
        data["Net Worth"],
    ]

    bottom = 0
    for value, label in zip(assets, ["Cash", "Other Assets"]):
        ax.bar(0, value, bottom=bottom, width=0.55, label=label)
        bottom += value

    bottom = 0
    for value, label in zip(
        liabilities,
        ["Borrowings", "Other Liabilities", "Net Worth"],
    ):
        ax.bar(1, value, bottom=bottom, width=0.55, label=label)
        bottom += value

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Assets", "Liabilities + Equity"], fontsize=7)
    ax.set_ylabel("₹ crore", fontsize=7)
    ax.set_title(
        "Latest Balance Sheet — Stacked Composition",
        fontsize=9,
        fontweight="bold",
    )
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", alpha=0.20)
    ax.legend(
        fontsize=6.5,
        frameon=False,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
    )
    fig.tight_layout()

    _save_chart(fig, path)
    return True


def build_cashflow_chart_data(cf):
    """Return the latest CFO / CFI / CFF values."""
    if cf is None or cf.empty:
        return None

    latest = latest_row(cf)
    if latest is None:
        return None

    def val(candidates):
        col = first_existing(latest.index, candidates)
        return safe_float(latest.get(col)) if col else None

    cfo = val(["operating_activity", "cfo", "cash_from_operations"])
    cfi = val(["investing_activity", "cfi", "cash_from_investing"])
    cff = val(["financing_activity", "cff", "cash_from_financing"])

    if cfo is None and cfi is None and cff is None:
        return None

    return {
        "CFO": cfo or 0,
        "CFI": cfi or 0,
        "CFF": cff or 0,
    }


def make_cashflow_waterfall(cf, path):
    """Cash-flow waterfall showing CFO, CFI and CFF contributions."""
    data = build_cashflow_chart_data(cf)
    if not data:
        return False

    labels = ["Start", "CFO", "CFI", "CFF", "Net"]
    values = [0, data["CFO"], data["CFI"], data["CFF"]]
    net = sum(values[1:])

    bottoms = [0]
    running = 0
    for value in values[1:]:
        bottoms.append(min(running, running + value))
        running += value

    fig, ax = plt.subplots(figsize=(7.0, 2.45))

    ax.bar(
        range(5),
        [0, data["CFO"], data["CFI"], data["CFF"], net],
        bottom=bottoms + [0],
        width=0.55,
    )

    ax.axhline(0, linewidth=0.8)
    ax.set_xticks(range(5))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("₹ crore", fontsize=7)
    ax.set_title(
        "Cash-Flow Waterfall — Latest Year",
        fontsize=9,
        fontweight="bold",
    )
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", alpha=0.20)

    chart_values = [0, data["CFO"], data["CFI"], data["CFF"], net]
    for i, value in enumerate(chart_values):
        if i == 0:
            continue
        if i == 4:
            y = net
            va = "bottom" if net >= 0 else "top"
        elif value >= 0:
            y = bottoms[i] + value
            va = "bottom"
        else:
            y = bottoms[i]
            va = "top"
        ax.text(
            i,
            y,
            f"{value:,.0f}",
            ha="center",
            va=va,
            fontsize=6.5,
        )

    fig.tight_layout()
    _save_chart(fig, path)
    return True


# ============================================================================
# KPI TILES
# ============================================================================

def make_kpi_tiles(kpis):

    labels = list(kpis.keys())

    rows = []
    current = []

    for label in labels:

        value = kpis[label]

        if label in [
            "ROE",
            "ROCE",
        ]:
            display = fmt_pct(value)

        elif label == "Debt/Equity":
            display = fmt_number(
                value,
                2,
            )

        else:
            display = fmt_number(value)

        content = Paragraph(
            f"<b>{label}</b><br/>"
            f"<font size='12'>"
            f"<b>{display}</b>"
            f"</font>",
            ParagraphStyle(
                f"KPI_{label}",
                parent=BODY_STYLE,
                alignment=TA_CENTER,
                textColor=NAVY,
                leading=15,
            ),
        )

        current.append(content)

        if len(current) == 3:
            rows.append(current)
            current = []

    if current:

        while len(current) < 3:
            current.append("")

        rows.append(current)

    table = Table(
        rows,
        colWidths=[
            (
                PAGE_WIDTH
                - MARGIN_LEFT
                - MARGIN_RIGHT
            ) / 3
        ] * 3,
        rowHeights=[
            19 * mm
        ] * len(rows),
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_BLUE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    MID_GRAY,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    MID_GRAY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


# ============================================================================
# TREND TABLES
# ============================================================================

def make_profit_trend_table(rows):

    if not rows:
        return Paragraph(
            "Revenue / net profit trend unavailable.",
            BODY_STYLE,
        )

    data = [
        [
            Paragraph(
                "Year",
                TABLE_HEADER_STYLE,
            ),
            Paragraph(
                "Revenue",
                TABLE_HEADER_STYLE,
            ),
            Paragraph(
                "Net Profit",
                TABLE_HEADER_STYLE,
            ),
        ]
    ]

    for row in rows:

        data.append(
            [
                Paragraph(
                    clean_text(
                        row["year"]
                    ),
                    TABLE_STYLE,
                ),
                Paragraph(
                    fmt_number(
                        row["revenue"]
                    ),
                    TABLE_STYLE,
                ),
                Paragraph(
                    fmt_number(
                        row["profit"]
                    ),
                    TABLE_STYLE,
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            35 * mm,
            55 * mm,
            55 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    MID_GRAY,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT_GRAY,
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


def make_roe_roce_table(rows):

    if not rows:
        return Paragraph(
            "ROE / ROCE trend unavailable.",
            BODY_STYLE,
        )

    data = [
        [
            Paragraph(
                "Year",
                TABLE_HEADER_STYLE,
            ),
            Paragraph(
                "ROE",
                TABLE_HEADER_STYLE,
            ),
            Paragraph(
                "ROCE",
                TABLE_HEADER_STYLE,
            ),
        ]
    ]

    for row in rows:

        data.append(
            [
                Paragraph(
                    clean_text(
                        row["year"]
                    ),
                    TABLE_STYLE,
                ),
                Paragraph(
                    fmt_pct(
                        row["roe"]
                    ),
                    TABLE_STYLE,
                ),
                Paragraph(
                    fmt_pct(
                        row["roce"]
                    ),
                    TABLE_STYLE,
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            35 * mm,
            55 * mm,
            55 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    MID_GRAY,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT_GRAY,
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ============================================================================
# TWO-COLUMN SNAPSHOTS
# ============================================================================

def make_panel(title, rows):

    content = [
        [
            Paragraph(
                title,
                TABLE_HEADER_STYLE,
            )
        ]
    ]

    if not rows:
        rows = [
            [
                "Data",
                "Unavailable",
            ]
        ]

    for label, value in rows:

        content.append(
            [
                Paragraph(
                    f"<b>{label}</b>  {value}",
                    TABLE_STYLE,
                )
            ]
        )

    table = Table(
        content,
        colWidths=[
            83 * mm
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    MID_GRAY,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT_GRAY,
                    ],
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


def make_two_column_table(
    left_title,
    left_rows,
    right_title,
    right_rows,
):

    table = Table(
        [
            [
                make_panel(
                    left_title,
                    left_rows,
                ),
                make_panel(
                    right_title,
                    right_rows,
                ),
            ]
        ],
        colWidths=[
            86 * mm,
            86 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    return table


# ============================================================================
# PROS / CONS
# ============================================================================

def make_pros_cons_table(pros, cons):

    max_len = max(
        len(pros),
        len(cons),
        1,
    )

    data = [
        [
            Paragraph(
                "PROS",
                TABLE_HEADER_STYLE,
            ),
            Paragraph(
                "CONS",
                TABLE_HEADER_STYLE,
            ),
        ]
    ]

    for index in range(max_len):

        pro = (
            pros[index]
            if index < len(pros)
            else ""
        )

        con = (
            cons[index]
            if index < len(cons)
            else ""
        )

        data.append(
            [
                Paragraph(
                    f"• {pro}"
                    if pro
                    else "",
                    GOOD_STYLE,
                ),
                Paragraph(
                    f"• {con}"
                    if con
                    else "",
                    BAD_STYLE,
                ),
            ]
        )

    table = Table(
        data,
        colWidths=[
            86 * mm,
            86 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    GREEN,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    RED,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    MID_GRAY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# ============================================================================
# CAPITAL ALLOCATION BADGE
# ============================================================================

def make_capital_badge(pattern):

    if pattern in [
        "Reinvestor",
        "Cash Accumulator",
        "Shareholder Returns",
    ]:
        bg = LIGHT_BLUE
        text_color = NAVY

    elif pattern in [
        "Distress Signal",
        "Liquidating Assets",
    ]:
        bg = colors.HexColor("#FDECEC")
        text_color = RED

    else:
        bg = LIGHT_GRAY
        text_color = DARK_GRAY

    content = Paragraph(
        f"<b>Capital Allocation Pattern</b><br/>"
        f"<font size='13'>"
        f"<b>{clean_text(pattern)}</b>"
        f"</font>",
        ParagraphStyle(
            "Badge",
            parent=BODY_STYLE,
            alignment=TA_CENTER,
            textColor=text_color,
            leading=16,
        ),
    )

    table = Table(
        [[content]],
        colWidths=[
            172 * mm
        ],
        rowHeights=[
            19 * mm
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    bg,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    text_color,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    return table


# ============================================================================
# DOCUMENT CLASS
# ============================================================================

class TearsheetDocTemplate(BaseDocTemplate):

    def __init__(
        self,
        filename,
        company_name="",
        ticker="",
    ):

        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title=f"{ticker} - Company Tearsheet",
            author="Nifty100 Analytics",
        )

        self.company_name = company_name
        self.ticker = ticker

        frame = Frame(
            MARGIN_LEFT,
            MARGIN_BOTTOM,
            PAGE_WIDTH
            - MARGIN_LEFT
            - MARGIN_RIGHT,
            PAGE_HEIGHT
            - MARGIN_TOP
            - MARGIN_BOTTOM,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        # ReportLab 5 requires a PageTemplate object.
        page_template = PageTemplate(
            id="Tearsheet",
            frames=[frame],
            onPage=self._draw_header_footer,
        )

        self.addPageTemplates(
            [page_template]
        )

    def _draw_header_footer(
        self,
        canvas,
        doc,
    ):

        canvas.saveState()

        # ------------------------------------------------------------
        # HEADER
        # ------------------------------------------------------------

        canvas.setFillColor(NAVY)

        canvas.rect(
            0,
            PAGE_HEIGHT - 18 * mm,
            PAGE_WIDTH,
            18 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(WHITE)

        canvas.setFont(
            "Helvetica-Bold",
            10,
        )

        canvas.drawString(
            MARGIN_LEFT,
            PAGE_HEIGHT - 10.5 * mm,
            "NIFTY100 ANALYTICS",
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        right_text = self.ticker

        if self.company_name:
            right_text = (
                f"{self.ticker} | "
                f"{self.company_name}"
            )

        canvas.drawRightString(
            PAGE_WIDTH - MARGIN_RIGHT,
            PAGE_HEIGHT - 10.5 * mm,
            right_text[:90],
        )

        # ------------------------------------------------------------
        # FOOTER
        # ------------------------------------------------------------

        canvas.setStrokeColor(
            MID_GRAY
        )

        canvas.line(
            MARGIN_LEFT,
            9 * mm,
            PAGE_WIDTH - MARGIN_RIGHT,
            9 * mm,
        )

        canvas.setFillColor(
            DARK_GRAY
        )

        canvas.setFont(
            "Helvetica",
            6.5,
        )

        canvas.drawString(
            MARGIN_LEFT,
            5.5 * mm,
            "Sprint 5 | Company Tearsheet",
        )

        canvas.drawRightString(
            PAGE_WIDTH - MARGIN_RIGHT,
            5.5 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()


# ============================================================================
# BUILD ONE TEARSHEET
# ============================================================================

def build_tearsheet(company_id):

    db = Database(DB_PATH)

    company_df = load_company(
        db,
        company_id,
    )

    if company_df.empty:
        raise ValueError(
            f"Company {company_id} not found."
        )

    company = company_df.iloc[0].to_dict()

    company_name = clean_text(
        company.get("company_name")
    )

    ticker = str(company_id).upper()

    pl = load_profit_loss(
        db,
        company_id,
    )

    bs = load_balance_sheet(
        db,
        company_id,
    )

    cf = load_cash_flow(
        db,
        company_id,
    )

    ratios = load_ratios(
        db,
        company_id,
    )

    # ------------------------------------------------------------
    # Minimum history check
    # ------------------------------------------------------------

    if pl is not None and not pl.empty:

        year_col = first_existing(
            pl.columns,
            [
                "year",
                "financial_year",
            ],
        )

        if year_col:

            years = (
                pd.to_numeric(
                    pl[year_col],
                    errors="coerce",
                )
                .dropna()
                .unique()
            )

            if len(years) < 3:
                raise ValueError(
                    f"Insufficient history: "
                    f"{len(years)} years"
                )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = (
        OUTPUT_DIR
        / f"{ticker}_tearsheet.pdf"
    )

    doc = TearsheetDocTemplate(
        str(pdf_path),
        company_name=company_name,
        ticker=ticker,
    )

    story = []

    # ============================================================
    # PAGE 1
    # ============================================================

    story.append(
        Paragraph(
            f"{ticker} — {company_name}",
            TITLE_STYLE,
        )
    )

    story.append(
        Paragraph(
            "Company Investment Tearsheet",
            SUBTITLE_STYLE,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # KPI tiles
    kpis = get_latest_kpis(
        pl,
        ratios,
    )

    story.append(
        make_kpi_tiles(kpis)
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # Visual operating-performance charts
    chart_dir = Path(tempfile.mkdtemp(prefix=f"{ticker}_", dir=str(OUTPUT_DIR)))
    profit_chart = chart_dir / "profit_trend.png"
    return_chart = chart_dir / "roe_roce_trend.png"

    profit_rows = build_profit_trend(pl)
    return_rows = build_roe_roce_trend(ratios)

    profit_ok = make_profit_chart(profit_rows, profit_chart)
    return_ok = make_roe_roce_chart(return_rows, return_chart)

    story.append(
        Paragraph(
            "Operating Performance",
            SECTION_STYLE,
        )
    )

    if profit_ok:
        story.append(
            Image(
                str(profit_chart),
                width=172 * mm,
                height=60 * mm,
            )
        )
    else:
        story.append(
            Paragraph(
                "Revenue / net profit chart unavailable.",
                BODY_STYLE,
            )
        )

    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            "Return Metrics",
            SECTION_STYLE,
        )
    )

    if return_ok:
        story.append(
            Image(
                str(return_chart),
                width=172 * mm,
                height=60 * mm,
            )
        )
    else:
        story.append(
            Paragraph(
                "ROE / ROCE chart unavailable.",
                BODY_STYLE,
            )
        )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        Paragraph(
            "Trend charts use the recent annual financial history "
            "available in the Nifty100 Analytics engine.",
            SMALL_STYLE,
        )
    )

    # ============================================================
    # PAGE BREAK
    # ============================================================

    story.append(
        PageBreak()
    )

    # ============================================================
    # PAGE 2
    # ============================================================

    story.append(
        Paragraph(
            "Financial Position & Cash Flow",
            SECTION_STYLE,
        )
    )

    balance_chart = chart_dir / "balance_sheet.png"
    cashflow_chart = chart_dir / "cashflow_waterfall.png"

    balance_ok = make_balance_chart(bs, balance_chart)
    cashflow_ok = make_cashflow_waterfall(cf, cashflow_chart)

    chart_cells = []
    if balance_ok:
        chart_cells.append(
            Image(
                str(balance_chart),
                width=84 * mm,
                height=54 * mm,
            )
        )
    else:
        chart_cells.append(
            Paragraph(
                "Balance-sheet chart unavailable.",
                SMALL_STYLE,
            )
        )

    if cashflow_ok:
        chart_cells.append(
            Image(
                str(cashflow_chart),
                width=84 * mm,
                height=54 * mm,
            )
        )
    else:
        chart_cells.append(
            Paragraph(
                "Cash-flow waterfall unavailable.",
                SMALL_STYLE,
            )
        )

    chart_table = Table(
        [chart_cells],
        colWidths=[86 * mm, 86 * mm],
    )
    chart_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(chart_table)

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    # Compact numeric snapshots retained beneath the charts.
    story.append(
        make_two_column_table(
            "Balance Sheet Snapshot",
            build_balance_snapshot(bs),
            "Cash Flow Snapshot",
            build_cashflow_snapshot(cf),
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    # Pros / Cons
    pros, cons = load_pros_cons(
        company_id
    )

    if not pros:
        pros = [
            "No high-confidence positive signal available."
        ]

    if not cons:
        cons = [
            "No high-confidence negative signal available."
        ]

    story.append(
        Paragraph(
            "Investment Pros & Cons",
            SECTION_STYLE,
        )
    )

    story.append(
        make_pros_cons_table(
            pros,
            cons,
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    # Capital allocation
    pattern = load_capital_allocation(
        company_id
    )

    story.append(
        make_capital_badge(
            pattern
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # Analyst snapshot
    story.append(
        Paragraph(
            "Analyst Snapshot",
            SECTION_STYLE,
        )
    )

    summary_parts = []

    if kpis["Revenue"] is not None:
        summary_parts.append(
            f"Revenue is "
            f"{fmt_number(kpis['Revenue'])}"
        )

    if kpis["Net Profit"] is not None:
        summary_parts.append(
            f"net profit is "
            f"{fmt_number(kpis['Net Profit'])}"
        )

    if kpis["ROE"] is not None:
        summary_parts.append(
            f"ROE is "
            f"{fmt_pct(kpis['ROE'])}"
        )

    if kpis["ROCE"] is not None:
        summary_parts.append(
            f"ROCE is "
            f"{fmt_pct(kpis['ROCE'])}"
        )

    summary = ". ".join(
        summary_parts
    )

    if summary:
        summary += "."

    else:
        summary = (
            "Financial summary unavailable "
            "from the current dataset."
        )

    story.append(
        Paragraph(
            summary,
            BODY_STYLE,
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        Paragraph(
            "Data source: Nifty100 Analytics SQLite database "
            "and Sprint 5 generated intelligence outputs.",
            SMALL_STYLE,
        )
    )

    # Build PDF
    doc.build(story)

    # ReportLab has embedded the chart images by this point.
    try:
        for chart_file in chart_dir.glob("*"):
            chart_file.unlink(missing_ok=True)
        chart_dir.rmdir()
    except Exception:
        pass

    if not pdf_path.exists():
        raise RuntimeError(
            f"PDF was not created: {pdf_path}"
        )

    size = pdf_path.stat().st_size

    if size < 30000:
        raise RuntimeError(
            f"PDF below Day 33 DoD size: {size} bytes"
        )

    return pdf_path


# ============================================================================
# PDF VALIDATION
# ============================================================================

def validate_pdf(pdf_path):

    if not pdf_path.exists():
        return False, "file missing"

    size = pdf_path.stat().st_size

    if size < 30000:
        return (
            False,
            f"below Day 33 DoD size ({size} bytes)",
        )

    try:
        from pypdf import PdfReader

        reader = PdfReader(
            str(pdf_path)
        )

        pages = len(
            reader.pages
        )

        if pages != 2:
            return (
                False,
                f"expected 2 pages, "
                f"found {pages}",
            )

    except ImportError:

        pages = "not_checked"

    except Exception as exc:

        return (
            False,
            f"PDF validation error: {exc}",
        )

    return (
        True,
        f"{size:,} bytes, pages={pages}",
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    import sys

    batch_mode = "--batch" in sys.argv

    print("=" * 70)

    if batch_mode:
        print("SPRINT 5 - DAY 34")
        print("FULL COMPANY TEARSHEET BATCH")
    else:
        print("SPRINT 5 - DAY 33")
        print("COMPANY TEARSHEET GENERATOR")

    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------------------
    # DAY 33: original 5-company visual/layout test
    # ------------------------------------------------------------------------

    if not batch_mode:

        test_companies = [
            "TCS",
            "HDFCBANK",
            "RELIANCE",
            "SUNPHARMA",
            "TATASTEEL",
        ]

        generated = []
        failures = []

        for company_id in test_companies:

            try:

                path = build_tearsheet(
                    company_id
                )

                valid, message = validate_pdf(
                    path
                )

                if not valid:
                    raise RuntimeError(
                        message
                    )

                generated.append(
                    company_id
                )

                print(
                    f"PASS {company_id:<12} "
                    f"{message}"
                )

            except Exception as exc:

                failures.append(
                    (
                        company_id,
                        str(exc),
                    )
                )

                print(
                    f"FAIL {company_id:<12} "
                    f"{exc}"
                )

        print()
        print("-" * 70)

        print(
            f"Generated : "
            f"{len(generated)}/{len(test_companies)}"
        )

        print(
            f"Failures  : "
            f"{len(failures)}"
        )

        if failures:

            print()
            print("Failures:")

            for company_id, error in failures:

                print(
                    f"  {company_id}: "
                    f"{error}"
                )

        print()
        print("Output directory:")
        print(
            f"  {OUTPUT_DIR}"
        )

        print()
        print("=" * 70)

        if len(generated) == len(
            test_companies
        ):

            print(
                "DAY 33 STATUS: PASS"
            )

            print("=" * 70)

            return

        print(
            "DAY 33 STATUS: FAIL"
        )

        print("=" * 70)

        raise RuntimeError(
            "Day 33 tearsheet generation failed."
        )

    # ------------------------------------------------------------------------
    # DAY 34: generate tearsheets for all companies
    # ------------------------------------------------------------------------

    print()
    print("[1/4] Loading company universe...")

    conn = sqlite3.connect(DB_PATH)

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            ORDER BY id
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year
            FROM profitandloss
            ORDER BY company_id, year
            """,
            conn,
        )

    finally:

        conn.close()

    companies["company_id"] = (
        companies["company_id"]
        .astype(str)
        .str.strip()
    )

    pnl["company_id"] = (
        pnl["company_id"]
        .astype(str)
        .str.strip()
    )

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce",
    )

    pnl = pnl.dropna(
        subset=["company_id", "year"]
    )

    year_counts = (
        pnl.groupby("company_id")["year"]
        .nunique()
    )

    print(
        f"      Companies: {len(companies)}"
    )

    print(
        f"      P&L rows: {len(pnl)}"
    )

    # ------------------------------------------------------------------------
    # Determine eligible / skipped companies
    # ------------------------------------------------------------------------

    eligible = []
    skipped = []

    for company_id in companies["company_id"]:

        years = int(
            year_counts.get(
                company_id,
                0,
            )
        )

        if years < 3:

            skipped.append(
                {
                    "company_id": company_id,
                    "reason": f"Only {years} years of P&L data",
                }
            )

        else:

            eligible.append(
                company_id
            )

    print(
        f"      Eligible: {len(eligible)}"
    )

    print(
        f"      Skipped (<3 years): {len(skipped)}"
    )

    # ------------------------------------------------------------------------
    # Write skipped-company report
    # ------------------------------------------------------------------------

    skipped_path = (
        ROOT
        / "output"
        / "skipped_tearsheets.csv"
    )

    if skipped:

        pd.DataFrame(
            skipped
        ).to_csv(
            skipped_path,
            index=False,
        )

    else:

        pd.DataFrame(
            columns=[
                "company_id",
                "reason",
            ]
        ).to_csv(
            skipped_path,
            index=False,
        )

    # ------------------------------------------------------------------------
    # Generate PDFs
    # ------------------------------------------------------------------------

    print()
    print("[2/4] Generating company tearsheets...")

    generated = []
    failures = []

    total = len(eligible)

    for index, company_id in enumerate(
        eligible,
        start=1,
    ):

        try:

            path = build_tearsheet(
                company_id
            )

            valid, message = validate_pdf(
                path
            )

            if not valid:

                raise RuntimeError(
                    message
                )

            generated.append(
                company_id
            )

            print(
                f"[{index:>3}/{total}] "
                f"PASS {company_id:<12} "
                f"{message}"
            )

        except Exception as exc:

            failures.append(
                (
                    company_id,
                    str(exc),
                )
            )

            print(
                f"[{index:>3}/{total}] "
                f"FAIL {company_id:<12} "
                f"{exc}"
            )

    # ------------------------------------------------------------------------
    # Validate final directory
    # ------------------------------------------------------------------------

    print()
    print("[3/4] Validating generated files...")

    pdf_files = sorted(
        OUTPUT_DIR.glob(
            "*_tearsheet.pdf"
        )
    )

    valid_files = []
    invalid_files = []

    for pdf_path in pdf_files:

        valid, message = validate_pdf(
            pdf_path
        )

        if valid:

            valid_files.append(
                pdf_path
            )

        else:

            invalid_files.append(
                (
                    pdf_path.name,
                    message,
                )
            )

    # ------------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------------

    print()
    print("[4/4] Day 34 batch validation")
    print()
    print("=" * 70)

    print(
        f"Eligible companies : {len(eligible)}"
    )

    print(
        f"Generated this run : {len(generated)}"
    )

    print(
        f"Valid PDF files    : {len(valid_files)}"
    )

    print(
        f"Skipped (<3 years) : {len(skipped)}"
    )

    print(
        f"Generation failures: {len(failures)}"
    )

    print(
        f"Invalid PDF files  : {len(invalid_files)}"
    )

    print()
    print(
        f"Output directory:"
    )

    print(
        f"  {OUTPUT_DIR}"
    )

    print()
    print(
        f"Skipped report:"
    )

    print(
        f"  {skipped_path}"
    )

    if failures:

        print()
        print("Generation failures:")

        for company_id, error in failures:

            print(
                f"  {company_id}: {error}"
            )

    if invalid_files:

        print()
        print("Invalid PDFs:")

        for filename, error in invalid_files:

            print(
                f"  {filename}: {error}"
            )

    print()
    print("=" * 70)

    # ------------------------------------------------------------------------
    # PASS criteria
    # ------------------------------------------------------------------------

    expected_valid = len(
        eligible
    )

    if (
        len(generated) == expected_valid
        and len(valid_files) == expected_valid
        and not failures
        and not invalid_files
    ):

        print(
            "DAY 34 TEARSHEET BATCH: PASS"
        )

        print("=" * 70)

        return

    print(
        "DAY 34 TEARSHEET BATCH: FAIL"
    )

    print("=" * 70)

    raise RuntimeError(
        "Day 34 full tearsheet batch validation failed."
    )


if __name__ == "__main__":
    main()