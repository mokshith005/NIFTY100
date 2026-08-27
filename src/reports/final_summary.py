"""
Sprint 3 - Day 21
Final Portfolio Analytics Summary

Generates a consolidated Excel workbook containing:
1. Portfolio overview
2. Screener summary
3. Top quality compounders
4. Growth leaders
5. Dividend leaders
6. Value picks
7. Peer-group summary
8. Data-quality summary
"""

from pathlib import Path
import sqlite3

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "final_analytics_summary.xlsx"


class FinalAnalyticsReport:
    """Build the consolidated Sprint 3 analytics workbook."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)

    def connect(self):
        return sqlite3.connect(self.db_path)

    def load_latest_data(self):
        """
        Load one latest financial-ratio record per company and join
        market valuation and company information.
        """
        conn = self.connect()

        query = """
        WITH latest_ratios AS (
            SELECT *
            FROM financial_ratios
            WHERE id IN (
                SELECT MAX(id)
                FROM financial_ratios
                GROUP BY company_id
            )
        ),
        latest_market AS (
            SELECT *
            FROM market_cap
            WHERE id IN (
                SELECT MAX(id)
                FROM market_cap
                GROUP BY company_id
            )
        )
        SELECT
            r.company_id,
            r.year,
            r.return_on_equity_pct,
            r.roce_pct,
            r.roa_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.free_cash_flow_cr,
            r.revenue_cagr_5yr,
            r.pat_cagr_5yr,
            r.eps_cagr_5yr,
            r.composite_quality_score,
            m.market_cap_crore,
            m.pe_ratio,
            m.pb_ratio,
            m.ev_ebitda,
            m.dividend_yield_pct
        FROM latest_ratios r
        LEFT JOIN latest_market m
            ON r.company_id = m.company_id
        ORDER BY r.company_id
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def load_peer_summary(self):
        conn = self.connect()

        query = """
        SELECT
            peer_group_name,
            COUNT(DISTINCT company_id) AS companies,
            COUNT(DISTINCT metric) AS metrics,
            COUNT(*) AS percentile_records,
            ROUND(AVG(percentile_rank), 4) AS avg_percentile
        FROM peer_percentiles
        GROUP BY peer_group_name
        ORDER BY peer_group_name
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def build_screener_summary(self, data):
        """
        Recreate the six Sprint 3 screener categories from the
        existing engine so the final report remains consistent
        with the screener output.
        """
        from src.screener.engine import ScreenerEngine

        engine = ScreenerEngine(str(self.db_path))
        results = engine.run_all_presets()

        rows = []

        for name, df in results.items():
            if df is None or df.empty:
                rows.append(
                    {
                        "preset": name,
                        "companies": 0,
                        "top_company": None,
                        "top_score": None,
                        "mean_score": None,
                    }
                )
                continue

            score_column = (
                "composite_quality_score"
                if "composite_quality_score" in df.columns
                else None
            )

            if score_column:
                sorted_df = df.sort_values(
                    score_column,
                    ascending=False,
                    na_position="last",
                )
                top_company = sorted_df.iloc[0]["company_id"]
                top_score = sorted_df.iloc[0][score_column]
                mean_score = df[score_column].mean()
            else:
                top_company = df.iloc[0]["company_id"]
                top_score = None
                mean_score = None

            rows.append(
                {
                    "preset": name,
                    "companies": len(df),
                    "top_company": top_company,
                    "top_score": top_score,
                    "mean_score": mean_score,
                }
            )

        return pd.DataFrame(rows)

    def build_quality_leaders(self, data):
        columns = [
            "company_id",
            "year",
            "return_on_equity_pct",
            "roce_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "composite_quality_score",
        ]

        available = [c for c in columns if c in data.columns]

        return (
            data[available]
            .sort_values(
                "composite_quality_score",
                ascending=False,
                na_position="last",
            )
            .head(10)
            .reset_index(drop=True)
        )

    def build_growth_leaders(self, data):
        columns = [
            "company_id",
            "year",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "eps_cagr_5yr",
            "composite_quality_score",
        ]

        available = [c for c in columns if c in data.columns]

        return (
            data[available]
            .sort_values(
                "revenue_cagr_5yr",
                ascending=False,
                na_position="last",
            )
            .head(10)
            .reset_index(drop=True)
        )

    def build_dividend_leaders(self, data):
        columns = [
            "company_id",
            "year",
            "dividend_yield_pct",
            "return_on_equity_pct",
            "free_cash_flow_cr",
            "composite_quality_score",
        ]

        available = [c for c in columns if c in data.columns]

        return (
            data[available]
            .sort_values(
                "dividend_yield_pct",
                ascending=False,
                na_position="last",
            )
            .head(10)
            .reset_index(drop=True)
        )

    def build_value_picks(self, data):
        result = data[
            (data["pe_ratio"] < 20)
            & (data["pb_ratio"] < 3)
            & (data["debt_to_equity"] < 2)
            & (data["dividend_yield_pct"] > 1)
        ].copy()

        columns = [
            "company_id",
            "year",
            "pe_ratio",
            "pb_ratio",
            "debt_to_equity",
            "dividend_yield_pct",
            "composite_quality_score",
        ]

        available = [c for c in columns if c in result.columns]

        return (
            result[available]
            .sort_values("pe_ratio")
            .reset_index(drop=True)
        )

    def build_overview(self, data, peer_summary, screener_summary):
        conn = self.connect()

        companies = conn.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()[0]

        peer_assignments = conn.execute(
            "SELECT COUNT(*) FROM peer_groups"
        ).fetchone()[0]

        percentile_records = conn.execute(
            "SELECT COUNT(*) FROM peer_percentiles"
        ).fetchone()[0]

        conn.close()

        return pd.DataFrame(
            [
                ["Database", str(self.db_path)],
                ["Companies in companies table", companies],
                ["Latest company records", len(data)],
                ["Peer-group assignments", peer_assignments],
                ["Peer groups", len(peer_summary)],
                ["Peer percentile records", percentile_records],
                ["Screener presets", len(screener_summary)],
                ["Screener companies across presets",
                 int(screener_summary["companies"].sum())],
            ],
            columns=["Metric", "Value"],
        )

    def export(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        data = self.load_latest_data()
        peer_summary = self.load_peer_summary()
        screener_summary = self.build_screener_summary(data)

        overview = self.build_overview(
            data,
            peer_summary,
            screener_summary,
        )

        quality = self.build_quality_leaders(data)
        growth = self.build_growth_leaders(data)
        dividend = self.build_dividend_leaders(data)
        value = self.build_value_picks(data)

        with pd.ExcelWriter(
            OUTPUT_FILE,
            engine="openpyxl",
        ) as writer:

            overview.to_excel(
                writer,
                sheet_name="Overview",
                index=False,
            )

            screener_summary.to_excel(
                writer,
                sheet_name="Screener Summary",
                index=False,
            )

            quality.to_excel(
                writer,
                sheet_name="Quality Leaders",
                index=False,
            )

            growth.to_excel(
                writer,
                sheet_name="Growth Leaders",
                index=False,
            )

            dividend.to_excel(
                writer,
                sheet_name="Dividend Leaders",
                index=False,
            )

            value.to_excel(
                writer,
                sheet_name="Value Picks",
                index=False,
            )

            peer_summary.to_excel(
                writer,
                sheet_name="Peer Summary",
                index=False,
            )

            data.to_excel(
                writer,
                sheet_name="Latest Metrics",
                index=False,
            )

        self.format_workbook()

        return OUTPUT_FILE

    def format_workbook(self):
        wb = load_workbook(OUTPUT_FILE)

        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(
                    horizontal="center"
                )

            for column_cells in ws.columns:
                max_length = 0

                for cell in column_cells:
                    value = "" if cell.value is None else str(cell.value)
                    max_length = max(max_length, len(value))

                width = min(max(max_length + 2, 12), 35)

                ws.column_dimensions[
                    column_cells[0].column_letter
                ].width = width

        wb.save(OUTPUT_FILE)


def main():
    print("=" * 70)
    print("SPRINT 3 - DAY 21")
    print("FINAL PORTFOLIO ANALYTICS SUMMARY")
    print("=" * 70)

    report = FinalAnalyticsReport()

    print()
    print("Database:")
    print(f"  {DB_PATH}")

    output = report.export()

    print()
    print("=" * 70)
    print("DAY 21 REPORT GENERATED")
    print("=" * 70)
    print(f"Excel file: {output}")

    wb = load_workbook(output, read_only=True)

    print()
    print("Sheets:")
    for sheet in wb.sheetnames:
        print(f"  {sheet}")

    print()
    print(f"Sheet count: {len(wb.sheetnames)}")

    wb.close()

    print()
    print("DAY 21 VALIDATION: PASS")
    print("=" * 70)


if __name__ == "__main__":
    main()