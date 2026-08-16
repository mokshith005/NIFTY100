import pytest

from src.etl.normaliser import normalize_year, normalize_ticker


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
        ("", None),
        (None, None),
        ("unknown", None),
        ("ABC", None),
        (1899, None),
        (2101, None),
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
        ("", None),
        (None, None),
        ("   ", None),
        ("@#$", None),
    ],
)
def test_normalize_ticker(value, expected):
    assert normalize_ticker(value) == expected