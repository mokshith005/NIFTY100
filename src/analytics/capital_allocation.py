"""
Sprint 5 - Day 32
Capital Allocation Intelligence

Generates yearly capital-allocation patterns, latest-year distribution,
pattern changes, and integrates the latest label into cashflow_intelligence.xlsx.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

from src.analytics.cashflow_kpis import capital_allocation_pattern


DB_PATH = Path("db/nifty100.db")
CAPITAL_OUTPUT = Path("output/capital_allocation.csv")
PATTERN_CHANGES = Path("output/pattern_changes.csv")
CASHFLOW_OUTPUT = Path("output/cashflow_intelligence.xlsx")


def num(x):
    try:
        if x is None or pd.isna(x):
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def normalize_year(x):
    try:
        return int(float(x))
    except Exception:
        return None


def main():
    print("=" * 70)
    print("SPRINT 5 - DAY 32")
    print("CAPITAL ALLOCATION INTELLIGENCE")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        "SELECT id AS company_id FROM companies",
        conn,
    )

    pnl = pd.read_sql_query(
        """
        SELECT company_id, year, sales, net_profit
        FROM profitandloss
        """,
        conn,
    )

    cf = pd.read_sql_query(
        """
        SELECT company_id, year,
               operating_activity,
               investing_activity,
               financing_activity,
               net_cash_flow
        FROM cashflow
        """,
        conn,
    )

    bs = pd.read_sql_query(
        """
        SELECT company_id, year, borrowings
        FROM balancesheet
        """,
        conn,
    )

    conn.close()

    print(f"Companies in universe : {len(companies)}")
    print(f"P&L rows              : {len(pnl)}")
    print(f"Cash-flow rows        : {len(cf)}")
    print(f"Balance-sheet rows    : {len(bs)}")

    for df in (pnl, cf, bs):
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df["year"] = df["year"].apply(normalize_year)

    pnl = pnl.dropna(subset=["year"])
    cf = cf.dropna(subset=["year"])
    bs = bs.dropna(subset=["year"])

    pnl = pnl.drop_duplicates(["company_id", "year"], keep="last")
    cf = cf.drop_duplicates(["company_id", "year"], keep="last")
    bs = bs.drop_duplicates(["company_id", "year"], keep="last")

    rows = []

    for company_id in companies["company_id"].astype(str):
        company_cf = cf[cf["company_id"] == company_id].copy()
        company_pnl = pnl[pnl["company_id"] == company_id].copy()
        company_bs = bs[bs["company_id"] == company_id].copy()

        if company_cf.empty:
            continue

        years = sorted(
            set(company_cf["year"].dropna())
            & set(company_pnl["year"].dropna())
        )

        previous_borrowings = None

        for year in years:
            cf_y = company_cf[company_cf["year"] == year]
            pnl_y = company_pnl[company_pnl["year"] == year]
            bs_y = company_bs[company_bs["year"] == year]

            if cf_y.empty:
                continue

            r = cf_y.iloc[-1]

            cfo = num(r["operating_activity"])
            cfi = num(r["investing_activity"])
            cff = num(r["financing_activity"])

            # Free cash flow = CFO + investing cash flow.
            fcf = cfo + cfi

            sales = num(pnl_y.iloc[-1]["sales"]) if not pnl_y.empty else 0.0
            net_profit = (
                num(pnl_y.iloc[-1]["net_profit"])
                if not pnl_y.empty
                else 0.0
            )

            if not bs_y.empty:
                borrowings = num(bs_y.iloc[-1]["borrowings"])
                if previous_borrowings is None:
                    borrowings_change = 0.0
                else:
                    borrowings_change = borrowings - previous_borrowings
                previous_borrowings = borrowings
            else:
                borrowings_change = 0.0

            try:
                label = capital_allocation_pattern(
                    cfo=cfo,
                    cfi=cfi,
                    cff=cff,
                    fcf=fcf,
                    borrowings_change=borrowings_change,
                    sales=sales,
                    net_profit=net_profit,
                )
            except TypeError:
                # Compatibility with the original Sprint 2 function.
                label = capital_allocation_pattern(
                    cfo=cfo,
                    cfi=cfi,
                    cff=cff,
                )

            rows.append(
                {
                    "company_id": company_id,
                    "year": year,
                    "cfo": cfo,
                    "cfi": cfi,
                    "cff": cff,
                    "fcf": fcf,
                    "borrowings_change": borrowings_change,
                    "pattern_label": label,
                }
            )

    patterns = pd.DataFrame(rows)

    CAPITAL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    patterns.to_csv(CAPITAL_OUTPUT, index=False)

    print(f"Capital allocation rows: {len(patterns)}")

    if patterns.empty:
        raise AssertionError("No capital allocation patterns generated.")

    latest_year = patterns.groupby("company_id")["year"].transform("max")
    latest = patterns[patterns["year"] == latest_year].copy()

    print()
    print("Latest-year capital allocation distribution:")
    distribution = (
        latest["pattern_label"]
        .value_counts()
        .reindex(
            [
                "Reinvestor",
                "Shareholder Returns",
                "Liquidating Assets",
                "Distress Signal",
                "Growth Funded by Debt",
                "Cash Accumulator",
                "Pre-Revenue",
                "Mixed",
            ],
            fill_value=0,
        )
    )

    print(distribution.to_string())

    # Pattern changes between latest two available years.
    changes = []

    for company_id, group in patterns.groupby("company_id"):
        group = group.sort_values("year")

        if len(group) < 2:
            continue

        previous = group.iloc[-2]
        current = group.iloc[-1]

        if previous["pattern_label"] != current["pattern_label"]:
            changes.append(
                {
                    "company_id": company_id,
                    "previous_year": previous["year"],
                    "previous_pattern": previous["pattern_label"],
                    "latest_year": current["year"],
                    "latest_pattern": current["pattern_label"],
                }
            )

    changes_df = pd.DataFrame(changes)

    if changes_df.empty:
        changes_df = pd.DataFrame(
            columns=[
                "company_id",
                "previous_year",
                "previous_pattern",
                "latest_year",
                "latest_pattern",
            ]
        )

    changes_df.to_csv(PATTERN_CHANGES, index=False)

    print(f"Pattern changes: {len(changes_df)}")

    # Integrate latest capital allocation into Day 31 workbook.
    if CASHFLOW_OUTPUT.exists():
        workbook = pd.read_excel(CASHFLOW_OUTPUT)

        latest_labels = latest[
            ["company_id", "pattern_label"]
        ].rename(
            columns={"pattern_label": "capital_allocation_label"}
        )

        workbook["company_id"] = workbook["company_id"].astype(str)
        latest_labels["company_id"] = latest_labels["company_id"].astype(str)

        workbook = workbook.drop(
            columns=["capital_allocation_label"],
            errors="ignore",
        )

        workbook = workbook.merge(
            latest_labels,
            on="company_id",
            how="left",
        )

        # Companies without enough data remain explicitly unclassified.
        workbook["capital_allocation_label"] = workbook[
            "capital_allocation_label"
        ].fillna("Insufficient Data")

        with pd.ExcelWriter(CASHFLOW_OUTPUT, engine="openpyxl") as writer:
            workbook.to_excel(
                writer,
                index=False,
                sheet_name="cashflow_intelligence",
            )

            if Path("output/distress_alerts.csv").exists():
                alerts = pd.read_csv("output/distress_alerts.csv")
                alerts.to_excel(
                    writer,
                    index=False,
                    sheet_name="distress_alerts",
                )

        print()
        print("Workbook columns:")
        print(workbook.columns.tolist())
        print(f"Workbook rows: {len(workbook)}")

    # Validation
    expected_companies = len(companies)
    patterned_companies = patterns["company_id"].nunique()

    print()
    print("-" * 70)
    print("DAY 32 VALIDATION")
    print("-" * 70)
    print(f"Universe companies       : {expected_companies}")
    print(f"Companies with patterns  : {patterned_companies}")
    print(f"Pattern rows              : {len(patterns)}")
    print(f"Pattern changes           : {len(changes_df)}")

    if CASHFLOW_OUTPUT.exists():
        final_wb = pd.read_excel(CASHFLOW_OUTPUT)
        required = [
            "company_id",
            "sector",
            "cfo_quality_score",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_label",
            "fcf_cagr_5yr",
            "fcf_conversion_pct",
            "distress_flag",
            "deleveraging_flag",
            "capital_allocation_label",
        ]

        missing = [c for c in required if c not in final_wb.columns]

        if missing:
            raise AssertionError(
                f"Missing workbook columns: {missing}"
            )

        if len(final_wb) != expected_companies:
            raise AssertionError(
                f"Workbook has {len(final_wb)} rows; expected "
                f"{expected_companies}."
            )

        print("Workbook validation      : PASS")
    else:
        print("Workbook validation      : SKIPPED")

    print()
    print("DAY 32 STATUS: PASS")
    print("=" * 70)


if __name__ == "__main__":
    main()