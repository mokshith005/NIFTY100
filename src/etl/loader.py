"""
Generic Excel loader for the NIFTY100 ETL pipeline.
"""

from pathlib import Path
from typing import Dict

import pandas as pd

from .normaliser import normalize_ticker, normalize_year


SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}


def discover_files(data_dir: str | Path) -> list[Path]:
    """Find supported Excel files recursively."""
    data_path = Path(data_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    return sorted(
        file
        for file in data_path.rglob("*")
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_excel_file(file_path: str | Path) -> Dict[str, pd.DataFrame]:
    """
    Load all sheets from an Excel workbook.

    Returns:
        Dictionary where:
            key   = sheet name
            value = DataFrame
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    return pd.read_excel(path, sheet_name=None)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply generic year and ticker normalisation when
    recognizable columns are present.
    """
    result = df.copy()

    for column in result.columns:
        column_name = str(column).strip().lower()

        if column_name in {"year", "fy", "financial_year", "fiscal_year"}:
            result[column] = result[column].apply(normalize_year)

        elif column_name in {"ticker", "symbol", "stock_symbol"}:
            result[column] = result[column].apply(normalize_ticker)

    return result


def load_directory(data_dir: str | Path) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Load every Excel workbook from a directory.

    Returns:
        {
            "filename.xlsx": {
                "Sheet1": DataFrame,
                "Sheet2": DataFrame
            }
        }
    """
    files = discover_files(data_dir)

    loaded_data = {}

    for file_path in files:
        sheets = load_excel_file(file_path)

        normalized_sheets = {
            sheet_name: normalize_dataframe(df)
            for sheet_name, df in sheets.items()
        }

        loaded_data[file_path.name] = normalized_sheets

    return loaded_data


def print_load_summary(
    loaded_data: Dict[str, Dict[str, pd.DataFrame]]
) -> None:
    """Print a summary of loaded workbooks and sheets."""
    if not loaded_data:
        print("No Excel files found.")
        return

    for filename, sheets in loaded_data.items():
        print(f"\nFile: {filename}")

        for sheet_name, df in sheets.items():
            rows, columns = df.shape

            print(
                f"  Sheet: {sheet_name} | "
                f"Rows: {rows} | Columns: {columns}"
            )


if __name__ == "__main__":
    raw_directory = Path("data/raw")

    data = load_directory(raw_directory)

    print_load_summary(data)