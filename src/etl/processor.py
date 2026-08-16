"""
ETL processing pipeline for the NIFTY 100 data foundation.

Reads Excel files from data/raw, normalizes fields, removes exact
duplicate records, checks company references, and writes cleaned
CSV files to data/processed.
"""

from pathlib import Path

import pandas as pd

from src.etl.normaliser import (
    normalize_dataframe_ticker,
    normalize_dataframe_year,
)


ROOT_DIR = Path(__file__).resolve().parents[2]

RAW_CORE = ROOT_DIR / "data" / "raw" / "core"
RAW_SUPPLEMENTARY = ROOT_DIR / "data" / "raw" / "supplementary"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_DIR = ROOT_DIR / "output"


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


def read_excel_file(path: Path, core: bool = False) -> pd.DataFrame:
    """Read an Excel file using the correct header row."""
    header = 1 if core else 0
    return pd.read_excel(path, header=header)


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize company IDs and year fields when present."""

    result = df.copy()

    if "company_id" in result.columns:
        result = normalize_dataframe_ticker(
            result,
            "company_id",
        )

    if "year" in result.columns:
        result = normalize_dataframe_year(
            result,
            "year",
        )

    if "Year" in result.columns:
        result = normalize_dataframe_year(
            result,
            "Year",
        )

        result = result.rename(
            columns={"Year": "year"}
        )

    return result


def remove_exact_duplicates(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove only completely identical rows.

    Rows with the same company_id and year but different financial
    values are preserved.
    """

    duplicate_mask = df.duplicated(
        keep="first"
    )

    rejected = df.loc[
        duplicate_mask
    ].copy()

    cleaned = df.loc[
        ~duplicate_mask
    ].copy()

    return cleaned, rejected


def get_company_reference(
    companies_df: pd.DataFrame,
) -> set[str]:
    """Return valid company IDs from the companies master."""

    if "id" not in companies_df.columns:
        raise ValueError(
            "companies dataset must contain an 'id' column"
        )

    return set(
        companies_df["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )


def remove_invalid_company_references(
    df: pd.DataFrame,
    valid_companies: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove records whose company_id does not exist in companies."""

    if "company_id" not in df.columns:
        return df.copy(), pd.DataFrame()

    invalid_mask = ~df["company_id"].isin(
        valid_companies
    )

    rejected = df.loc[
        invalid_mask
    ].copy()

    cleaned = df.loc[
        ~invalid_mask
    ].copy()

    return cleaned, rejected


def process_file(
    path: Path,
    core: bool,
    valid_companies: set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process one Excel file.

    Returns:
        cleaned dataframe
        rejected dataframe
    """

    df = read_excel_file(
        path,
        core=core,
    )

    rows_read = len(df)

    df = normalize_dataset(df)

    rejected_parts = []

    cleaned, duplicate_rejected = (
        remove_exact_duplicates(df)
    )

    if not duplicate_rejected.empty:
        duplicate_rejected = (
            duplicate_rejected.copy()
        )

        duplicate_rejected[
            "rejection_reason"
        ] = "exact_duplicate"

        rejected_parts.append(
            duplicate_rejected
        )

    if valid_companies is not None:
        cleaned, reference_rejected = (
            remove_invalid_company_references(
                cleaned,
                valid_companies,
            )
        )

        if not reference_rejected.empty:
            reference_rejected = (
                reference_rejected.copy()
            )

            reference_rejected[
                "rejection_reason"
            ] = "invalid_company_reference"

            rejected_parts.append(
                reference_rejected
            )

    if rejected_parts:
        rejected = pd.concat(
            rejected_parts,
            ignore_index=True,
        )
    else:
        rejected = pd.DataFrame()

    return cleaned, rejected


def save_processed_file(
    df: pd.DataFrame,
    source_name: str,
) -> Path:
    """Save cleaned data as CSV."""

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_name = (
        Path(source_name).stem + ".csv"
    )

    output_path = (
        PROCESSED_DIR / output_name
    )

    df.to_csv(
        output_path,
        index=False,
    )

    return output_path


def main() -> None:
    """Run the complete preprocessing stage."""

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("NIFTY 100 ETL PROCESSOR")
    print("=" * 70)

    companies_path = (
        RAW_CORE / "companies.xlsx"
    )

    companies = read_excel_file(
        companies_path,
        core=True,
    )

    companies = normalize_dataset(
        companies
    )

    valid_companies = get_company_reference(
        companies
    )

    print(
        f"\nValid company IDs: "
        f"{len(valid_companies)}"
    )

    audit_records = []
    all_rejections = []

    all_files = [
        (RAW_CORE, filename, True)
        for filename in CORE_FILES
        if filename != "companies.xlsx"
    ]

    all_files += [
        (RAW_SUPPLEMENTARY, filename, False)
        for filename in SUPPLEMENTARY_FILES
    ]

    companies_output = save_processed_file(
        companies,
        "companies.xlsx",
    )

    audit_records.append(
        {
            "source_file": "companies.xlsx",
            "table": "companies",
            "rows_read": len(companies),
            "rows_loaded": len(companies),
            "rows_rejected": 0,
            "status": "OK",
        }
    )

    print(
        f"\ncompanies.xlsx -> "
        f"{len(companies)} rows"
    )

    for directory, filename, core in all_files:

        path = directory / filename

        print(
            f"\nProcessing: {filename}"
        )

        source_df = read_excel_file(
            path,
            core=core,
        )

        rows_read = len(source_df)

        cleaned, rejected = process_file(
            path,
            core=core,
            valid_companies=valid_companies,
        )

        output_path = save_processed_file(
            cleaned,
            filename,
        )

        rejected_count = len(rejected)

        if rejected_count > 0:

            rejected = rejected.copy()

            rejected[
                "source_file"
            ] = filename

            all_rejections.append(
                rejected
            )

        audit_records.append(
            {
                "source_file": filename,
                "table": Path(
                    filename
                ).stem,
                "rows_read": rows_read,
                "rows_loaded": len(cleaned),
                "rows_rejected": rejected_count,
                "status": (
                    "REJECTED_ROWS"
                    if rejected_count
                    else "OK"
                ),
            }
        )

        print(
            f"  Read: {rows_read}"
        )

        print(
            f"  Loaded: {len(cleaned)}"
        )

        print(
            f"  Rejected: {rejected_count}"
        )

        print(
            f"  Output: {output_path}"
        )

    audit = pd.DataFrame(
        audit_records
    )

    audit_path = (
        OUTPUT_DIR / "load_audit.csv"
    )

    audit.to_csv(
        audit_path,
        index=False,
    )

    if all_rejections:

        validation_failures = pd.concat(
            all_rejections,
            ignore_index=True,
        )

        validation_path = (
            OUTPUT_DIR
            / "validation_failures.csv"
        )

        validation_failures.to_csv(
            validation_path,
            index=False,
        )

        print(
            f"\nRejection report: "
            f"{validation_path}"
        )

    print(
        f"\nLoad audit: {audit_path}"
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "ETL PROCESSING COMPLETE"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()