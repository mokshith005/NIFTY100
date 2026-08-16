"""
Sprint 2 - Day 13
Ratio Anomaly Summary

Checks:
1. Financial ratio row uniqueness
2. ROE anomaly summary
3. ROCE anomaly summary
4. Financial-sector carve-out
5. Foreign-key integrity
"""

from pathlib import Path
import sqlite3


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "db" / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"
LOG_PATH = OUTPUT_DIR / "anomaly_summary.log"

ANOMALY_THRESHOLD = 5.0


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def check_uniqueness(conn):
    total = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    distinct_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT company_id, year
            FROM financial_ratios
            GROUP BY company_id, year
        )
        """
    ).fetchone()[0]

    duplicate_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT company_id, year
            FROM financial_ratios
            GROUP BY company_id, year
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    return total, distinct_pairs, duplicate_pairs


def get_financial_sector_count(conn):
    return conn.execute(
        """
        SELECT COUNT(*)
        FROM sectors
        WHERE LOWER(broad_sector) = 'financials'
        """
    ).fetchone()[0]


def get_roe_anomalies(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*)
        FROM financial_ratios fr
        JOIN companies c
            ON c.id = fr.company_id
        WHERE c.roe_percentage IS NOT NULL
          AND fr.return_on_equity_pct IS NOT NULL
          AND ABS(
              fr.return_on_equity_pct - c.roe_percentage
          ) > ?
        """,
        (ANOMALY_THRESHOLD,),
    ).fetchone()[0]


def get_roce_anomalies(conn):
    return conn.execute(
        """
        SELECT
            COUNT(*)
        FROM financial_ratios fr
        JOIN companies c
            ON c.id = fr.company_id
        WHERE c.roce_percentage IS NOT NULL
          AND fr.return_on_equity_pct IS NOT NULL
          AND ABS(
              fr.return_on_equity_pct - c.roce_percentage
          ) > ?
        """,
        (ANOMALY_THRESHOLD,),
    ).fetchone()[0]


def get_known_source_anomalies(conn):
    """Check known TCS source anomaly."""

    row = conn.execute(
        """
        SELECT
            company_name,
            roe_percentage,
            roce_percentage
        FROM companies
        WHERE id = 'TCS'
        """
    ).fetchone()

    return row


def get_foreign_key_errors(conn):
    return conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()


def write_log(lines):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOG_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main():
    print("=" * 70)
    print("SPRINT 2 - DAY 13 RATIO ANOMALY SUMMARY")
    print("=" * 70)

    conn = get_connection()

    total, distinct_pairs, duplicate_pairs = (
        check_uniqueness(conn)
    )

    financials = get_financial_sector_count(conn)

    roe_anomalies = get_roe_anomalies(conn)

    roce_anomalies = get_roce_anomalies(conn)

    tcs = get_known_source_anomalies(conn)

    fk_errors = get_foreign_key_errors(conn)

    lines = []

    lines.append("=" * 70)
    lines.append("SPRINT 2 - DAY 13 RATIO ANOMALY SUMMARY")
    lines.append("=" * 70)

    print()
    print("DATABASE UNIQUENESS")
    print("-" * 70)

    print(
        f"Financial ratios rows:       {total}"
    )
    print(
        f"Distinct company/year:       {distinct_pairs}"
    )
    print(
        f"Duplicate company/year:      {duplicate_pairs}"
    )

    lines.append("")
    lines.append("DATABASE UNIQUENESS")
    lines.append("-" * 70)
    lines.append(
        f"Financial ratios rows:       {total}"
    )
    lines.append(
        f"Distinct company/year:       {distinct_pairs}"
    )
    lines.append(
        f"Duplicate company/year:      {duplicate_pairs}"
    )

    uniqueness_pass = (
        total == distinct_pairs
        and duplicate_pairs == 0
    )

    print(
        f"Uniqueness check:            "
        f"{'PASS' if uniqueness_pass else 'FAIL'}"
    )

    lines.append(
        f"Uniqueness check:            "
        f"{'PASS' if uniqueness_pass else 'FAIL'}"
    )

    print()
    print("ANOMALY SUMMARY")
    print("-" * 70)

    print(
        f"Anomaly threshold:           "
        f">{ANOMALY_THRESHOLD} percentage points"
    )

    print(
        f"ROE anomalies:               {roe_anomalies}"
    )

    print(
        f"ROCE anomalies:              {roce_anomalies}"
    )

    lines.append("")
    lines.append("ANOMALY SUMMARY")
    lines.append("-" * 70)
    lines.append(
        f"Anomaly threshold:           "
        f">{ANOMALY_THRESHOLD} percentage points"
    )
    lines.append(
        f"ROE anomalies:               {roe_anomalies}"
    )
    lines.append(
        f"ROCE anomalies:              {roce_anomalies}"
    )

    print()
    print("FINANCIAL SECTOR CARVE-OUT")
    print("-" * 70)

    print(
        f"Financials companies:         {financials}"
    )

    lines.append("")
    lines.append("FINANCIAL SECTOR CARVE-OUT")
    lines.append("-" * 70)
    lines.append(
        f"Financials companies:         {financials}"
    )

    carveout_pass = financials > 0

    print(
        f"Financial carve-out:         "
        f"{'PASS' if carveout_pass else 'FAIL'}"
    )

    lines.append(
        f"Financial carve-out:         "
        f"{'PASS' if carveout_pass else 'FAIL'}"
    )

    print()
    print("KNOWN SOURCE ANOMALY")
    print("-" * 70)

    if tcs:
        company_name, source_roe, source_roce = tcs

        print(
            f"TCS company:                 {company_name}"
        )
        print(
            f"TCS source ROE:              {source_roe}"
        )
        print(
            f"TCS source ROCE:             {source_roce}"
        )

        lines.append("")
        lines.append("KNOWN SOURCE ANOMALY")
        lines.append("-" * 70)
        lines.append(
            f"TCS company:                 {company_name}"
        )
        lines.append(
            f"TCS source ROE:              {source_roe}"
        )
        lines.append(
            f"TCS source ROCE:             {source_roce}"
        )
        lines.append(
            "TCS source values are retained "
            "for display only."
        )
        lines.append(
            "Ratio-engine values are used "
            "for analytics."
        )

    print()
    print("FOREIGN KEY CHECK")
    print("-" * 70)

    print(
        f"Foreign key errors:          {len(fk_errors)}"
    )

    lines.append("")
    lines.append("FOREIGN KEY CHECK")
    lines.append("-" * 70)
    lines.append(
        f"Foreign key errors:          {len(fk_errors)}"
    )

    if fk_errors:
        for error in fk_errors:
            print(error)
            lines.append(str(error))

    overall_pass = (
        uniqueness_pass
        and carveout_pass
        and not fk_errors
    )

    print()
    print("=" * 70)
    print(
        f"STATUS: {'PASS' if overall_pass else 'FAIL'}"
    )
    print("=" * 70)

    lines.append("")
    lines.append("=" * 70)
    lines.append(
        f"STATUS: {'PASS' if overall_pass else 'FAIL'}"
    )
    lines.append("=" * 70)

    write_log(lines)

    print()
    print(f"Log: {LOG_PATH}")

    conn.close()


if __name__ == "__main__":
    main()