import sqlite3

DB_PATH = "db/nifty100.db"

conn = sqlite3.connect(DB_PATH)

rows = conn.execute(
    """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        debt_to_equity
    FROM financial_ratios
    WHERE CAST(year AS REAL) = (
        SELECT MAX(CAST(year AS REAL))
        FROM financial_ratios
    )
      AND return_on_equity_pct > 15
      AND debt_to_equity < 0.5
    ORDER BY return_on_equity_pct DESC
    """
).fetchall()

print("=" * 70)
print("DAY 14 - CURRENT ROE / DEBT-TO-EQUITY SCREENER")
print("=" * 70)

print(f"Results: {len(rows)}")

print()
print("Company list:")
print("-" * 70)

for company_id, year, roe, de in rows:
    print(
        f"{company_id:<15} "
        f"{str(year):<8} "
        f"ROE={roe:>8.2f}% "
        f"D/E={de:>8.2f}"
    )

print()
print("=" * 70)

if 15 <= len(rows) <= 50:
    print("STATUS: PASS")
    print("Result count is within the required 15-50 range.")
else:
    print("STATUS: REVIEW")
    print("Result count is outside the specified 15-50 range.")

print("=" * 70)

conn.close()