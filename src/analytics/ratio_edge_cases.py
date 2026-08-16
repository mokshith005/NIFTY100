"""
Sprint 2 - Day 13
Bank/Financials carve-out and ratio edge-case analysis.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path("db/nifty100.db")
OUTPUT_PATH = Path("output/ratio_edge_cases.log")


def classify_anomaly(source_value, calculated_value, tolerance):
    """
    Categorize differences between source and calculated values.

    The source dataset may use a different calculation period,
    formula, or data version than the ratio engine.
    """

    if source_value is None or calculated_value is None:
        return "data source issue"

    difference = abs(calculated_value - source_value)

    if difference <= tolerance:
        return None

    # Large differences are generally source/version differences
    # unless the calculated formula itself is clearly inconsistent.
    if difference > tolerance * 5:
        return "version difference"

    return "formula discrepancy"


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    # ------------------------------------------------------------
    # 1. Financials carve-out verification
    # ------------------------------------------------------------

    financials = conn.execute(
        """
        SELECT DISTINCT company_id
        FROM sectors
        WHERE LOWER(TRIM(broad_sector)) = 'financials'
        ORDER BY company_id
        """
    ).fetchall()

    financials = [row[0] for row in financials]

    financials_flagged = conn.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios r
        WHERE r.company_id IN (
            SELECT DISTINCT company_id
            FROM sectors
            WHERE LOWER(TRIM(broad_sector)) = 'financials'
        )
        AND r.high_leverage_flag = 1
        """
    ).fetchone()[0]

    # ------------------------------------------------------------
    # 2. ROCE and ROE source comparisons
    # ------------------------------------------------------------

    rows = conn.execute(
        """
        SELECT
            r.company_id,
            c.company_name,
            r.year,
            r.roce_pct,
            c.roce_percentage,
            r.return_on_equity_pct,
            c.roe_percentage
        FROM financial_ratios r
        JOIN companies c
            ON r.company_id = c.id
        ORDER BY r.company_id, CAST(r.year AS REAL)
        """
    ).fetchall()

    roce_anomalies = []
    roe_anomalies = []

    for row in rows:
        (
            company_id,
            company_name,
            year,
            calculated_roce,
            source_roce,
            calculated_roe,
            source_roe,
        ) = row

        # ROCE comparison
        if calculated_roce is not None and source_roce is not None:
            roce_difference = abs(
                calculated_roce - source_roce
            )

            if roce_difference > 5:
                category = classify_anomaly(
                    source_roce,
                    calculated_roce,
                    5,
                )

                roce_anomalies.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "year": year,
                        "calculated": calculated_roce,
                        "source": source_roce,
                        "difference": roce_difference,
                        "category": category,
                    }
                )

        # ROE comparison
        if calculated_roe is not None and source_roe is not None:
            roe_difference = abs(
                calculated_roe - source_roe
            )

            if roe_difference > 5:
                category = classify_anomaly(
                    source_roe,
                    calculated_roe,
                    5,
                )

                roe_anomalies.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "year": year,
                        "calculated": calculated_roe,
                        "source": source_roe,
                        "difference": roe_difference,
                        "category": category,
                    }
                )

    # ------------------------------------------------------------
    # 3. Write edge-case log
    # ------------------------------------------------------------

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as log:

        log.write("=" * 78 + "\n")
        log.write("NIFTY 100 - SPRINT 2 DAY 13 RATIO EDGE CASE LOG\n")
        log.write("=" * 78 + "\n\n")

        log.write("FINANCIALS CARVE-OUT\n")
        log.write("-" * 78 + "\n")
        log.write(
            f"Financials companies found: {len(financials)}\n"
        )
        log.write(
            "Expected specification count: 19\n"
        )
        log.write(
            f"Actual database count: {len(financials)}\n"
        )
        log.write(
            "High leverage flags on Financials rows: "
            f"{financials_flagged}\n"
        )

        if financials_flagged == 0:
            log.write(
                "STATUS: PASS - Financials leverage warning "
                "suppression is working.\n"
            )
        else:
            log.write(
                "STATUS: REVIEW - Financials rows contain "
                "high leverage flags.\n"
            )

        log.write("\nFinancials companies:\n")

        for company in financials:
            log.write(f"  - {company}\n")

        log.write("\n")
        log.write("ROCE SOURCE COMPARISON\n")
        log.write("-" * 78 + "\n")
        log.write(
            "Anomaly threshold: absolute difference > 5 percentage points\n"
        )
        log.write(
            f"ROCE anomalies found: {len(roce_anomalies)}\n\n"
        )

        for item in roce_anomalies:
            log.write(
                f"{item['company_id']} | "
                f"{item['year']} | "
                f"calculated={item['calculated']:.4f} | "
                f"source={item['source']:.4f} | "
                f"difference={item['difference']:.4f} | "
                f"category={item['category']}\n"
            )

        if not roce_anomalies:
            log.write("No ROCE anomalies above 5% found.\n")

        log.write("\n")
        log.write("ROE SOURCE COMPARISON\n")
        log.write("-" * 78 + "\n")
        log.write(
            "Anomaly threshold: absolute difference > 5 percentage points\n"
        )
        log.write(
            f"ROE anomalies found: {len(roe_anomalies)}\n\n"
        )

        for item in roe_anomalies:
            log.write(
                f"{item['company_id']} | "
                f"{item['year']} | "
                f"calculated={item['calculated']:.4f} | "
                f"source={item['source']:.4f} | "
                f"difference={item['difference']:.4f} | "
                f"category={item['category']}\n"
            )

        if not roe_anomalies:
            log.write("No ROE anomalies above 5% found.\n")

        log.write("\n")
        log.write("KNOWN SOURCE ANOMALY CHECK\n")
        log.write("-" * 78 + "\n")

        tcs = conn.execute(
            """
            SELECT
                roe_percentage,
                roce_percentage
            FROM companies
            WHERE id = 'TCS'
            """
        ).fetchone()

        if tcs:
            log.write(
                f"TCS source ROE: {tcs[0]}\n"
            )
            log.write(
                f"TCS source ROCE: {tcs[1]}\n"
            )
            log.write(
                "TCS source values are retained for display only; "
                "ratio-engine values are used for analytics.\n"
            )

        log.write("\n")
        log.write("SUMMARY\n")
        log.write("-" * 78 + "\n")
        log.write(
            f"Financials companies: {len(financials)}\n"
        )
        log.write(
            f"Financials high-leverage flags: {financials_flagged}\n"
        )
        log.write(
            f"ROCE anomalies: {len(roce_anomalies)}\n"
        )
        log.write(
            f"ROE anomalies: {len(roe_anomalies)}\n"
        )

        if financials_flagged == 0:
            log.write(
                "Financials carve-out: PASS\n"
            )
        else:
            log.write(
                "Financials carve-out: REVIEW REQUIRED\n"
            )

    conn.close()

    # ------------------------------------------------------------
    # Console output
    # ------------------------------------------------------------

    print("=" * 78)
    print("SPRINT 2 - DAY 13 RATIO EDGE CASE ANALYSIS")
    print("=" * 78)
    print(f"Financials companies: {len(financials)}")
    print(
        "Financials high-leverage flags:",
        financials_flagged,
    )
    print("ROCE anomalies:", len(roce_anomalies))
    print("ROE anomalies:", len(roe_anomalies))
    print(f"Log: {OUTPUT_PATH}")

    if financials_flagged == 0:
        print("Financials carve-out: PASS")
    else:
        print("Financials carve-out: REVIEW REQUIRED")


if __name__ == "__main__":
    main()