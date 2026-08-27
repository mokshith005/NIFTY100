"""
Sprint 3 - Day 20
Peer Comparison Excel Report

Output:
    output/peer_comparison.xlsx

Requirements:
- Exactly 11 peer-group sheets
- Company + 20 metric columns
- Percentile rank for each metric
- Green >= 75th percentile
- Yellow 25th to <75th percentile
- Red <25th percentile
- Benchmark company highlighted
- Peer-group median summary row
"""

from pathlib import Path
import sqlite3

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter


# ================================================================
# PATHS
# ================================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

DB_PATH = ROOT_DIR / "db" / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE = OUTPUT_DIR / "peer_comparison.xlsx"


# ================================================================
# METRICS
# ================================================================

METRICS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "roce_pct",
    "NPM": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "EPS CAGR 5yr": "eps_cagr_5yr",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
}

# Excel needs value + percentile for each metric.
# 10 metrics x 2 = 20 metric columns.


# ================================================================
# DATABASE
# ================================================================

class PeerComparisonEngine:

    def __init__(self, db_path=DB_PATH):

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {self.db_path}"
            )

    # ============================================================
    # LOAD PEER GROUPS
    # ============================================================

    def load_peer_groups(self):

        query = """
        SELECT
            peer_group_name,
            company_id,
            is_benchmark
        FROM peer_groups
        ORDER BY peer_group_name, company_id
        """

        with sqlite3.connect(
            self.db_path
        ) as conn:

            return pd.read_sql_query(
                query,
                conn,
            )

    # ============================================================
    # COMPANY NAMES
    # ============================================================

    def load_company_names(self):

        query = """
        SELECT
            company_id,
            company_name
        FROM companies
        """

        with sqlite3.connect(
            self.db_path
        ) as conn:

            try:
                return pd.read_sql_query(
                    query,
                    conn,
                )

            except Exception:

                # Some versions of the database may not contain
                # company_name. Fall back to company_id.

                return pd.DataFrame(
                    columns=[
                        "company_id",
                        "company_name",
                    ]
                )

    # ============================================================
    # LOAD FINANCIAL DATA
    # ============================================================

    def load_financial_data(self):

        query = """
        WITH latest_ratios AS (

            SELECT
                fr.*,

                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY CAST(fr.year AS REAL) DESC
                ) AS rn

            FROM financial_ratios fr
        )

        SELECT
            company_id,
            year,
            return_on_equity_pct,
            roce_pct,
            net_profit_margin_pct,
            debt_to_equity,
            free_cash_flow_cr,
            pat_cagr_5yr,
            revenue_cagr_5yr,
            eps_cagr_5yr,
            interest_coverage,
            asset_turnover

        FROM latest_ratios

        WHERE rn = 1
        """

        with sqlite3.connect(
            self.db_path
        ) as conn:

            return pd.read_sql_query(
                query,
                conn,
            )

    # ============================================================
    # LOAD PEER PERCENTILES
    # ============================================================

    def load_percentiles(self):

        query = """
        SELECT
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
        """

        with sqlite3.connect(
            self.db_path
        ) as conn:

            return pd.read_sql_query(
                query,
                conn,
            )

    # ============================================================
    # BUILD ONE PEER SHEET
    # ============================================================

    def build_group_dataframe(
        self,
        peer_group,
        assignments,
        financial,
        percentiles,
        company_names,
    ):

        group_assignments = assignments[
            assignments["peer_group_name"]
            == peer_group
        ].copy()

        # --------------------------------------------------------
        # Start with company IDs
        # --------------------------------------------------------

        result = group_assignments[
            [
                "company_id",
                "is_benchmark",
            ]
        ].copy()

        # --------------------------------------------------------
        # Add company name
        # --------------------------------------------------------

        if (
            not company_names.empty
            and "company_name"
            in company_names.columns
        ):

            result = result.merge(
                company_names[
                    [
                        "company_id",
                        "company_name",
                    ]
                ],
                on="company_id",
                how="left",
            )

        else:

            result["company_name"] = (
                result["company_id"]
            )

        # --------------------------------------------------------
        # Add financial metric values
        # --------------------------------------------------------

        metric_columns = list(
            METRICS.values()
        )

        available = [
            column
            for column in metric_columns
            if column in financial.columns
        ]

        financial_subset = financial[
            [
                "company_id"
            ]
            + available
        ].copy()

        result = result.merge(
            financial_subset,
            on="company_id",
            how="left",
        )

        # --------------------------------------------------------
        # Rename financial columns to readable names
        # --------------------------------------------------------

        reverse_metrics = {
            value: key
            for key, value in METRICS.items()
        }

        result.rename(
            columns=reverse_metrics,
            inplace=True,
        )

        # --------------------------------------------------------
        # Add percentile columns
        # --------------------------------------------------------

        group_percentiles = percentiles[
            percentiles[
                "peer_group_name"
            ]
            == peer_group
        ].copy()

        for metric in METRICS.keys():

            metric_rows = group_percentiles[
                group_percentiles[
                    "metric"
                ]
                == metric
            ][
                [
                    "company_id",
                    "percentile_rank",
                ]
            ].copy()

            percentile_column = (
                f"{metric} Percentile"
            )

            metric_rows.rename(
                columns={
                    "percentile_rank":
                        percentile_column
                },
                inplace=True,
            )

            result = result.merge(
                metric_rows,
                on="company_id",
                how="left",
            )

        # --------------------------------------------------------
        # Clean up benchmark marker
        # --------------------------------------------------------

        result["Benchmark"] = (
            result["is_benchmark"]
            .astype(bool)
        )

        result.drop(
            columns=["is_benchmark"],
            inplace=True,
        )

        # --------------------------------------------------------
        # Reorder columns
        # --------------------------------------------------------

        columns = [
            "company_id",
            "company_name",
        ]

        for metric in METRICS.keys():

            columns.append(metric)

            columns.append(
                f"{metric} Percentile"
            )

        columns.append("Benchmark")

        result = result[
            [
                column
                for column in columns
                if column in result.columns
            ]
        ]

        return result

    # ============================================================
    # ADD MEDIAN ROW
    # ============================================================

    def add_median_row(
        self,
        dataframe,
    ):

        median = {}

        for column in dataframe.columns:

            if column in (
                "company_id",
                "company_name",
                "Benchmark",
            ):

                median[column] = ""

            else:

                median[column] = pd.to_numeric(
                    dataframe[column],
                    errors="coerce",
                ).median()

        median["company_id"] = "PEER GROUP MEDIAN"
        median["company_name"] = "Median"

        return pd.concat(
            [
                dataframe,
                pd.DataFrame(
                    [median]
                ),
            ],
            ignore_index=True,
        )

    # ============================================================
    # EXPORT
    # ============================================================

    def export(self):

        assignments = (
            self.load_peer_groups()
        )

        financial = (
            self.load_financial_data()
        )

        percentiles = (
            self.load_percentiles()
        )

        company_names = (
            self.load_company_names()
        )

        peer_groups = sorted(
            assignments[
                "peer_group_name"
            ].dropna().unique()
        )

        print(
            f"Peer groups found: {len(peer_groups)}"
        )

        # --------------------------------------------------------
        # Excel writer
        # --------------------------------------------------------

        with pd.ExcelWriter(
            OUTPUT_FILE,
            engine="openpyxl",
        ) as writer:

            for peer_group in peer_groups:

                print(
                    f"Generating: {peer_group}"
                )

                df = self.build_group_dataframe(
                    peer_group,
                    assignments,
                    financial,
                    percentiles,
                    company_names,
                )

                df = self.add_median_row(
                    df
                )

                # Excel sheet names max 31 chars

                sheet_name = peer_group[:31]

                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                )

        return peer_groups


# ================================================================
# EXCEL FORMATTING
# ================================================================

def format_workbook():

    workbook = load_workbook(
        OUTPUT_FILE
    )

    # ------------------------------------------------------------
    # Fills
    # ------------------------------------------------------------

    green_fill = PatternFill(
        fill_type="solid",
        fgColor="C6EFCE",
    )

    yellow_fill = PatternFill(
        fill_type="solid",
        fgColor="FFEB9C",
    )

    red_fill = PatternFill(
        fill_type="solid",
        fgColor="FFC7CE",
    )

    benchmark_fill = PatternFill(
        fill_type="solid",
        fgColor="FFD966",
    )

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="D9EAF7",
    )

    median_fill = PatternFill(
        fill_type="solid",
        fgColor="E7E6E6",
    )

    # ------------------------------------------------------------
    # Process every sheet
    # ------------------------------------------------------------

    for worksheet in workbook.worksheets:

        max_row = worksheet.max_row
        max_column = worksheet.max_column

        # --------------------------------------------------------
        # Header
        # --------------------------------------------------------

        for cell in worksheet[1]:

            cell.font = Font(
                bold=True
            )

            cell.fill = header_fill

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        worksheet.freeze_panes = "C2"

        worksheet.auto_filter.ref = (
            worksheet.dimensions
        )

        # --------------------------------------------------------
        # Find columns
        # --------------------------------------------------------

        headers = {
            worksheet.cell(
                row=1,
                column=column
            ).value: column

            for column in range(
                1,
                max_column + 1
            )
        }

        percentile_columns = [
            column
            for name, column in headers.items()
            if name
            and "Percentile"
            in str(name)
        ]

        benchmark_column = headers.get(
            "Benchmark"
        )

        company_id_column = headers.get(
            "company_id"
        )

        # --------------------------------------------------------
        # Data rows
        # --------------------------------------------------------

        median_row = max_row

        for row in range(
            2,
            max_row + 1
        ):

            is_median = (
                worksheet.cell(
                    row=row,
                    column=company_id_column,
                ).value
                == "PEER GROUP MEDIAN"
            )

            # ----------------------------------------------------
            # Median row
            # ----------------------------------------------------

            if is_median:

                for column in range(
                    1,
                    max_column + 1
                ):

                    cell = worksheet.cell(
                        row=row,
                        column=column,
                    )

                    cell.fill = median_fill
                    cell.font = Font(
                        bold=True
                    )

                continue

            # ----------------------------------------------------
            # Benchmark row
            # ----------------------------------------------------

            is_benchmark = False

            if benchmark_column:

                benchmark_value = (
                    worksheet.cell(
                        row=row,
                        column=benchmark_column,
                    ).value
                )

                is_benchmark = (
                    benchmark_value is True
                    or benchmark_value == 1
                    or str(
                        benchmark_value
                    ).lower()
                    == "true"
                )

            if is_benchmark:

                for column in range(
                    1,
                    max_column + 1
                ):

                    worksheet.cell(
                        row=row,
                        column=column,
                    ).fill = benchmark_fill

            # ----------------------------------------------------
            # Percentile colouring
            # ----------------------------------------------------

            for column in percentile_columns:

                cell = worksheet.cell(
                    row=row,
                    column=column,
                )

                value = cell.value

                if value is None:
                    continue

                try:
                    percentile = float(
                        value
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                # Values are stored as 0-1

                if percentile >= 0.75:

                    cell.fill = green_fill

                elif percentile <= 0.25:

                    cell.fill = red_fill

                else:

                    cell.fill = yellow_fill

        # --------------------------------------------------------
        # Number formats
        # --------------------------------------------------------

        for row in worksheet.iter_rows(
            min_row=2,
            max_row=max_row,
        ):

            for cell in row:

                if isinstance(
                    cell.value,
                    (int, float),
                ):

                    cell.number_format = (
                        "0.00"
                    )

        # --------------------------------------------------------
        # Percentile format
        # --------------------------------------------------------

        for column in percentile_columns:

            for row in range(
                2,
                max_row + 1
            ):

                worksheet.cell(
                    row=row,
                    column=column,
                ).number_format = (
                    "0%"
                )

        # --------------------------------------------------------
        # Hide Benchmark helper column
        # --------------------------------------------------------

        if benchmark_column:

            worksheet.column_dimensions[
                get_column_letter(
                    benchmark_column
                )
            ].hidden = True

        # --------------------------------------------------------
        # Column widths
        # --------------------------------------------------------

        for column in range(
            1,
            max_column + 1
        ):

            letter = get_column_letter(
                column
            )

            header = worksheet.cell(
                row=1,
                column=column,
            ).value

            if header in (
                "company_id",
                "company_name",
            ):

                width = 20

            else:

                width = 16

            worksheet.column_dimensions[
                letter
            ].width = width

        worksheet.row_dimensions[
            1
        ].height = 32

    # ------------------------------------------------------------
    # Save
    # ------------------------------------------------------------

    workbook.save(
        OUTPUT_FILE
    )


# ================================================================
# VALIDATION
# ================================================================

def validate():

    print("\n" + "=" * 70)
    print("DAY 20 PEER COMPARISON VALIDATION")
    print("=" * 70)

    workbook = load_workbook(
        OUTPUT_FILE,
        read_only=True,
        data_only=True,
    )

    sheets = workbook.sheetnames

    print(
        f"Output file             : {OUTPUT_FILE}"
    )

    print(
        f"Sheets                  : {len(sheets)}"
    )

    print(
        f"Sheet names             : {sheets}"
    )

    expected = 11

    if len(sheets) == expected:

        print(
            "Sheet count check       : PASS"
        )

    else:

        print(
            "Sheet count check       : FAIL"
        )

    total_rows = 0

    for sheet in sheets:

        ws = workbook[sheet]

        rows = ws.max_row
        columns = ws.max_column

        total_rows += rows

        print(
            f"  {sheet:<25} "
            f"rows={rows:<4} "
            f"columns={columns}"
        )

    workbook.close()

    print(
        f"\nTotal worksheet rows    : {total_rows}"
    )

    if len(sheets) == 11:

        print(
            "\nDAY 20 VALIDATION: PASS"
        )

    else:

        print(
            "\nDAY 20 VALIDATION: CHECK"
        )

    print("=" * 70)


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print("SPRINT 3 - DAY 20")
    print("PEER COMPARISON EXCEL REPORT")
    print("=" * 70)

    engine = PeerComparisonEngine()

    print(
        f"\nDatabase: {DB_PATH}"
    )

    peer_groups = engine.export()

    print(
        f"\nPeer groups exported: "
        f"{len(peer_groups)}"
    )

    format_workbook()

    print(
        f"\nExcel generated:"
    )

    print(
        f"  {OUTPUT_FILE}"
    )

    validate()


if __name__ == "__main__":
    main()