"""
Sprint 5 - Day 29
NLP Analysis Text Parser

Parses structured growth/ROE text from data/raw/core/analysis.xlsx.

Expected source fields:
    - compounded_sales_growth
    - compounded_profit_growth
    - stock_price_cagr
    - roe

Expected pattern:
    (\d+)\s*Years?:?\s*([\d.]+)%

Non-matching values are recorded in output/parse_failures.csv.
"""

from pathlib import Path
import re

import pandas as pd



PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "core" / "analysis.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "output"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURES_FILE = OUTPUT_DIR / "parse_failures.csv"

PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%")

TARGET_FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]


def load_analysis():
    """Load analysis.xlsx using row 2 as the real header."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Analysis file not found: {INPUT_FILE}")

    # Row 1 of the workbook is a title; row 2 contains the headers.
    df = pd.read_excel(INPUT_FILE, header=1)

    required = {"company_id", *TARGET_FIELDS}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    return df


def parse_value(value):
    """
    Parse a value using the Sprint 5 regex.

    Returns:
        (period_years, value_pct)
        or (None, None) when the value does not match.
    """
    if pd.isna(value):
        return None, None

    text = str(value).strip()
    match = PATTERN.search(text)

    if not match:
        return None, None

    period_years = int(match.group(1))
    value_pct = float(match.group(2))

    return period_years, value_pct


def parse_analysis():
    """Parse all supported analysis fields."""
    df = load_analysis()

    parsed_rows = []
    failures = []

    for _, row in df.iterrows():
        company_id = str(row["company_id"]).strip()

        for metric_type in TARGET_FIELDS:
            raw_value = row[metric_type]
            period_years, value_pct = parse_value(raw_value)

            if period_years is None:
                failures.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_value": (
                            "" if pd.isna(raw_value) else str(raw_value)
                        ),
                        "reason": "Pattern did not match",
                    }
                )
                continue

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    return pd.DataFrame(parsed_rows), pd.DataFrame(failures)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_df, failures_df = parse_analysis()

    parsed_columns = [
        "company_id",
        "metric_type",
        "period_years",
        "value_pct",
    ]

    failure_columns = [
        "company_id",
        "metric_type",
        "raw_value",
        "reason",
    ]

    if parsed_df.empty:
        parsed_df = pd.DataFrame(columns=parsed_columns)
    else:
        parsed_df = parsed_df[parsed_columns]

    if failures_df.empty:
        failures_df = pd.DataFrame(columns=failure_columns)
    else:
        failures_df = failures_df[failure_columns]

    parsed_df.to_csv(PARSED_FILE, index=False)
    failures_df.to_csv(FAILURES_FILE, index=False)

    print("=" * 60)
    print("SPRINT 5 - DAY 29: NLP ANALYSIS PARSER")
    print("=" * 60)
    print(f"Input file       : {INPUT_FILE}")
    print(f"Parsed output    : {PARSED_FILE}")
    print(f"Failure output   : {FAILURES_FILE}")
    print(f"Input rows       : {len(load_analysis())}")
    print(f"Parsed rows      : {len(parsed_df)}")
    print(f"Parse failures   : {len(failures_df)}")
    print("=" * 60)

    if not parsed_df.empty:
        print("\nParsed metric counts:")
        print(parsed_df["metric_type"].value_counts().to_string())

    if not failures_df.empty:
        print("\nParse failures:")
        print(failures_df.to_string(index=False))


if __name__ == "__main__":
    main()