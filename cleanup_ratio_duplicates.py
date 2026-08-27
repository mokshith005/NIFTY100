import sqlite3
from pathlib import Path


DB_PATH = Path("db/nifty100.db")


def main():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA foreign_keys = ON")

    print("=" * 70)
    print("FINANCIAL RATIOS DUPLICATE CLEANUP")
    print("=" * 70)

    before = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    distinct_before = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT company_id, year
            FROM financial_ratios
        )
        """
    ).fetchone()[0]

    duplicates_before = before - distinct_before

    print(f"Rows before cleanup:       {before}")
    print(f"Distinct company/year:     {distinct_before}")
    print(f"Duplicate rows to remove:  {duplicates_before}")

    # ------------------------------------------------------------
    # Backup table
    # ------------------------------------------------------------

    conn.execute(
        """
        DROP TABLE IF EXISTS financial_ratios_backup
        """
    )

    conn.execute(
        """
        CREATE TABLE financial_ratios_backup
        AS
        SELECT *
        FROM financial_ratios
        """
    )

    print("\nBackup table created:")
    print("financial_ratios_backup")

    # ------------------------------------------------------------
    # Identify duplicate IDs.
    #
    # Keep the lowest ID for each company/year.
    # The duplicate rows contain the same ratio values for the
    # problematic records, so keeping the first record preserves
    # the calculated KPI data.
    # ------------------------------------------------------------

    duplicate_ids = conn.execute(
        """
        SELECT id
        FROM financial_ratios
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM financial_ratios
            GROUP BY company_id, year
        )
        ORDER BY id
        """
    ).fetchall()

    ids = [row[0] for row in duplicate_ids]

    print(f"\nDuplicate IDs found: {len(ids)}")

    # ------------------------------------------------------------
    # Delete duplicates
    # ------------------------------------------------------------

    if ids:
        placeholders = ",".join(
            "?" for _ in ids
        )

        conn.execute(
            f"""
            DELETE FROM financial_ratios
            WHERE id IN ({placeholders})
            """,
            ids,
        )

    conn.commit()

    # ------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------

    after = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    distinct_after = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT company_id, year
            FROM financial_ratios
        )
        """
    ).fetchone()[0]

    remaining_duplicates = conn.execute(
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

    fk_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print("\n" + "=" * 70)
    print("CLEANUP RESULT")
    print("=" * 70)

    print(f"Rows after cleanup:        {after}")
    print(f"Distinct company/year:     {distinct_after}")
    print(f"Remaining duplicate pairs: {remaining_duplicates}")
    print(f"Foreign key errors:        {len(fk_errors)}")

    if after != distinct_after:
        raise RuntimeError(
            "Duplicate company/year records still exist."
        )

    if remaining_duplicates != 0:
        raise RuntimeError(
            "Duplicate pairs remain after cleanup."
        )

    if fk_errors:
        raise RuntimeError(
            f"Foreign-key errors found: {fk_errors}"
        )

    print("\nSTATUS: PASS")
    print("One financial_ratios row now exists per company/year.")

    conn.close()


if __name__ == "__main__":
    main()