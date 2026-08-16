import pandas as pd
import pytest

from src.etl.normaliser import (
    normalize_year,
    normalize_ticker,
    normalize_dataframe_year,
    normalize_dataframe_ticker,
    deduplicate_company_year,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (2024, 2024),
        ("2024", 2024),
        (" 2024 ", 2024),
        ("FY2024", 2024),
        ("FY 2024", 2024),
        ("FY-2024", 2024),
        ("2024-25", 2024),
        ("2024/25", 2024),
        ("FY2024-25", 2024),
        ("FY 2024-25", 2024),
        ("2020", 2020),
        ("1999", 1999),
        ("2099", 2099),
        ("-", None),
        (None, None),
        ("unknown", None),
        ("ABC", None),
        ("1899", None),
        ("2101", None),
        ("FY ABC", None),
    ],
)
def test_normalize_year(value, expected):
    assert normalize_year(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("RELIANCE", "RELIANCE"),
        (" reliance ", "RELIANCE"),
        ("reliance", "RELIANCE"),
        ("RELIANCE.NS", "RELIANCE"),
        ("RELIANCE.NSE", "RELIANCE"),
        ("RELIANCE.BSE", "RELIANCE"),
        (" tcs ", "TCS"),
        ("TCS.NS", "TCS"),
        ("INFY.BSE", "INFY"),
        ("HDFC-BANK", "HDFC-BANK"),
        ("ABC123", "ABC123"),
        ("-", None),
        (None, None),
        ("   ", None),
        ("@#$", None),
    ],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected


def test_normalize_dataframe_year():
    df = pd.DataFrame(
        {
            "company_id": ["ABB", "TCS"],
            "year": ["FY2024", "Mar 2023"],
        }
    )

    result = normalize_dataframe_year(df)

    assert result["year"].tolist() == [2024, 2023]


def test_normalize_dataframe_ticker():
    df = pd.DataFrame(
        {
            "company_id": [" reliance ", "TCS.NS"],
            "year": [2024, 2024],
        }
    )

    result = normalize_dataframe_ticker(df)

    assert result["company_id"].tolist() == [
        "RELIANCE",
        "TCS",
    ]


def test_normalize_dataframe_preserves_other_columns():
    df = pd.DataFrame(
        {
            "company_id": ["ABB"],
            "year": ["FY2024"],
            "sales": [1000],
        }
    )

    result = normalize_dataframe_year(df)

    assert result["sales"].tolist() == [1000]
    assert result["company_id"].tolist() == ["ABB"]


def test_deduplicate_company_year_keeps_first():
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "company_id": ["ABB", "ABB", "TCS"],
            "year": ["Mar 2024", "Mar 2024", "Mar 2024"],
            "value": [100, 200, 300],
        }
    )

    cleaned, rejected = deduplicate_company_year(df)

    assert len(cleaned) == 2
    assert len(rejected) == 1

    assert cleaned.iloc[0]["id"] == 1
    assert rejected.iloc[0]["id"] == 2


def test_deduplicate_company_year_no_duplicates():
    df = pd.DataFrame(
        {
            "company_id": ["ABB", "TCS"],
            "year": ["Mar 2024", "Mar 2024"],
            "value": [100, 200],
        }
    )

    cleaned, rejected = deduplicate_company_year(df)

    assert len(cleaned) == 2
    assert len(rejected) == 0


def test_deduplicate_company_year_missing_columns():
    df = pd.DataFrame(
        {
            "company_id": ["ABB"],
            "value": [100],
        }
    )

    with pytest.raises(ValueError):
        deduplicate_company_year(df)


def test_deduplicate_company_year_invalid_keep():
    df = pd.DataFrame(
        {
            "company_id": ["ABB"],
            "year": [2024],
        }
    )

    with pytest.raises(ValueError):
        deduplicate_company_year(df, keep="invalid")


def test_deduplicate_company_year_keeps_last():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "company_id": ["ABB", "ABB"],
            "year": [2024, 2024],
        }
    )

    cleaned, rejected = deduplicate_company_year(
        df,
        keep="last",
    )

    assert len(cleaned) == 1
    assert len(rejected) == 1

    assert cleaned.iloc[0]["id"] == 2
    assert rejected.iloc[0]["id"] == 1