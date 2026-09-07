"""
Sprint 5 - Day 35
Portfolio Summary PDF & Sprint Review

Generates:
    reports/portfolio/portfolio_summary.pdf

One page per company, alphabetically by ticker.

Each page contains:
    - Company name
    - Ticker
    - Sector
    - Six key KPIs
    - Trend arrows for latest-year movement

Trend rules:
    ↑ = improved
    ↓ = declined
    → = flat within 2%

The six KPIs used:
    Revenue
    Net Profit
    ROE
    ROCE
    P/E
    FCF Yield
"""

from pathlib import Path
import sqlite3
import re
import math

import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from pypdf import PdfReader


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "portfolio"
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = OUTPUT_DIR / "portfolio_summary.pdf"

VALUATION_FILE = (
    ROOT / "output" / "valuation_summary.xlsx"
)


# ============================================================
# CONSTANTS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

EXPECTED_COMPANIES = 92


# ============================================================
# UTILITIES
# ============================================================

def clean_text(value, default="N/A"):
    """Clean a value for display."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except Exception:
        pass

    text = str(value).strip()

    if not text:
        return default

    if text.lower() in {
        "nan",
        "none",
        "null",
    }:
        return default

    return text


def normalize_columns(df):
    """Normalize dataframe columns."""

    df = df.copy()

    columns = []

    for column in df.columns:
        name = str(column).strip().lower()
        name = name.replace(" ", "_")
        name = name.replace("-", "_")
        columns.append(name)

    df.columns = columns

    return df


def normalize_id(df):
    """Normalize company identifiers."""

    df = df.copy()

    if "company_id" in df.columns:
        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

    return df


def numeric(value):
    """Safely convert to float."""

    try:
        value = float(value)

        if math.isnan(value):
            return np.nan

        if math.isinf(value):
            return np.nan

        return value

    except Exception:
        return np.nan


def fmt_number(value, decimals=1):
    """Format numeric value."""

    value = numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f}"


def fmt_pct(value, decimals=1):
    """Format percentage."""

    value = numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}%"


def fmt_multiple(value):
    """Format valuation multiple."""

    value = numeric(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:.1f}x"


def safe_text(value):
    """Escape ReportLab-sensitive text."""

    text = clean_text(value)

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return text


# ============================================================
# TREND CALCULATION
# ============================================================

def trend_arrow(latest, previous):
    """
    Calculate trend arrow.

    Improved:
        latest > previous by more than 2%

    Declined:
        latest < previous by more than 2%

    Flat:
        movement within ±2%

    Special handling:
        Missing values -> →
        Previous zero -> based on latest sign
    """

    latest = numeric(latest)
    previous = numeric(previous)

    if pd.isna(latest) or pd.isna(previous):
        return "→"

    if previous == 0:

        if latest > 0:
            return "↑"

        if latest < 0:
            return "↓"

        return "→"

    change = (
        (latest - previous)
        / abs(previous)
    )

    if change > 0.02:
        return "↑"

    if change < -0.02:
        return "↓"

    return "→"


# ============================================================
# DATABASE LOAD
# ============================================================

def load_database_data():
    """
    Load companies and historical P&L data.

    Actual companies schema:
        id
        company_name
        roce_percentage
        roe_percentage

    Actual P&L schema:
        company_id
        year
        sales
        net_profit
        ...
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name,
                roce_percentage,
                roe_percentage
            FROM companies
            """,
            conn,
        )

        pnl = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                sales,
                net_profit,
                roe,
                roce
            FROM profitandloss
            ORDER BY company_id, year
            """,
            conn,
        )

    except Exception as exc:

        # Some project versions may store P&L under
        # a slightly different table name.
        try:

            pnl = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    year,
                    sales,
                    net_profit
                FROM profitandloss
                ORDER BY company_id, year
                """,
                conn,
            )

        except Exception:
            conn.close()
            raise RuntimeError(
                "Could not load P&L data from the database. "
                f"Original error: {exc}"
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

    return companies, pnl


# ============================================================
# VALUATION LOAD
# ============================================================

def load_valuation():
    """Load valuation summary."""

    if not VALUATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing valuation file: {VALUATION_FILE}"
        )

    df = pd.read_excel(
        VALUATION_FILE
    )

    df = normalize_columns(df)
    df = normalize_id(df)

    return df


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_dataset(
    companies,
    pnl,
    valuation,
):
    """Build one company-level portfolio dataset."""

    # --------------------------------------------------------
    # Start with valuation because it contains sector.
    # --------------------------------------------------------

    valuation_latest = valuation.copy()

    if "company_id" not in valuation_latest.columns:
        raise RuntimeError(
            "valuation_summary.xlsx missing company_id"
        )

    # --------------------------------------------------------
    # One row per company.
    # --------------------------------------------------------

    valuation_latest = (
        valuation_latest
        .drop_duplicates(
            subset=["company_id"],
            keep="last",
        )
    )

    merged = companies.merge(
        valuation_latest,
        on="company_id",
        how="left",
        suffixes=(
            "_master",
            "",
        ),
    )

    # --------------------------------------------------------
    # Sector
    # --------------------------------------------------------

    if "sector" not in merged.columns:
        merged["sector"] = "Unknown"

    # --------------------------------------------------------
    # Company name
    # --------------------------------------------------------

    if "company_name" not in merged.columns:

        if "company_name_master" in merged.columns:
            merged["company_name"] = (
                merged["company_name_master"]
            )

        else:
            merged["company_name"] = (
                merged["company_id"]
            )

    # --------------------------------------------------------
    # Historical P&L
    # --------------------------------------------------------

    pnl = pnl.copy()

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce",
    )

    pnl = pnl.dropna(
        subset=["year"]
    )

    pnl["year"] = pnl["year"].astype(int)

    pnl = pnl.sort_values(
        [
            "company_id",
            "year",
        ]
    )

    # --------------------------------------------------------
    # Latest / previous P&L per company
    # --------------------------------------------------------

    latest_rows = []

    previous_rows = []

    for company_id, group in pnl.groupby(
        "company_id"
    ):

        group = group.sort_values(
            "year"
        )

        latest_rows.append(
            group.iloc[-1]
        )

        if len(group) >= 2:
            previous_rows.append(
                group.iloc[-2]
            )

    if latest_rows:

        latest = pd.DataFrame(
            latest_rows
        )

        latest = latest.rename(
            columns={
                column: f"latest_{column}"
                for column in latest.columns
                if column != "company_id"
            }
        )

        merged = merged.merge(
            latest,
            on="company_id",
            how="left",
        )

    if previous_rows:

        previous = pd.DataFrame(
            previous_rows
        )

        previous = previous.rename(
            columns={
                column: f"previous_{column}"
                for column in previous.columns
                if column != "company_id"
            }
        )

        merged = merged.merge(
            previous,
            on="company_id",
            how="left",
        )

    return merged


# ============================================================
# KPI EXTRACTION
# ============================================================

def get_value(row, *columns):
    """Return first available numeric column."""

    for column in columns:

        if column in row.index:

            value = numeric(
                row[column]
            )

            if not pd.isna(value):
                return value

    return np.nan


def build_company_kpis(row):
    """
    Build six portfolio KPIs.

    1. Revenue
    2. Net Profit
    3. ROE
    4. ROCE
    5. P/E
    6. FCF Yield
    """

    revenue_latest = get_value(
        row,
        "latest_sales",
        "sales",
    )

    revenue_previous = get_value(
        row,
        "previous_sales",
    )

    profit_latest = get_value(
        row,
        "latest_net_profit",
        "net_profit",
    )

    profit_previous = get_value(
        row,
        "previous_net_profit",
    )

    roe_latest = get_value(
        row,
        "roe",
        "latest_roe",
        "roe_percentage",
    )

    roe_previous = get_value(
        row,
        "previous_roe",
    )

    roce_latest = get_value(
        row,
        "roce",
        "latest_roce",
        "roce_percentage",
    )

    roce_previous = get_value(
        row,
        "previous_roce",
    )

    pe_latest = get_value(
        row,
        "p/e",
    )

    fcf_yield_latest = get_value(
        row,
        "fcf_yield_pct",
    )

    return [
        {
            "name": "Revenue",
            "value": fmt_number(
                revenue_latest
            ),
            "trend": trend_arrow(
                revenue_latest,
                revenue_previous,
            ),
        },
        {
            "name": "Net Profit",
            "value": fmt_number(
                profit_latest
            ),
            "trend": trend_arrow(
                profit_latest,
                profit_previous,
            ),
        },
        {
            "name": "ROE",
            "value": fmt_pct(
                roe_latest
            ),
            "trend": trend_arrow(
                roe_latest,
                roe_previous,
            ),
        },
        {
            "name": "ROCE",
            "value": fmt_pct(
                roce_latest
            ),
            "trend": trend_arrow(
                roce_latest,
                roce_previous,
            ),
        },
        {
            "name": "P/E",
            "value": fmt_multiple(
                pe_latest
            ),
            # P/E is a valuation metric, so lower is
            # treated as improved.
            "trend": (
                trend_arrow(
                    -pe_latest
                    if not pd.isna(pe_latest)
                    else np.nan,
                    -get_value(
                        row,
                        "previous_p/e",
                    )
                    if not pd.isna(
                        get_value(
                            row,
                            "previous_p/e",
                        )
                    )
                    else np.nan,
                )
            ),
        },
        {
            "name": "FCF Yield",
            "value": fmt_pct(
                fcf_yield_latest
            ),
            "trend": trend_arrow(
                fcf_yield_latest,
                get_value(
                    row,
                    "previous_fcf_yield_pct",
                ),
            ),
        },
    ]


# ============================================================
# REPORT STYLES
# ============================================================

def get_styles():

    styles = getSampleStyleSheet()

    return {

        "title": ParagraphStyle(
            "PortfolioTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            spaceAfter=5,
        ),

        "company": ParagraphStyle(
            "PortfolioCompany",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),

        "subtitle": ParagraphStyle(
            "PortfolioSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceAfter=12,
        ),

        "section": ParagraphStyle(
            "PortfolioSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        ),

        "body": ParagraphStyle(
            "PortfolioBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        ),

        "small": ParagraphStyle(
            "PortfolioSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.grey,
        ),

        "kpi_name": ParagraphStyle(
            "KPIName",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),

        "kpi_value": ParagraphStyle(
            "KPIValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=TA_CENTER,
        ),

        "trend": ParagraphStyle(
            "Trend",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=19,
            alignment=TA_CENTER,
        ),
    }


# ============================================================
# KPI TABLE
# ============================================================

def build_kpi_table(kpis, styles):

    header = [
        Paragraph(
            safe_text(kpi["name"]),
            styles["kpi_name"],
        )
        for kpi in kpis
    ]

    values = [
        Paragraph(
            safe_text(kpi["value"]),
            styles["kpi_value"],
        )
        for kpi in kpis
    ]

    trends = [
        Paragraph(
            safe_text(kpi["trend"]),
            styles["trend"],
        )
        for kpi in kpis
    ]

    table = Table(
        [
            header,
            values,
            trends,
        ],
        colWidths=[
            29.5 * mm,
            29.5 * mm,
            29.5 * mm,
            29.5 * mm,
            29.5 * mm,
            29.5 * mm,
        ],
        rowHeights=[
            9 * mm,
            14 * mm,
            9 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#E8E8E8"
                    ),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#B5B5B5"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return table


# ============================================================
# PAGE FOOTER
# ============================================================

def footer(canvas, doc):

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.grey
    )

    canvas.drawString(
        15 * mm,
        8 * mm,
        "Nifty100 Analytics — Sprint 5 Portfolio Summary",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 15 * mm,
        8 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# MAIN PDF GENERATION
# ============================================================

def generate_portfolio_pdf(
    dataset
):
    """Generate portfolio summary."""

    styles = get_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Nifty100 Portfolio Summary",
        author="Nifty100 Analytics",
    )

    story = []

    # --------------------------------------------------------
    # Sort alphabetically by ticker/company ID
    # --------------------------------------------------------

    dataset = dataset.sort_values(
        "company_id"
    ).reset_index(
        drop=True
    )

    for index, row in dataset.iterrows():

        ticker = clean_text(
            row.get("company_id"),
            "N/A",
        )

        company_name = clean_text(
            row.get("company_name"),
            ticker,
        )

        sector = clean_text(
            row.get("sector"),
            "Unknown",
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "NIFTY 100 PORTFOLIO SUMMARY",
                styles["title"],
            )
        )

        story.append(
            Paragraph(
                safe_text(company_name),
                styles["company"],
            )
        )

        story.append(
            Paragraph(
                f"<b>Ticker:</b> {safe_text(ticker)}"
                f"&nbsp;&nbsp;&nbsp;"
                f"<b>Sector:</b> {safe_text(sector)}",
                styles["subtitle"],
            )
        )

        # ----------------------------------------------------
        # KPI section
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Key Performance Indicators",
                styles["section"],
            )
        )

        kpis = build_company_kpis(
            row
        )

        story.append(
            build_kpi_table(
                kpis,
                styles,
            )
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        # ----------------------------------------------------
        # Trend legend
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "<b>Trend Direction</b>",
                styles["section"],
            )
        )

        legend_data = [
            [
                Paragraph(
                    "↑ Improved",
                    styles["body"],
                ),
                Paragraph(
                    "→ Flat",
                    styles["body"],
                ),
                Paragraph(
                    "↓ Declined",
                    styles["body"],
                ),
            ]
        ]

        legend = Table(
            legend_data,
            colWidths=[
                55 * mm,
                55 * mm,
                55 * mm,
            ],
        )

        legend.setStyle(
            TableStyle(
                [
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.HexColor(
                            "#CCCCCC"
                        ),
                    ),
                ]
            )
        )

        story.append(
            legend
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        # ----------------------------------------------------
        # Company snapshot
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Company Snapshot",
                styles["section"],
            )
        )

        snapshot = (
            f"<b>Company:</b> "
            f"{safe_text(company_name)}<br/>"
            f"<b>Ticker:</b> "
            f"{safe_text(ticker)}<br/>"
            f"<b>Sector:</b> "
            f"{safe_text(sector)}<br/>"
            f"<b>Portfolio position:</b> "
            f"{index + 1} of {len(dataset)}"
        )

        story.append(
            Paragraph(
                snapshot,
                styles["body"],
            )
        )

        story.append(
            Spacer(
                1,
                12 * mm,
            )
        )

        # ----------------------------------------------------
        # Methodology
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Methodology",
                styles["section"],
            )
        )

        methodology = (
            "The portfolio summary uses the latest available "
            "financial and valuation data in the Nifty100 "
            "Analytics pipeline. Trend arrows compare the "
            "latest available year with the immediately "
            "preceding year. A movement within ±2% is classified "
            "as flat. For P/E, a decline is treated as an "
            "improvement in valuation."
        )

        story.append(
            Paragraph(
                methodology,
                styles["body"],
            )
        )

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        story.append(
            Paragraph(
                "Source: Nifty100 Analytics project database "
                "and valuation_summary.xlsx.",
                styles["small"],
            )
        )

        # ----------------------------------------------------
        # New page
        # ----------------------------------------------------

        if index < len(dataset) - 1:
            story.append(
                PageBreak()
            )

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_portfolio_pdf():
    """Validate generated portfolio PDF."""

    if not OUTPUT_FILE.exists():
        raise RuntimeError(
            "Portfolio PDF was not generated."
        )

    size = OUTPUT_FILE.stat().st_size

    reader = PdfReader(
        str(OUTPUT_FILE)
    )

    pages = len(
        reader.pages
    )

    print("\n" + "=" * 70)
    print("DAY 35 PORTFOLIO PDF VALIDATION")
    print("=" * 70)

    print(
        f"File       : {OUTPUT_FILE}"
    )

    print(
        f"Size       : {size:,} bytes"
    )

    print(
        f"Pages      : {pages}"
    )

    print(
        f"Expected   : {EXPECTED_COMPANIES}"
    )

    if pages != EXPECTED_COMPANIES:
        raise RuntimeError(
            f"Expected {EXPECTED_COMPANIES} pages "
            f"but generated {pages}."
        )

    if size < 30_000:
        raise RuntimeError(
            "Portfolio PDF is unexpectedly small."
        )

    # Check every page has extractable text.
    blank_pages = []

    for number, page in enumerate(
        reader.pages,
        start=1,
    ):

        text = page.extract_text()

        if not text or len(text.strip()) < 20:
            blank_pages.append(
                number
            )

    if blank_pages:
        raise RuntimeError(
            f"Blank/empty pages detected: "
            f"{blank_pages}"
        )

    print(
        f"Blank pages: {len(blank_pages)}"
    )

    print(
        "\nDAY 35 PORTFOLIO PDF PASS"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SPRINT 5 - DAY 35")
    print("PORTFOLIO SUMMARY PDF")
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print(
        "\n[1/5] Loading company database..."
    )

    companies, pnl = (
        load_database_data()
    )

    print(
        f"      Companies: {len(companies)}"
    )

    print(
        f"      P&L rows: {len(pnl)}"
    )

    if len(companies) != EXPECTED_COMPANIES:
        raise RuntimeError(
            f"Expected {EXPECTED_COMPANIES} companies "
            f"but found {len(companies)}."
        )

    print(
        "\n[2/5] Loading valuation data..."
    )

    valuation = load_valuation()

    print(
        f"      Valuation rows: {len(valuation)}"
    )

    print(
        "\n[3/5] Preparing portfolio dataset..."
    )

    dataset = prepare_dataset(
        companies,
        pnl,
        valuation,
    )

    print(
        f"      Portfolio rows: {len(dataset)}"
    )

    if len(dataset) != EXPECTED_COMPANIES:
        raise RuntimeError(
            "Portfolio dataset does not contain "
            "exactly 92 companies."
        )

    print(
        "\n[4/5] Generating portfolio PDF..."
    )

    generate_portfolio_pdf(
        dataset
    )

    print(
        "\n[5/5] Validating portfolio PDF..."
    )

    validate_portfolio_pdf()

    print(
        "\nOutput:"
    )

    print(
        f"  {OUTPUT_FILE}"
    )

    print(
        "\nDAY 35 PASS"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()