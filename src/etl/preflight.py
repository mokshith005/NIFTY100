"""
Pre-load inspection for the NIFTY100 datasets.

This script inspects the supplied source files before the
final SQLite schema and DQ rules are applied.
"""

from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")


CORE_FILES = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "documents.xlsx",
    "analysis.xlsx",
    "prosandcons.xlsx",
]

SUPPLEMENTARY_FILES = [
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
    "sectors.xlsx",
    "stock_prices.xlsx",
]


def read_source_file(filename: str) -> pd.DataFrame:
    """Read a source Excel file using its correct header row."""

    if filename in CORE_FILES:
        path = RAW_DIR / "core" / filename
        return pd.read_excel(path, header=1)

    path = RAW_DIR / "supplementary" / filename
    return pd.read_excel(path)


def inspect_file(filename: str) -> None:
    """Print basic information about one source file."""

    df = read_source_file(filename)

    print("\n" + "=" * 70)
    print(filename)
    print("=" * 70)

    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nMissing values:")
    missing = df.isna().sum()

    for column, count in missing.items():
        if count > 0:
            print(f"  - {column}: {count}")

    print("\nFirst 2 rows:")
    print(df.head(2).to_string(index=False))


def check_company_references() -> None:
    """Check company IDs against companies.xlsx."""

    companies = read_source_file("companies.xlsx")

    valid_ids = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    print("\n" + "=" * 70)
    print("COMPANY REFERENCE CHECK")
    print("=" * 70)

    for filename in (
        "profitandloss.xlsx",
        "balancesheet.xlsx",
        "cashflow.xlsx",
        "documents.xlsx",
        "analysis.xlsx",
        "prosandcons.xlsx",
        "financial_ratios.xlsx",
        "market_cap.xlsx",
        "peer_groups.xlsx",
        "sectors.xlsx",
        "stock_prices.xlsx",
    ):
        df = read_source_file(filename)

        if "company_id" not in df.columns:
            print(f"{filename}: no company_id column")
            continue

        source_ids = set(
            df["company_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        invalid = sorted(source_ids - valid_ids)

        print(
            f"{filename}: "
            f"{len(source_ids)} unique companies, "
            f"{len(invalid)} invalid references"
        )

        if invalid:
            print(f"  Invalid IDs: {invalid[:20]}")


def check_duplicate_keys() -> None:
    """Check likely natural keys in the datasets."""

    print("\n" + "=" * 70)
    print("DUPLICATE KEY CHECK")
    print("=" * 70)

    checks = {
        "profitandloss.xlsx": ["company_id", "year"],
        "balancesheet.xlsx": ["company_id", "year"],
        "cashflow.xlsx": ["company_id", "year"],
        "financial_ratios.xlsx": ["company_id", "year"],
        "market_cap.xlsx": ["company_id", "year"],
        "stock_prices.xlsx": ["company_id", "date"],
    }

    for filename, keys in checks.items():
        df = read_source_file(filename)

        duplicates = df.duplicated(
            subset=keys,
            keep=False,
        )

        count = int(duplicates.sum())

        print(
            f"{filename}: "
            f"{count} rows involved in duplicate keys"
        )

        if count:
            print(
                df.loc[duplicates, keys]
                .head(10)
                .to_string(index=False)
            )


def main() -> None:
    """Run complete pre-load inspection."""

    for filename in CORE_FILES + SUPPLEMENTARY_FILES:
        inspect_file(filename)

    check_company_references()
    check_duplicate_keys()


if __name__ == "__main__":
    main()