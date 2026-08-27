import sqlite3

DB = "db/nifty100.db"
companies = ["RELIANCE", "TCS", "INFY"]

conn = sqlite3.connect(DB)

print("=" * 70)
print("DAY 12 - MANUAL 5-YEAR REVENUE CAGR SPOT CHECK")
print("=" * 70)

for company in companies:
    rows = conn.execute(
        """
        SELECT CAST(year AS REAL), sales
        FROM profitandloss
        WHERE company_id = ?
          AND sales IS NOT NULL
          AND CAST(year AS REAL) >= 2019
          AND CAST(year AS REAL) <= 2024
        ORDER BY CAST(year AS REAL)
        """,
        (company,),
    ).fetchall()

    db = conn.execute(
        """
        SELECT revenue_cagr_5yr
        FROM financial_ratios
        WHERE company_id = ?
          AND CAST(year AS REAL) = 2024
        ORDER BY id
        LIMIT 1
        """,
        (company,),
    ).fetchone()

    print(f"\n{company}")
    print("Revenue history:", rows)
    print("Database CAGR:", db)

    if len(rows) < 6:
        print("STATUS: INSUFFICIENT DATA")
        continue

    start_sales = rows[0][1]
    end_sales = rows[-1][1]

    manual_cagr = ((end_sales / start_sales) ** (1 / 5) - 1) * 100
    database_cagr = db[0]

    difference = abs(manual_cagr - database_cagr)

    print(f"Start Sales: {start_sales}")
    print(f"End Sales: {end_sales}")
    print(f"Manual 5Y CAGR: {manual_cagr:.6f}%")
    print(f"Database 5Y CAGR: {database_cagr:.6f}%")
    print(f"Difference: {difference:.6f}%")

    if difference < 0.1:
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")

conn.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)