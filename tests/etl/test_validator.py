import pandas as pd
import pytest

from src.etl.validator import (
    ValidationFailure,
    Validator,
    example_rule,
)


def test_validator_initially_has_no_rules():
    validator = Validator()

    assert validator.rules == []
    assert validator.failures == []


def test_register_rule():
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "CRITICAL",
        example_rule,
    )

    assert len(validator.rules) == 1
    assert validator.rules[0][0] == "DQ-TEST"


def test_invalid_severity():
    validator = Validator()

    with pytest.raises(ValueError):
        validator.register_rule(
            "DQ-TEST",
            "INVALID",
            example_rule,
        )


def test_duplicate_rule():
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "CRITICAL",
        example_rule,
    )

    with pytest.raises(ValueError):
        validator.register_rule(
            "DQ-TEST",
            "WARNING",
            example_rule,
        )


def test_run_rule_without_registration():
    validator = Validator()

    df = pd.DataFrame({"value": [1, 2]})

    with pytest.raises(ValueError):
        validator.run_rule(
            "DQ-TEST",
            df,
            "companies",
        )


def test_run_rule_detects_failure():
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "WARNING",
        example_rule,
    )

    df = pd.DataFrame(
        {
            "value": [1, None],
        }
    )

    failures = validator.run_rule(
        "DQ-TEST",
        df,
        "companies",
    )

    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-TEST"
    assert failures[0].severity == "WARNING"


def test_run_rule_with_clean_data():
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "WARNING",
        example_rule,
    )

    df = pd.DataFrame(
        {
            "value": [1, 2, 3],
        }
    )

    failures = validator.run_rule(
        "DQ-TEST",
        df,
        "companies",
    )

    assert failures == []


def test_to_dataframe_empty():
    validator = Validator()

    result = validator.to_dataframe()

    expected_columns = [
        "rule_id",
        "severity",
        "table",
        "column",
        "company_id",
        "year",
        "message",
    ]

    assert result.empty
    assert list(result.columns) == expected_columns


def test_to_dataframe_with_failure():
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "CRITICAL",
        example_rule,
    )

    df = pd.DataFrame(
        {
            "value": [None],
        }
    )

    validator.run_rule(
        "DQ-TEST",
        df,
        "companies",
    )

    result = validator.to_dataframe()

    assert len(result) == 1
    assert result.iloc[0]["rule_id"] == "DQ-TEST"
    assert result.iloc[0]["severity"] == "CRITICAL"


def test_save_report(tmp_path):
    validator = Validator()

    validator.register_rule(
        "DQ-TEST",
        "WARNING",
        example_rule,
    )

    df = pd.DataFrame(
        {
            "value": [None],
        }
    )

    validator.run_rule(
        "DQ-TEST",
        df,
        "companies",
    )

    output_file = tmp_path / "validation_failures.csv"

    result = validator.save_report(output_file)

    assert result.exists()

    saved = pd.read_csv(output_file)

    assert len(saved) == 1
    assert saved.iloc[0]["rule_id"] == "DQ-TEST"


def test_validation_failure_dataclass():
    failure = ValidationFailure(
        rule_id="DQ-01",
        severity="CRITICAL",
        table="companies",
        column="company_id",
        company_id="C001",
        year=2024,
        message="Duplicate company ID",
    )

    assert failure.rule_id == "DQ-01"
    assert failure.severity == "CRITICAL"
    assert failure.table == "companies"