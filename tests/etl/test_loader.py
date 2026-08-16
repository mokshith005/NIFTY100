import pandas as pd
import pytest

from src.etl.loader import (
    discover_files,
    load_excel_file,
    load_directory,
    normalize_dataframe,
)


def test_discover_files(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    excel_file = data_dir / "sample.xlsx"
    pd.DataFrame({"year": [2024]}).to_excel(excel_file, index=False)

    files = discover_files(data_dir)

    assert len(files) == 1
    assert files[0].name == "sample.xlsx"


def test_discover_files_empty_directory(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    files = discover_files(data_dir)

    assert files == []


def test_discover_files_missing_directory(tmp_path):
    missing_dir = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        discover_files(missing_dir)


def test_load_excel_file(tmp_path):
    excel_file = tmp_path / "sample.xlsx"

    df = pd.DataFrame(
        {
            "year": [2024, 2023],
            "ticker": ["RELIANCE.NS", "TCS.NSE"],
        }
    )

    df.to_excel(excel_file, index=False)

    result = load_excel_file(excel_file)

    assert "Sheet1" in result
    assert len(result["Sheet1"]) == 2


def test_load_excel_file_missing(tmp_path):
    missing_file = tmp_path / "missing.xlsx"

    with pytest.raises(FileNotFoundError):
        load_excel_file(missing_file)


def test_load_excel_file_invalid_extension(tmp_path):
    invalid_file = tmp_path / "sample.txt"
    invalid_file.write_text("test")

    with pytest.raises(ValueError):
        load_excel_file(invalid_file)


def test_normalize_dataframe_year():
    df = pd.DataFrame(
        {
            "year": ["FY2024", "2023-24"],
            "value": [100, 200],
        }
    )

    result = normalize_dataframe(df)

    assert result["year"].tolist() == [2024, 2023]


def test_normalize_dataframe_ticker():
    df = pd.DataFrame(
        {
            "ticker": ["RELIANCE.NS", "TCS.BSE"],
        }
    )

    result = normalize_dataframe(df)

    assert result["ticker"].tolist() == ["RELIANCE", "TCS"]


def test_normalize_dataframe_preserves_other_columns():
    df = pd.DataFrame(
        {
            "company": ["ABC", "XYZ"],
            "value": [100, 200],
        }
    )

    result = normalize_dataframe(df)

    assert result["company"].tolist() == ["ABC", "XYZ"]
    assert result["value"].tolist() == [100, 200]


def test_load_directory(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    excel_file = data_dir / "companies.xlsx"

    pd.DataFrame(
        {
            "year": ["FY2024"],
            "ticker": ["RELIANCE.NS"],
        }
    ).to_excel(excel_file, index=False)

    result = load_directory(data_dir)

    assert "companies.xlsx" in result
    assert "Sheet1" in result["companies.xlsx"]

    loaded_df = result["companies.xlsx"]["Sheet1"]

    assert loaded_df["year"].iloc[0] == 2024
    assert loaded_df["ticker"].iloc[0] == "RELIANCE"


def test_load_directory_empty(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    result = load_directory(data_dir)

    assert result == {}


def test_load_directory_missing(tmp_path):
    missing_dir = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        load_directory(missing_dir)