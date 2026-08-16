import pandas as pd
import pytest

from src.etl.load_audit import AuditRecord, LoadAudit


def test_audit_starts_empty():
    audit = LoadAudit()

    assert audit.records == []
    assert audit.to_dataframe().empty


def test_add_audit_record():
    audit = LoadAudit()

    audit.add(
        table_name="companies",
        source_file="companies.xlsx",
        rows_read=92,
        rows_loaded=92,
    )

    assert len(audit.records) == 1
    assert audit.records[0].table_name == "companies"
    assert audit.records[0].rows_loaded == 92


def test_audit_dataframe():
    audit = LoadAudit()

    audit.add(
        "companies",
        "companies.xlsx",
        92,
        92,
    )

    result = audit.to_dataframe()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["rows_read"] == 92


def test_negative_rows_read():
    audit = LoadAudit()

    with pytest.raises(ValueError):
        audit.add(
            "companies",
            "companies.xlsx",
            -1,
            0,
        )


def test_negative_rows_loaded():
    audit = LoadAudit()

    with pytest.raises(ValueError):
        audit.add(
            "companies",
            "companies.xlsx",
            10,
            -1,
        )


def test_negative_rows_rejected():
    audit = LoadAudit()

    with pytest.raises(ValueError):
        audit.add(
            "companies",
            "companies.xlsx",
            10,
            10,
            -1,
        )


def test_loaded_plus_rejected_cannot_exceed_read():
    audit = LoadAudit()

    with pytest.raises(ValueError):
        audit.add(
            "companies",
            "companies.xlsx",
            10,
            8,
            5,
        )


def test_invalid_severity():
    audit = LoadAudit()

    with pytest.raises(ValueError):
        audit.add(
            "companies",
            "companies.xlsx",
            10,
            10,
            severity="ERROR",
        )


def test_critical_rejection_detection():
    audit = LoadAudit()

    audit.add(
        "companies",
        "companies.xlsx",
        100,
        98,
        2,
        "CRITICAL",
        "Invalid company records",
    )

    assert audit.has_critical_rejections() is True


def test_no_critical_rejections():
    audit = LoadAudit()

    audit.add(
        "companies",
        "companies.xlsx",
        100,
        100,
    )

    assert audit.has_critical_rejections() is False


def test_save_audit_report(tmp_path):
    audit = LoadAudit()

    audit.add(
        "companies",
        "companies.xlsx",
        92,
        92,
    )

    output_file = tmp_path / "load_audit.csv"

    result = audit.save(output_file)

    assert result.exists()

    saved = pd.read_csv(output_file)

    assert len(saved) == 1
    assert saved.iloc[0]["table_name"] == "companies"


def test_audit_record_defaults():
    record = AuditRecord(
        table_name="companies",
        source_file="companies.xlsx",
        rows_read=92,
        rows_loaded=92,
        rows_rejected=0,
        severity="INFO",
        message="",
    )

    assert record.rows_read == 92
    assert record.rows_loaded == 92
    assert record.rows_rejected == 0