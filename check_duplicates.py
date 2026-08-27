import sqlite3

conn = sqlite3.connect("db/nifty100.db")

print("=" * 70)
print("FINANCIAL RATIOS DUPLICATE CHECK")
print("=" * 70)

total = conn.execute(
    "SELECT COUNT(*) FROM financial_ratios"
).fetchone()[0]

distinct_pairs = conn.execute(
    """
    SELECT COUNT(*)
    FROM (
        SELECT DISTINCT company_id, year
        FROM financial_ratios
    )
    """
).fetchone()[0]

duplicates = conn.execute(
    """
    SELECT company_id, year, COUNT(*)
    FROM financial_ratios
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
    ORDER BY company_id, year
    """
).fetchall()

print(f"Total ratio rows:       {total}")
print(f"Distinct company/year:  {distinct_pairs}")
print(f"Duplicate pairs:        {len(duplicates)}")

if duplicates:
    print("\nDuplicates:")
    for row in duplicates[:30]:
        print(row)
else:
    print("\nNo duplicate company/year records found.")

conn.close()