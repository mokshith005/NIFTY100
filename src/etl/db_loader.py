"""
SQLite database loader for the NIFTY 100 data foundation.

Loads processed CSV files into the SQLite database using db/schema.sql.
"""

from pathlib import Path
import sqlite3

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DB_DIR = ROOT_DIR / "db"
DATABASE_PATH = DB_DIR / "database.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


TABLE_FILES = {
    "companies": "companies.csv",
    "profitandloss": "profitandloss.csv",
    "balancesheet": "balancesheet.csv",
    "cashflow": "cashflow.csv",
    "documents": "documents.csv",
    "analysis": "analysis.csv",
    "prosandcons": "prosandcons.csv",
    "financial_ratios": "financial_ratios.csv",
    "market_cap": "market_cap.csv",
    "peer_groups": "peer_groups.csv",
    "sectors": "sectors.csv",
    "stock_prices": "stock_prices.csv",
}


def create_database() -> sqlite3.Connection:
    """Create the SQLite database and apply the schema."""

    DB_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    schema = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    connection.executescript(
        schema
    )

    return connection


def prepare_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare CSV data for SQLite loading."""

    result = df.copy()

    result = result.where(
        pd.notna(result),
        None,
    )

    return result


def load_csv(
    connection: sqlite3.Connection,
    table_name: str,
    filename: str,
) -> int:
    """Load one processed CSV file into SQLite."""

    path = PROCESSED_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Processed file not found: {path}"
        )

    df = pd.read_csv(
        path,
        keep_default_na=True,
    )

    if df.empty:
        print(
            f"{table_name}: 0 rows"
        )
        return 0

    df = prepare_dataframe(
        df
    )

    df.to_sql(
        table_name,
        connection,
        if_exists="append",
        index=False,
    )

    return len(df)


def get_row_count(
    connection: sqlite3.Connection,
    table_name: str,
) -> int:
    """Return the number of rows in a database table."""

    result = connection.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()

    return int(result[0])


def validate_database(
    connection: sqlite3.Connection,
) -> None:
    """Validate foreign keys and loaded row counts."""

    print("\nDatabase validation")
    print("-" * 50)

    foreign_keys = connection.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    print(
        f"Foreign keys: {foreign_keys}"
    )

    if foreign_keys != 1:
        raise RuntimeError(
            "SQLite foreign-key enforcement is disabled."
        )

    print("\nLoaded rows:")

    for table_name in TABLE_FILES:
        count = get_row_count(
            connection,
            table_name,
        )

        print(
            f"  {table_name:<20} {count:>6}"
        )

    violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if violations:
        raise RuntimeError(
            f"Foreign-key violations found: {violations}"
        )

    print(
        "\nForeign-key check: PASSED"
    )


def validate_tables(
    connection: sqlite3.Connection,
) -> None:
    """Verify that all expected tables exist."""

    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    existing_tables = {
        row[0]
        for row in tables
    }

    missing_tables = (
        set(TABLE_FILES)
        - existing_tables
    )

    if missing_tables:
        raise RuntimeError(
            f"Missing database tables: "
            f"{sorted(missing_tables)}"
        )

    print(
        f"\nSchema validation: "
        f"{len(existing_tables)} tables found"
    )


def main() -> None:
    """Run the complete SQLite loading process."""

    print("=" * 70)
    print("NIFTY 100 SQLITE DATABASE LOADER")
    print("=" * 70)

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    connection = create_database()

    try:
        print(
            f"\nDatabase: {DATABASE_PATH}"
        )

        print(
            f"Schema:   {SCHEMA_PATH}"
        )

        validate_tables(
            connection
        )

        print(
            "\nLoading processed CSV files"
        )

        print(
            "-" * 50
        )

        total_rows = 0

        for table_name, filename in TABLE_FILES.items():

            print(
                f"Loading {filename:<25}",
                end="",
            )

            rows = load_csv(
                connection,
                table_name,
                filename,
            )

            total_rows += rows

            print(
                f"{rows:>6} rows"
            )

        connection.commit()

        validate_database(
            connection
        )

        print(
            "\n" + "-" * 50
        )

        print(
            f"Total rows loaded: "
            f"{total_rows}"
        )

        print(
            f"Database created: "
            f"{DATABASE_PATH}"
        )

        print(
            "\n" + "=" * 70
        )

        print(
            "SQLITE LOAD COMPLETE"
        )

        print(
            "=" * 70
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()