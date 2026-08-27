import sqlite3

DB = "db/nifty100.db"
companies = ["RELIANCE", "TCS", "INFY"]

conn = sqlite3.connect(DB)

print("=" * 70)
print("DAY 12 - MANUAL ROE SPOT CHECK")
print("=" * 70)

for company in companies:
    print(f"\n{company}")

    bs = conn.execute(
        """
        SELECT equity_capital, reserves
        FROM balancesheet
        WHERE company_id = ? AND CAST(year AS REAL) = 2024
        ORDER BY id
        LIMIT 1
        """,
        (company,),
    ).fetchone()

    pl = conn.execute(
        """
        SELECT net_profit
        FROM profitandloss
        WHERE company_id = ? AND CAST(year AS REAL) = 2024
        ORDER BY id
        LIMIT 1
        """,
        (company,),
    ).fetchone()

    db = conn.execute(
        """
        SELECT return_on_equity_pct
        FROM financial_ratios
        WHERE company_id = ? AND CAST(year AS REAL) = 2024
        ORDER BY id
        LIMIT 1
        """,
        (company,),
    ).fetchone()

    print("Balance Sheet:", bs)
    print("Profit & Loss:", pl)
    print("Database ROE:", db)

    if bs is None:
        print("ERROR: 2024 balance sheet row not found")
        continue

    if pl is None:
        print("ERROR: 2024 P&L row not found")
        continue

    if db is None:
        print("ERROR: 2024 ratio row not found")
        continue

    equity_capital = bs[0] or 0
    reserves = bs[1] or 0
    net_profit = pl[0]

    total_equity = equity_capital + reserves

    if net_profit is None:
        print("Manual ROE: None - net profit unavailable")
        continue

    if total_equity <= 0:
        print("Manual ROE: None - equity <= 0")
        continue

    manual_roe = (net_profit / total_equity) * 100
    database_roe = db[0]
    difference = abs(manual_roe - database_roe)

    print(f"Total Equity: {total_equity}")
    print(f"Net Profit: {net_profit}")
    print(f"Manual ROE: {manual_roe:.6f}%")
    print(f"Database ROE: {database_roe:.6f}%")
    print(f"Difference: {difference:.6f}%")

    if difference < 0.1:
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")

conn.close()

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)