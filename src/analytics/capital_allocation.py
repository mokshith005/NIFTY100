"""
Sprint 2 - Day 11
Generate capital allocation classifications for all
available company-year cash-flow records.
"""

from pathlib import Path

import sqlite3
import pandas as pd

from src.analytics.cashflow_kpis import (
    calculate_cfo_pat_5yr,
    capital_allocation_pattern,
)


DB_PATH = Path("db/nifty100.db")
OUTPUT_PATH = Path("output/capital_allocation.csv")


def generate_capital_allocation():
    """
    Generate capital allocation classifications.

    The classification uses:
        CFO = operating_activity
        CFI = investing_activity
        CFF = financing_activity

    For (+,-,-), the latest five common CFO/PAT years
    are used to calculate the average CFO/PAT ratio.
    """

    conn = sqlite3.connect(DB_PATH)

    cashflow = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_activity AS cfo,
            investing_activity AS cfi,
            financing_activity AS cff
        FROM cashflow
        ORDER BY company_id, year
        """,
        conn,
    )

    profit_loss = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            net_profit AS pat
        FROM profitandloss
        ORDER BY company_id, year
        """,
        conn,
    )

    conn.close()

    results = []

    companies = sorted(
        set(cashflow["company_id"].dropna())
    )

    for company_id in companies:

        company_cashflow = cashflow[
            cashflow["company_id"] == company_id
        ].copy()

        company_pat = profit_loss[
            profit_loss["company_id"] == company_id
        ].copy()

        # Calculate latest 5-year CFO/PAT average.
        cfo_rows = list(
            company_cashflow[
                ["year", "cfo"]
            ].itertuples(index=False, name=None)
        )

        pat_rows = list(
            company_pat[
                ["year", "pat"]
            ].itertuples(index=False, name=None)
        )

        cfo_pat_5yr = calculate_cfo_pat_5yr(
            cfo_rows,
            pat_rows,
        )

        for _, row in company_cashflow.iterrows():

            cfo = row["cfo"]
            cfi = row["cfi"]
            cff = row["cff"]

            pattern_label = capital_allocation_pattern(
                cfo=cfo,
                cfi=cfi,
                cff=cff,
                cfo_quality=cfo_pat_5yr,
            )

            def sign(value):
                if pd.isna(value) or value == 0:
                    return "0"

                return "+" if value > 0 else "-"

            results.append(
                {
                    "company_id": company_id,
                    "year": row["year"],
                    "cfo_sign": sign(cfo),
                    "cfi_sign": sign(cfi),
                    "cff_sign": sign(cff),
                    "pattern_label": pattern_label,
                }
            )

    result = pd.DataFrame(
        results,
        columns=[
            "company_id",
            "year",
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ],
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("=" * 70)
    print("CAPITAL ALLOCATION GENERATION")
    print("=" * 70)

    print(f"Database: {DB_PATH}")
    print(f"Output:   {OUTPUT_PATH}")
    print(f"Rows:     {len(result)}")

    print("\nPattern distribution:")
    print(
        result["pattern_label"]
        .value_counts()
        .to_string()
    )

    print("\nSample:")
    print(
        result.head(10)
        .to_string(index=False)
    )

    return result


if __name__ == "__main__":
    generate_capital_allocation()