"""
Load audit utilities for the NIFTY100 ETL pipeline.
"""

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass
class AuditRecord:
    table_name: str
    source_file: str
    rows_read: int
    rows_loaded: int
    rows_rejected: int
    severity: str
    message: str


class LoadAudit:
    """Collect and export ETL load statistics."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def add(
        self,
        table_name: str,
        source_file: str,
        rows_read: int,
        rows_loaded: int,
        rows_rejected: int = 0,
        severity: str = "INFO",
        message: str = "",
    ) -> None:
        if rows_read < 0:
            raise ValueError("rows_read cannot be negative")

        if rows_loaded < 0:
            raise ValueError("rows_loaded cannot be negative")

        if rows_rejected < 0:
            raise ValueError("rows_rejected cannot be negative")

        if rows_loaded + rows_rejected > rows_read:
            raise ValueError(
                "rows_loaded + rows_rejected cannot exceed rows_read"
            )

        if severity not in {"INFO", "WARNING", "CRITICAL"}:
            raise ValueError(f"Invalid severity: {severity}")

        self.records.append(
            AuditRecord(
                table_name=table_name,
                source_file=source_file,
                rows_read=rows_read,
                rows_loaded=rows_loaded,
                rows_rejected=rows_rejected,
                severity=severity,
                message=message,
            )
        )

    def to_dataframe(self) -> pd.DataFrame:
        columns = [
            "table_name",
            "source_file",
            "rows_read",
            "rows_loaded",
            "rows_rejected",
            "severity",
            "message",
        ]

        if not self.records:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame(
            [asdict(record) for record in self.records],
            columns=columns,
        )

    def save(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.to_dataframe().to_csv(path, index=False)

        return path

    def has_critical_rejections(self) -> bool:
        return any(
            record.severity == "CRITICAL"
            and record.rows_rejected > 0
            for record in self.records
        )