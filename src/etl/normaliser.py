"""
Data normalization utilities for NIFTY 100 ETL pipeline.
"""

import re

import pandas as pd


def normalize_year(value):
    """
    Normalize financial year/date labels to a four-digit year.

    Examples:
        2024       -> 2024
        "2024"     -> 2024
        "FY2024"   -> 2024
        "Mar 2024" -> 2024
        "2024-25"  -> 2024
        "TTM"      -> None
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    match = re.search(r"(19|20)\d{2}", value)

    if not match:
        return None

    year = int(match.group())

    if year < 1900 or year > 2100:
        return None

    return year


def normalize_ticker(value):
    """
    Normalize company ticker symbols.

    Examples:
        " reliance "  -> "RELIANCE"
        "reliance.NS" -> "RELIANCE"
        "TCS.BSE"     -> "TCS"
        "BAJAJ-AUTO"  -> "BAJAJ-AUTO"
        "M&M"         -> "M&M"
        "-"           -> None
    """

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    value = re.sub(r"\.(NS|NSE|BSE)$", "", value)

    if value == "-":
        return None

    # Allow letters, numbers, hyphens and ampersands.
    # Ampersand is required for valid ticker: M&M.
    if not re.fullmatch(r"[A-Z0-9&-]+", value):
        return None

    return value


def normalize_dataframe_year(
    df: pd.DataFrame,
    column: str = "year",
) -> pd.DataFrame:
    """
    Normalize the year column in a DataFrame.

    The original DataFrame is not modified.
    """

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    result = df.copy()

    result[column] = result[column].apply(normalize_year)

    return result


def normalize_dataframe_ticker(
    df: pd.DataFrame,
    column: str = "company_id",
) -> pd.DataFrame:
    """
    Normalize the company/ticker column in a DataFrame.

    The original DataFrame is not modified.
    """

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found")

    result = df.copy()

    result[column] = result[column].apply(normalize_ticker)

    return result


def deduplicate_company_year(
    df: pd.DataFrame,
    keep: str = "first",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resolve duplicate (company_id, year) records.

    The selected source occurrence is retained.
    Removed records are returned separately for audit purposes.

    Returns:
        cleaned_df:
            DataFrame containing one record per
            (company_id, year).

        rejected_df:
            DataFrame containing records removed because
            they were duplicate company/year records.
    """

    required_columns = {"company_id", "year"}

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    if keep not in {"first", "last"}:
        raise ValueError(
            "keep must be either 'first' or 'last'"
        )

    duplicate_mask = df.duplicated(
        subset=["company_id", "year"],
        keep=keep,
    )

    rejected_df = df.loc[duplicate_mask].copy()

    cleaned_df = df.loc[~duplicate_mask].copy()

    return cleaned_df, rejected_df