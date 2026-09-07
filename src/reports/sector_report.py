"""
Sprint 5 - Day 34
Sector Report Generator

Generates one 2-page PDF report for every sector represented in
output/valuation_summary.xlsx.

Inputs
------
- db/nifty100.db
- output/valuation_summary.xlsx
- output/cashflow_intelligence.xlsx
- output/pros_cons_generated.csv

Output
------
- output/sector_reports/<sector>_sector_report.pdf

Requirements
------------
- Every sector is discovered dynamically.
- No sector names are hardcoded.
- Each generated PDF must be >= 30 KB.
- Each generated PDF must contain exactly 2 pages.
"""

from pathlib import Path
import re
import sqlite3
import warnings

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)

from pypdf import PdfReader


warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
SECTOR_DIR = OUTPUT_DIR / "sector_reports"

VALUATION_FILE = OUTPUT_DIR / "valuation_summary.xlsx"
CASHFLOW_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"
PROS_CONS_FILE = OUTPUT_DIR / "pros_cons_generated.csv"

SECTOR_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONSTANTS
# ============================================================

MIN_PDF_BYTES = 30_000
EXPECTED_PAGES = 2

PAGE_WIDTH, PAGE_HEIGHT = A4


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def clean_text(value, default="N/A"):
    """Convert a value into clean display text."""

    if value is None:
        return default

    if pd.isna(value):
        return default

    text = str(value).strip()

    if not text or text.lower() in {"nan", "none", "null"}:
        return default

    return text


def safe_filename(value):
    """Create a filesystem-safe filename."""

    text = clean_text(value, "Unknown Sector")

    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text)

    return text[:120]


def normalize_columns(df):
    """Normalize dataframe column names."""

    df = df.copy()

    normalized = []

    for column in df.columns:
        name = str(column).strip().lower()
        name = name.replace(" ", "_")
        name = name.replace("-", "_")
        normalized.append(name)

    df.columns = normalized

    return df


def normalize_company_id(df):
    """Normalize company ID values."""

    df = df.copy()

    if "company_id" in df.columns:
        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

    return df


def numeric_series(df, column):
    """Return a numeric series or NaN series."""

    if column not in df.columns:
        return pd.Series(
            np.nan,
            index=df.index,
            dtype=float,
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    )


def find_column(df, candidates):
    """Find the first matching column from candidate names."""

    normalized = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower()

        if key in normalized:
            return normalized[key]

    # Partial matching
    for candidate in candidates:
        candidate = candidate.lower()

        for column in df.columns:
            if candidate in str(column).lower():
                return column

    return None


def fmt_number(value, decimals=1):
    """Format a number for reports."""

    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def fmt_pct(value, decimals=1):
    """Format percentage."""

    if value is None or pd.isna(value):
        return "N/A"

    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "N/A"


def sector_slug(sector):
    return safe_filename(sector).lower()


# ============================================================
# DATABASE
# ============================================================

def load_universe():
    """
    Load company master data.

    Actual database schema:

        companies.id
        companies.company_name
        companies.roce_percentage
        companies.roe_percentage

    There is no company_id or sector column in companies.
    """

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        df = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name,
                roce_percentage AS roce_master,
                roe_percentage AS roe_master
            FROM companies
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        raise RuntimeError(
            "companies table is empty"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
    )

    df["company_name"] = (
        df["company_name"]
        .astype(str)
        .str.strip()
    )

    return df


# ============================================================
# INPUT FILES
# ============================================================

def load_valuation():
    """Load valuation summary."""

    if not VALUATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing valuation file: {VALUATION_FILE}"
        )

    df = pd.read_excel(VALUATION_FILE)

    df = normalize_columns(df)
    df = normalize_company_id(df)

    if "company_id" not in df.columns:
        raise RuntimeError(
            "valuation_summary.xlsx is missing company_id"
        )

    if "sector" not in df.columns:
        raise RuntimeError(
            "valuation_summary.xlsx is missing sector"
        )

    return df


def load_cashflow():
    """Load cash-flow intelligence workbook."""

    if not CASHFLOW_FILE.exists():
        raise FileNotFoundError(
            f"Missing cash-flow file: {CASHFLOW_FILE}"
        )

    df = pd.read_excel(
        CASHFLOW_FILE
    )

    df = normalize_columns(df)
    df = normalize_company_id(df)

    return df


def load_pros_cons():
    """Load generated pros and cons."""

    if not PROS_CONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing pros/cons file: {PROS_CONS_FILE}"
        )

    df = pd.read_csv(
        PROS_CONS_FILE
    )

    df = normalize_columns(df)
    df = normalize_company_id(df)

    return df


# ============================================================
# MERGE DATA
# ============================================================

def prepare_sector_data(
    universe,
    valuation,
    cashflow,
    pros_cons,
):
    """
    Combine master, valuation, cash-flow and NLP data.

    Sector classification comes from valuation_summary.xlsx.
    """

    universe = universe.copy()
    valuation = valuation.copy()
    cashflow = cashflow.copy()
    pros_cons = pros_cons.copy()

    universe = normalize_company_id(universe)
    valuation = normalize_company_id(valuation)
    cashflow = normalize_company_id(cashflow)
    pros_cons = normalize_company_id(pros_cons)

    # --------------------------------------------------------
    # Start from valuation because it contains sector
    # --------------------------------------------------------

    merged = valuation.merge(
        universe,
        on="company_id",
        how="left",
        suffixes=("", "_master"),
    )

    # --------------------------------------------------------
    # Fill company name
    # --------------------------------------------------------

    if "company_name" not in merged.columns:
        merged["company_name"] = merged.get(
            "company_name_master",
            merged["company_id"],
        )

    if "company_name_master" in merged.columns:
        merged["company_name"] = (
            merged["company_name"]
            .replace("", np.nan)
            .fillna(merged["company_name_master"])
        )

    # --------------------------------------------------------
    # ROE / ROCE
    # --------------------------------------------------------

    if "roe" not in merged.columns:
        merged["roe"] = np.nan

    if "roce" not in merged.columns:
        merged["roce"] = np.nan

    merged["roe"] = numeric_series(
        merged,
        "roe",
    )

    merged["roce"] = numeric_series(
        merged,
        "roce",
    )

    if "roe_master" in merged.columns:
        merged["roe"] = merged["roe"].fillna(
            numeric_series(
                merged,
                "roe_master",
            )
        )

    if "roce_master" in merged.columns:
        merged["roce"] = merged["roce"].fillna(
            numeric_series(
                merged,
                "roce_master",
            )
        )

    # --------------------------------------------------------
    # Cash-flow data
    # --------------------------------------------------------

    if (
        "company_id" in cashflow.columns
        and not cashflow.empty
    ):
        # Avoid duplicate company rows.
        cashflow_latest = (
            cashflow
            .drop_duplicates(
                subset=["company_id"],
                keep="last",
            )
        )

        cashflow_columns = [
            column
            for column in cashflow_latest.columns
            if column != "company_id"
        ]

        if cashflow_columns:
            merged = merged.merge(
                cashflow_latest[
                    ["company_id"] + cashflow_columns
                ],
                on="company_id",
                how="left",
                suffixes=("", "_cashflow"),
            )

    # --------------------------------------------------------
    # Pros/cons data
    # --------------------------------------------------------

    if (
        "company_id" in pros_cons.columns
        and not pros_cons.empty
    ):
        pc = pros_cons.copy()

        # Find signal column.
        signal_column = find_column(
            pc,
            [
                "signal_type",
                "type",
                "signal",
                "category",
            ],
        )

        confidence_column = find_column(
            pc,
            [
                "confidence",
                "confidence_score",
            ],
        )

        aggregation = {}

        if signal_column:
            aggregation["pro_count"] = (
                signal_column,
                lambda x: (
                    x.astype(str)
                    .str.lower()
                    .eq("pro")
                    .sum()
                ),
            )

            aggregation["con_count"] = (
                signal_column,
                lambda x: (
                    x.astype(str)
                    .str.lower()
                    .eq("con")
                    .sum()
                ),
            )

        if confidence_column:
            aggregation["avg_confidence"] = (
                confidence_column,
                lambda x: pd.to_numeric(
                    x,
                    errors="coerce",
                ).mean(),
            )

        if aggregation:
            pc_summary = (
                pc.groupby("company_id")
                .agg(**aggregation)
                .reset_index()
            )

            merged = merged.merge(
                pc_summary,
                on="company_id",
                how="left",
            )

    if "pro_count" not in merged.columns:
        merged["pro_count"] = 0

    if "con_count" not in merged.columns:
        merged["con_count"] = 0

    if "avg_confidence" not in merged.columns:
        merged["avg_confidence"] = np.nan

    return merged


# ============================================================
# CASH FLOW COLUMN DETECTION
# ============================================================

def detect_cashflow_columns(df):
    """Detect useful cash-flow columns dynamically."""

    columns = list(df.columns)

    result = {
        "operating_cash": None,
        "investing_cash": None,
        "financing_cash": None,
        "net_cash": None,
        "allocation": None,
        "quality": None,
        "distress": None,
    }

    for column in columns:
        c = column.lower()

        if (
            result["operating_cash"] is None
            and (
                "operating_activity" in c
                or "operating_cash" in c
                or c == "cfo"
            )
        ):
            result["operating_cash"] = column

        if (
            result["investing_cash"] is None
            and (
                "investing_activity" in c
                or "investing_cash" in c
                or "capex" in c
            )
        ):
            result["investing_cash"] = column

        if (
            result["financing_cash"] is None
            and (
                "financing_activity" in c
                or "financing_cash" in c
            )
        ):
            result["financing_cash"] = column

        if (
            result["net_cash"] is None
            and (
                "net_cash_flow" in c
                or c == "net_cash"
                or "net_cash" == c
            )
        ):
            result["net_cash"] = column

        if (
            result["allocation"] is None
            and (
                "allocation" in c
                or "pattern" in c
            )
        ):
            result["allocation"] = column

        if (
            result["quality"] is None
            and "quality" in c
        ):
            result["quality"] = column

        if (
            result["distress"] is None
            and "distress" in c
        ):
            result["distress"] = column

    return result


# ============================================================
# SECTOR METRICS
# ============================================================

def calculate_sector_metrics(df):
    """Calculate sector-level KPIs."""

    metrics = {}

    metrics["companies"] = len(df)

    metrics["pe"] = (
        numeric_series(df, "p/e")
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )

    metrics["pb"] = (
        numeric_series(df, "p/b")
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )

    metrics["ev_ebitda"] = (
        numeric_series(df, "ev/ebitda")
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )

    metrics["fcf_yield"] = (
        numeric_series(df, "fcf_yield_pct")
        .replace([np.inf, -np.inf], np.nan)
        .median()
    )

    metrics["roe"] = (
        numeric_series(df, "roe")
        .replace([np.inf, -np.inf], np.nan)
        .mean()
    )

    metrics["roce"] = (
        numeric_series(df, "roce")
        .replace([np.inf, -np.inf], np.nan)
        .mean()
    )

    metrics["pros"] = (
        pd.to_numeric(
            df["pro_count"],
            errors="coerce",
        ).sum()
    )

    metrics["cons"] = (
        pd.to_numeric(
            df["con_count"],
            errors="coerce",
        ).sum()
    )

    return metrics


# ============================================================
# CHARTS
# ============================================================

def create_valuation_chart(df, path):
    """Create valuation comparison chart."""

    cols = [
        ("P/E", "p/e"),
        ("P/B", "p/b"),
        ("EV/EBITDA", "ev/ebitda"),
    ]

    available = []

    for label, column in cols:
        if column in df.columns:
            value = (
                numeric_series(df, column)
                .replace(
                    [np.inf, -np.inf],
                    np.nan,
                )
                .median()
            )

            if not pd.isna(value):
                available.append(
                    (label, value)
                )

    fig, ax = plt.subplots(
        figsize=(8.2, 3.2)
    )

    if available:
        labels = [x[0] for x in available]
        values = [x[1] for x in available]

        ax.bar(
            labels,
            values,
        )

        ax.set_ylabel("Median Multiple")
        ax.set_title(
            "Sector Valuation Snapshot",
            fontsize=13,
            fontweight="bold",
        )

        ax.grid(
            axis="y",
            alpha=0.25,
        )

        for i, value in enumerate(values):
            ax.text(
                i,
                value,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    else:
        ax.text(
            0.5,
            0.5,
            "Valuation data unavailable",
            ha="center",
            va="center",
        )
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(
        path,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def create_returns_chart(df, path):
    """Create ROE/ROCE chart."""

    roe = (
        numeric_series(df, "roe")
        .replace([np.inf, -np.inf], np.nan)
        .mean()
    )

    roce = (
        numeric_series(df, "roce")
        .replace([np.inf, -np.inf], np.nan)
        .mean()
    )

    labels = []
    values = []

    if not pd.isna(roe):
        labels.append("ROE")
        values.append(roe)

    if not pd.isna(roce):
        labels.append("ROCE")
        values.append(roce)

    fig, ax = plt.subplots(
        figsize=(8.2, 3.2)
    )

    if values:
        ax.bar(
            labels,
            values,
        )

        ax.set_ylabel("Percentage")
        ax.set_title(
            "Sector Profitability",
            fontsize=13,
            fontweight="bold",
        )

        ax.grid(
            axis="y",
            alpha=0.25,
        )

        for i, value in enumerate(values):
            ax.text(
                i,
                value,
                f"{value:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    else:
        ax.text(
            0.5,
            0.5,
            "ROE / ROCE data unavailable",
            ha="center",
            va="center",
        )
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(
        path,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


def create_cashflow_chart(df, path):
    """Create cash-flow chart."""

    detected = detect_cashflow_columns(df)

    labels = []
    values = []

    mapping = [
        (
            "Operating",
            detected["operating_cash"],
        ),
        (
            "Investing",
            detected["investing_cash"],
        ),
        (
            "Financing",
            detected["financing_cash"],
        ),
        (
            "Net Cash",
            detected["net_cash"],
        ),
    ]

    for label, column in mapping:

        if column is None:
            continue

        value = (
            numeric_series(df, column)
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .mean()
        )

        if pd.isna(value):
            continue

        labels.append(label)
        values.append(value)

    fig, ax = plt.subplots(
        figsize=(8.2, 3.2)
    )

    if values:
        ax.bar(
            labels,
            values,
        )

        ax.axhline(
            0,
            linewidth=0.8,
        )

        ax.set_ylabel("Average Cash Flow")
        ax.set_title(
            "Sector Cash Flow Profile",
            fontsize=13,
            fontweight="bold",
        )

        ax.grid(
            axis="y",
            alpha=0.25,
        )

    else:
        ax.text(
            0.5,
            0.5,
            "Cash-flow data unavailable",
            ha="center",
            va="center",
        )
        ax.axis("off")

    fig.tight_layout()
    fig.savefig(
        path,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(fig)


# ============================================================
# REPORT STYLES
# ============================================================

def get_styles():
    """Create ReportLab styles."""

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        "SectorTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    subtitle = ParagraphStyle(
        "SectorSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=10,
    )

    heading = ParagraphStyle(
        "SectorHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        spaceBefore=5,
        spaceAfter=5,
    )

    body = ParagraphStyle(
        "SectorBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    small = ParagraphStyle(
        "SectorSmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        alignment=TA_CENTER,
    )

    table_body = ParagraphStyle(
        "TableBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=7.5,
        alignment=TA_CENTER,
    )

    return {
        "title": title,
        "subtitle": subtitle,
        "heading": heading,
        "body": body,
        "small": small,
        "table_header": table_header,
        "table_body": table_body,
    }


# ============================================================
# KPI TABLE
# ============================================================

def create_kpi_table(metrics, styles):
    """Create KPI tiles."""

    data = [
        [
            Paragraph(
                "<b>Companies</b>",
                styles["table_header"],
            ),
            Paragraph(
                "<b>Median P/E</b>",
                styles["table_header"],
            ),
            Paragraph(
                "<b>Median P/B</b>",
                styles["table_header"],
            ),
            Paragraph(
                "<b>Median EV/EBITDA</b>",
                styles["table_header"],
            ),
            Paragraph(
                "<b>FCF Yield</b>",
                styles["table_header"],
            ),
        ],
        [
            Paragraph(
                str(metrics["companies"]),
                styles["table_body"],
            ),
            Paragraph(
                fmt_number(metrics["pe"]),
                styles["table_body"],
            ),
            Paragraph(
                fmt_number(metrics["pb"]),
                styles["table_body"],
            ),
            Paragraph(
                fmt_number(metrics["ev_ebitda"]),
                styles["table_body"],
            ),
            Paragraph(
                fmt_pct(metrics["fcf_yield"]),
                styles["table_body"],
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            35 * mm,
            35 * mm,
            35 * mm,
            42 * mm,
            35 * mm,
        ],
        rowHeights=[
            8 * mm,
            10 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8E8E8"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#BBBBBB"),
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
            ]
        )
    )

    return table


# ============================================================
# COMPANY TABLE
# ============================================================

def create_company_table(df, styles):
    """Create compact company comparison table."""

    columns = [
        ("Company", "company_name"),
        ("P/E", "p/e"),
        ("P/B", "p/b"),
        ("EV/EBITDA", "ev/ebitda"),
        ("ROE", "roe"),
        ("ROCE", "roce"),
        ("FCF Yield", "fcf_yield_pct"),
    ]

    rows = [
        [
            Paragraph(
                label,
                styles["table_header"],
            )
            for label, _ in columns
        ]
    ]

    # Sort by company name and cap table size.
    display_df = df.copy()

    if "company_name" in display_df.columns:
        display_df = display_df.sort_values(
            "company_name"
        )

    # Keep the report readable for large sectors.
    display_df = display_df.head(30)

    for _, row in display_df.iterrows():

        company = clean_text(
            row.get("company_name"),
            row.get("company_id", "N/A"),
        )

        if len(company) > 25:
            company = company[:22] + "..."

        values = [
            company,
            fmt_number(row.get("p/e")),
            fmt_number(row.get("p/b")),
            fmt_number(row.get("ev/ebitda")),
            fmt_pct(row.get("roe")),
            fmt_pct(row.get("roce")),
            fmt_pct(row.get("fcf_yield_pct")),
        ]

        rows.append(
            [
                Paragraph(
                    str(value),
                    styles["table_body"],
                )
                for value in values
            ]
        )

    table = Table(
        rows,
        colWidths=[
            49 * mm,
            19 * mm,
            19 * mm,
            27 * mm,
            19 * mm,
            19 * mm,
            25 * mm,
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
                    colors.HexColor("#E8E8E8"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.HexColor("#BBBBBB"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    return table


# ============================================================
# INSIGHTS
# ============================================================

def build_sector_insights(df, metrics):
    """Generate concise sector insights."""

    insights = []

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    pe = metrics["pe"]

    if not pd.isna(pe):
        if pe < 15:
            insights.append(
                f"The sector trades at a relatively low median P/E of "
                f"{pe:.1f}x, indicating comparatively moderate valuation."
            )
        elif pe > 30:
            insights.append(
                f"The sector has a relatively high median P/E of "
                f"{pe:.1f}x, suggesting elevated growth expectations."
            )
        else:
            insights.append(
                f"The sector median P/E is {pe:.1f}x, indicating a "
                f"mid-range valuation profile."
            )

    # --------------------------------------------------------
    # Profitability
    # --------------------------------------------------------

    roe = metrics["roe"]
    roce = metrics["roce"]

    if not pd.isna(roe):
        if roe >= 20:
            insights.append(
                f"Average ROE is strong at {roe:.1f}%, indicating "
                f"healthy shareholder returns."
            )
        elif roe < 10:
            insights.append(
                f"Average ROE is relatively low at {roe:.1f}%, "
                f"highlighting weaker return efficiency."
            )
        else:
            insights.append(
                f"Average ROE stands at {roe:.1f}%."
            )

    if not pd.isna(roce):
        insights.append(
            f"Average ROCE is {roce:.1f}%, providing a view of "
            f"capital efficiency."
        )

    # --------------------------------------------------------
    # FCF
    # --------------------------------------------------------

    fcf = metrics["fcf_yield"]

    if not pd.isna(fcf):
        if fcf > 5:
            insights.append(
                f"Median FCF yield is {fcf:.1f}%, suggesting "
                f"meaningful free-cash-flow generation."
            )
        elif fcf < 0:
            insights.append(
                f"Median FCF yield is negative at {fcf:.1f}%, "
                f"indicating cash-flow pressure."
            )

    # --------------------------------------------------------
    # NLP signals
    # --------------------------------------------------------

    pros = metrics["pros"]
    cons = metrics["cons"]

    if pros > cons:
        insights.append(
            f"NLP-derived signals are tilted positively, with "
            f"{int(pros)} pros versus {int(cons)} cons."
        )
    elif cons > pros:
        insights.append(
            f"NLP-derived signals show more concerns, with "
            f"{int(cons)} cons versus {int(pros)} pros."
        )
    else:
        insights.append(
            f"NLP-derived signals are balanced at "
            f"{int(pros)} pros and {int(cons)} cons."
        )

    if not insights:
        insights.append(
            "Insufficient data is available to generate sector-level insights."
        )

    return insights[:5]


# ============================================================
# PAGE FOOTER
# ============================================================

def add_page_number(canvas, doc):
    """Add footer page number."""

    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.grey
    )

    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        8 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# BUILD REPORT
# ============================================================

def build_sector_report(
    sector,
    sector_df,
    image_dir,
):
    """Generate one two-page sector report."""

    styles = get_styles()

    filename = (
        SECTOR_DIR
        / f"{safe_filename(sector)}_sector_report.pdf"
    )

    metrics = calculate_sector_metrics(
        sector_df
    )

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    image_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    slug = sector_slug(sector)

    valuation_chart = (
        image_dir
        / f"{slug}_valuation.png"
    )

    returns_chart = (
        image_dir
        / f"{slug}_returns.png"
    )

    cashflow_chart = (
        image_dir
        / f"{slug}_cashflow.png"
    )

    create_valuation_chart(
        sector_df,
        valuation_chart,
    )

    create_returns_chart(
        sector_df,
        returns_chart,
    )

    create_cashflow_chart(
        sector_df,
        cashflow_chart,
    )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=12 * mm,
        title=f"{sector} Sector Report",
        author="Nifty100 Analytics",
    )

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        Paragraph(
            f"{clean_text(sector)}",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Nifty 100 Sector Intelligence Report",
            styles["subtitle"],
        )
    )

    story.append(
        create_kpi_table(
            metrics,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # Valuation
    story.append(
        Paragraph(
            "Valuation",
            styles["heading"],
        )
    )

    story.append(
        Image(
            str(valuation_chart),
            width=178 * mm,
            height=69 * mm,
        )
    )

    # Profitability
    story.append(
        Paragraph(
            "Profitability",
            styles["heading"],
        )
    )

    story.append(
        Image(
            str(returns_chart),
            width=178 * mm,
            height=69 * mm,
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        Paragraph(
            f"{clean_text(sector)} — Cash Flow & Companies",
            styles["heading"],
        )
    )

    story.append(
        Image(
            str(cashflow_chart),
            width=178 * mm,
            height=63 * mm,
        )
    )

    # --------------------------------------------------------
    # Insights
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Sector Insights",
            styles["heading"],
        )
    )

    insights = build_sector_insights(
        sector_df,
        metrics,
    )

    insight_rows = []

    for i, insight in enumerate(insights, start=1):
        insight_rows.append(
            [
                Paragraph(
                    f"<b>{i}.</b>",
                    styles["body"],
                ),
                Paragraph(
                    insight,
                    styles["body"],
                ),
            ]
        )

    insight_table = Table(
        insight_rows,
        colWidths=[
            8 * mm,
            170 * mm,
        ],
    )

    insight_table.setStyle(
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
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(
        insight_table
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    # --------------------------------------------------------
    # Company comparison
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Company Comparison",
            styles["heading"],
        )
    )

    story.append(
        create_company_table(
            sector_df,
            styles,
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    story.append(
        Paragraph(
            "Source: Nifty100 Analytics project outputs. "
            "Sector classification is taken from valuation_summary.xlsx. "
            "Metrics may be unavailable for companies with missing source data.",
            styles["small"],
        )
    )

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return filename


# ============================================================
# VALIDATION
# ============================================================

def validate_pdf(path):
    """Validate PDF size and page count."""

    if not path.exists():
        return False, "file does not exist"

    size = path.stat().st_size

    if size < MIN_PDF_BYTES:
        return False, (
            f"file too small: {size:,} bytes"
        )

    try:
        reader = PdfReader(
            str(path)
        )

        pages = len(reader.pages)

    except Exception as exc:
        return False, (
            f"PDF read failed: {exc}"
        )

    if pages != EXPECTED_PAGES:
        return False, (
            f"expected {EXPECTED_PAGES} pages, got {pages}"
        )

    return True, (
        f"{size:,} bytes, pages={pages}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SPRINT 5 - DAY 34")
    print("SECTOR REPORT GENERATOR")
    print("=" * 70)

    # --------------------------------------------------------
    # Load inputs
    # --------------------------------------------------------

    print("\n[1/6] Loading company universe...")

    universe = load_universe()

    print(
        f"      Companies in database: {len(universe)}"
    )

    print("\n[2/6] Loading valuation data...")

    valuation = load_valuation()

    print(
        f"      Valuation rows: {len(valuation)}"
    )

    print("\n[3/6] Loading cash-flow data...")

    cashflow = load_cashflow()

    print(
        f"      Cash-flow rows: {len(cashflow)}"
    )

    print("\n[4/6] Loading pros/cons data...")

    pros_cons = load_pros_cons()

    print(
        f"      Pros/cons rows: {len(pros_cons)}"
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    print("\n[5/6] Preparing sector dataset...")

    merged = prepare_sector_data(
        universe,
        valuation,
        cashflow,
        pros_cons,
    )

    merged["sector"] = (
        merged["sector"]
        .astype(str)
        .str.strip()
    )

    merged = merged[
        merged["sector"].notna()
        & (merged["sector"] != "")
        & (merged["sector"].str.lower() != "nan")
    ].copy()

    sectors = sorted(
        merged["sector"].unique()
    )

    print(
        f"      Sectors discovered: {len(sectors)}"
    )

    for sector in sectors:
        count = (
            merged[
                merged["sector"] == sector
            ]
            .shape[0]
        )

        print(
            f"        - {sector}: {count} companies"
        )

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    print("\n[6/6] Generating sector reports...")

    image_dir = SECTOR_DIR / "_charts"

    results = []

    for sector in sectors:

        sector_df = merged[
            merged["sector"] == sector
        ].copy()

        try:

            pdf_path = build_sector_report(
                sector,
                sector_df,
                image_dir,
            )

            valid, message = validate_pdf(
                pdf_path
            )

            if valid:
                print(
                    f"      PASS {sector}: {message}"
                )

                results.append(
                    (
                        sector,
                        True,
                        pdf_path,
                    )
                )

            else:
                print(
                    f"      FAIL {sector}: {message}"
                )

                results.append(
                    (
                        sector,
                        False,
                        pdf_path,
                    )
                )

        except Exception as exc:

            print(
                f"      FAIL {sector}: {exc}"
            )

            results.append(
                (
                    sector,
                    False,
                    None,
                )
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    passed = sum(
        1
        for _, ok, _ in results
        if ok
    )

    failed = len(results) - passed

    print("\n" + "=" * 70)
    print("DAY 34 VALIDATION")
    print("=" * 70)

    print(
        f"Sectors discovered : {len(sectors)}"
    )

    print(
        f"Reports generated  : {len(results)}"
    )

    print(
        f"Passed             : {passed}"
    )

    print(
        f"Failed             : {failed}"
    )

    print(
        f"Output directory   : {SECTOR_DIR}"
    )

    if failed == 0 and len(results) > 0:
        print("\nDAY 34 PASS")
    else:
        print("\nDAY 34 FAIL")

    print("=" * 70)

    return 0 if failed == 0 and len(results) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )