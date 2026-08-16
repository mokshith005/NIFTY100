"""
Data normalisation utilities for the NIFTY100 ETL pipeline.
"""

import re
from typing import Optional


def normalize_year(value) -> Optional[int]:
    """
    Normalize different year representations into an integer year.

    Examples:
        2024       -> 2024
        "2024"     -> 2024
        "FY2024"   -> 2024
        "FY 2024"  -> 2024
        "2024-25"  -> 2024
    """
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    match = re.search(r"(?:FY\s*)?(\d{4})", text, re.IGNORECASE)

    if not match:
        return None

    year = int(match.group(1))

    if 1900 <= year <= 2100:
        return year

    return None


def normalize_ticker(value) -> Optional[str]:
    """
    Normalize a stock ticker symbol.

    Examples:
        "RELIANCE"        -> "RELIANCE"
        " reliance "      -> "RELIANCE"
        "RELIANCE.NS"     -> "RELIANCE"
        "TCS.BSE"         -> "TCS"
    """
    if value is None:
        return None

    ticker = str(value).strip().upper()

    if not ticker:
        return None

    # Remove exchange suffixes.
    ticker = re.sub(r"\.(NS|NSE|BSE)$", "", ticker)

    # Keep alphanumeric characters and hyphens.
    ticker = re.sub(r"[^A-Z0-9-]", "", ticker)

    return ticker or None