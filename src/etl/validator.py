"""
Data Quality validation framework for the NIFTY100 ETL pipeline.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


@dataclass
class ValidationFailure:
    rule_id: str
    severity: str
    table: str
    column: str
    company_id: str | None
    year: int | None
    message: str


class Validator:
    """Execute registered data-quality rules."""

    VALID_SEVERITIES = {"CRITICAL", "WARNING", "INFO"}

    def __init__(self):
        self.rules: list[tuple[str, str, Callable]] = []
        self.failures: list[ValidationFailure] = []

    def register_rule(
        self,
        rule_id: str,
        severity: str,
        rule_function: Callable,
    ) -> None:
        """Register a validation rule."""

        if severity not in self.VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity: {severity}. "
                f"Use {self.VALID_SEVERITIES}."
            )

        if any(rule[0] == rule_id for rule in self.rules):
            raise ValueError(f"Rule already registered: {rule_id}")

        self.rules.append(
            (rule_id, severity, rule_function)
        )

    def run_rule(
        self,
        rule_id: str,
        data: pd.DataFrame,
        table: str,
    ) -> list[ValidationFailure]:
        """Run one registered validation rule."""

        matching_rules = [
            rule for rule in self.rules
            if rule[0] == rule_id
        ]

        if not matching_rules:
            raise ValueError(f"Rule not registered: {rule_id}")

        _, severity, rule_function = matching_rules[0]

        failures = rule_function(
            data=data,
            table=table,
            rule_id=rule_id,
            severity=severity,
        )

        self.failures.extend(failures)

        return failures

    def run_all(
        self,
        datasets: dict[str, pd.DataFrame],
    ) -> list[ValidationFailure]:
        """Run all registered rules against supplied datasets."""

        self.failures.clear()

        for rule_id, _, rule_function in self.rules:
            for table, data in datasets.items():
                failures = rule_function(
                    data=data,
                    table=table,
                    rule_id=rule_id,
                    severity=self._get_severity(rule_id),
                )

                self.failures.extend(failures)

        return self.failures

    def _get_severity(self, rule_id: str) -> str:
        """Return severity for a registered rule."""

        for registered_id, severity, _ in self.rules:
            if registered_id == rule_id:
                return severity

        raise ValueError(f"Rule not registered: {rule_id}")

    def to_dataframe(self) -> pd.DataFrame:
        """Convert validation failures to a DataFrame."""

        columns = [
            "rule_id",
            "severity",
            "table",
            "column",
            "company_id",
            "year",
            "message",
        ]

        if not self.failures:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame(
            [
                {
                    "rule_id": failure.rule_id,
                    "severity": failure.severity,
                    "table": failure.table,
                    "column": failure.column,
                    "company_id": failure.company_id,
                    "year": failure.year,
                    "message": failure.message,
                }
                for failure in self.failures
            ],
            columns=columns,
        )

    def save_report(
        self,
        output_path: str | Path,
    ) -> Path:
        """Save validation failures as CSV."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        report = self.to_dataframe()
        report.to_csv(path, index=False)

        return path


def example_rule(
    data: pd.DataFrame,
    table: str,
    rule_id: str,
    severity: str,
) -> list[ValidationFailure]:
    """
    Example rule used only for testing the framework.

    It reports rows containing null values.
    """

    failures = []

    for index, row in data.iterrows():
        if row.isna().any():
            failures.append(
                ValidationFailure(
                    rule_id=rule_id,
                    severity=severity,
                    table=table,
                    column="",
                    company_id=None,
                    year=None,
                    message=f"Null value detected at row {index}",
                )
            )

    return failures