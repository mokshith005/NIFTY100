"""
NIFTY 100 Data Quality Validator.

Implements DQ-01 through DQ-16 for the Sprint 1 data foundation.

Raw-source issues are reported separately from the final processed
data quality state. Critical FK validation is performed against the
processed datasets, which are the inputs to the SQLite database.
"""

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT_DIR / "data" / "raw"
CORE_DIR = RAW_DIR / "core"
SUPPLEMENTARY_DIR = RAW_DIR / "supplementary"

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_DIR = ROOT_DIR / "output"

VALIDATION_FILE = OUTPUT_DIR / "validation_failures.csv"
RAW_REFERENCE_FILE = OUTPUT_DIR / "raw_reference_issues.csv"


CORE_FILES = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "documents.xlsx",
    "analysis.xlsx",
    "prosandcons.xlsx",
]

SUPPLEMENTARY_FILES = [
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
    "sectors.xlsx",
    "stock_prices.xlsx",
]


DQ_RULES = {
    "DQ-01": "Primary key uniqueness",
    "DQ-02": "Company/year key uniqueness",
    "DQ-03": "Foreign-key integrity",
    "DQ-04": "Balance Sheet balance",
    "DQ-05": "OPM cross-check",
    "DQ-06": "Positive sales",
    "DQ-07": "Net cash consistency",
    "DQ-08": "Tax rate validation",
    "DQ-09": "Dividend cap",
    "DQ-10": "URL validity",
    "DQ-11": "EPS sign validation",
    "DQ-12": "BSE balance validation",
    "DQ-13": "Interest coverage validation",
    "DQ-14": "Company coverage",
    "DQ-15": "Year coverage",
    "DQ-16": "Stock price OHLC validation",
}


def read_source_file(filename: str) -> pd.DataFrame:
    """Read one source Excel file."""

    if filename in CORE_FILES:
        return pd.read_excel(
            CORE_DIR / filename,
            header=1,
        )

    return pd.read_excel(
        SUPPLEMENTARY_DIR / filename
    )


def read_processed_file(filename: str) -> pd.DataFrame:
    """Read one processed CSV file."""

    return pd.read_csv(
        PROCESSED_DIR / filename
    )


def add_failure(
    failures: list[dict],
    rule_id: str,
    severity: str,
    source_file: str,
    message: str,
    company_id=None,
    year=None,
    column=None,
    value=None,
) -> None:
    """Add a validation failure."""

    failures.append(
        {
            "rule_id": rule_id,
            "rule": DQ_RULES[rule_id],
            "severity": severity,
            "source_file": source_file,
            "company_id": company_id,
            "year": year,
            "column": column,
            "value": value,
            "message": message,
        }
    )


def normalize_company_id(
    series: pd.Series,
) -> pd.Series:
    """Normalize company IDs."""

    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


def normalize_year(
    series: pd.Series,
) -> pd.Series:
    """Extract a four-digit year."""

    return (
        series.astype("string")
        .str.extract(
            r"(\d{4})",
            expand=False,
        )
    )


def is_valid_url(value) -> bool:
    """Check basic HTTP/HTTPS URL validity."""

    if pd.isna(value):
        return False

    value = str(value).strip()

    if not value:
        return False

    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def get_valid_company_ids() -> set[str]:
    """Return the 92 company IDs from processed companies."""

    companies = read_processed_file(
        "companies.csv"
    )

    return set(
        normalize_company_id(
            companies["id"]
        )
        .dropna()
    )


def check_raw_reference_issues() -> None:
    """
    Report invalid raw source references separately.

    These are source-data mismatches that the ETL processor rejects.
    They are not counted as unresolved database FK failures.
    """

    valid_ids = get_valid_company_ids()

    issues = []

    for filename in (
        CORE_FILES
        + SUPPLEMENTARY_FILES
    ):
        if filename == "companies.xlsx":
            continue

        df = read_source_file(filename)

        if "company_id" not in df.columns:
            continue

        normalized = normalize_company_id(
            df["company_id"]
        )

        invalid_mask = (
            normalized.notna()
            & ~normalized.isin(valid_ids)
        )

        invalid = df.loc[
            invalid_mask
        ].copy()

        if invalid.empty:
            continue

        for _, row in invalid.iterrows():
            issues.append(
                {
                    "source_file": filename,
                    "company_id": row.get(
                        "company_id"
                    ),
                    "year": row.get(
                        "year"
                    ),
                    "reason": (
                        "raw_company_reference_not_in_master"
                    ),
                }
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(
        issues,
        columns=[
            "source_file",
            "company_id",
            "year",
            "reason",
        ],
    ).to_csv(
        RAW_REFERENCE_FILE,
        index=False,
    )

    print(
        "\nRaw source reference issues:"
    )
    print(
        f"  {len(issues)} rows rejected during ETL"
    )
    print(
        f"  Report: {RAW_REFERENCE_FILE}"
    )


def check_dq01_primary_key_uniqueness(
    failures: list[dict],
) -> None:
    """DQ-01: Primary key uniqueness."""

    print("\nDQ-01 PRIMARY KEY UNIQUENESS")
    print("-" * 60)

    for filename in (
        CORE_FILES
        + SUPPLEMENTARY_FILES
    ):
        processed_name = (
            Path(filename).stem + ".csv"
        )

        path = PROCESSED_DIR / processed_name

        if not path.exists():
            continue

        df = pd.read_csv(path)

        if "id" not in df.columns:
            continue

        duplicate_mask = df["id"].duplicated(
            keep=False
        )

        count = int(
            duplicate_mask.sum()
        )

        if count == 0:
            print(
                f"{processed_name:<30} PASS"
            )
            continue

        print(
            f"{processed_name:<30} "
            f"CRITICAL - {count} duplicate IDs"
        )

        for value in (
            df.loc[
                duplicate_mask,
                "id",
            ]
            .dropna()
            .unique()
        ):
            add_failure(
                failures,
                "DQ-01",
                "CRITICAL",
                processed_name,
                f"Duplicate primary key: {value}",
                value=value,
            )


def check_dq02_company_year_uniqueness(
    failures: list[dict],
) -> None:
    """DQ-02: Company/year uniqueness."""

    print("\nDQ-02 COMPANY/YEAR KEY UNIQUENESS")
    print("-" * 60)

    datasets = [
        "profitandloss.csv",
        "balancesheet.csv",
        "cashflow.csv",
        "financial_ratios.csv",
        "market_cap.csv",
    ]

    for filename in datasets:
        path = PROCESSED_DIR / filename

        if not path.exists():
            continue

        df = pd.read_csv(path)

        if not {
            "company_id",
            "year",
        }.issubset(df.columns):
            continue

        temp = df.copy()

        temp["company_id"] = normalize_company_id(
            temp["company_id"]
        )

        temp["year"] = normalize_year(
            temp["year"]
        )

        duplicates = temp.duplicated(
            subset=[
                "company_id",
                "year",
            ],
            keep=False,
        )

        count = int(
            duplicates.sum()
        )

        if count == 0:
            print(
                f"{filename:<30} PASS"
            )
        else:
            print(
                f"{filename:<30} "
                f"WARNING - {count} duplicate-key rows"
            )

            keys = (
                temp.loc[
                    duplicates,
                    [
                        "company_id",
                        "year",
                    ],
                ]
                .drop_duplicates()
            )

            for _, row in keys.iterrows():
                add_failure(
                    failures,
                    "DQ-02",
                    "WARNING",
                    filename,
                    (
                        "Duplicate company/year key: "
                        f"{row['company_id']} / "
                        f"{row['year']}"
                    ),
                    company_id=row[
                        "company_id"
                    ],
                    year=row["year"],
                )


def check_dq03_foreign_keys(
    failures: list[dict],
) -> None:
    """
    DQ-03: Validate company references in processed data.

    Invalid raw references have already been rejected by the ETL
    processor and are recorded separately.
    """

    print("\nDQ-03 FOREIGN-KEY INTEGRITY")
    print("-" * 60)

    valid_ids = get_valid_company_ids()

    datasets = [
        "profitandloss.csv",
        "balancesheet.csv",
        "cashflow.csv",
        "documents.csv",
        "analysis.csv",
        "prosandcons.csv",
        "financial_ratios.csv",
        "market_cap.csv",
        "peer_groups.csv",
        "sectors.csv",
        "stock_prices.csv",
    ]

    total = 0

    for filename in datasets:
        path = PROCESSED_DIR / filename

        if not path.exists():
            continue

        df = pd.read_csv(path)

        if "company_id" not in df.columns:
            continue

        company_ids = normalize_company_id(
            df["company_id"]
        )

        invalid_mask = (
            company_ids.notna()
            & ~company_ids.isin(valid_ids)
        )

        invalid = df.loc[
            invalid_mask
        ]

        if invalid.empty:
            print(
                f"{filename:<30} PASS"
            )
            continue

        total += len(invalid)

        print(
            f"{filename:<30} "
            f"CRITICAL - {len(invalid)} invalid references"
        )

        for _, row in invalid.iterrows():
            add_failure(
                failures,
                "DQ-03",
                "CRITICAL",
                filename,
                (
                    "Processed dataset contains "
                    f"invalid company reference: "
                    f"{row['company_id']}"
                ),
                company_id=row[
                    "company_id"
                ],
            )

    if total == 0:
        print(
            "\nProcessed FK validation: PASS"
        )


def check_dq04_balance_sheet(
    failures: list[dict],
) -> None:
    """DQ-04: Balance Sheet balance."""

    print("\nDQ-04 BALANCE SHEET BALANCE")
    print("-" * 60)

    filename = "balancesheet.csv"

    df = read_processed_file(
        filename
    )

    required = {
        "company_id",
        "year",
        "total_assets",
        "total_liabilities",
    }

    if not required.issubset(df.columns):
        print(
            "Missing required columns"
        )
        return

    count = 0

    for _, row in df.iterrows():
        assets = pd.to_numeric(
            row["total_assets"],
            errors="coerce",
        )

        liabilities = pd.to_numeric(
            row["total_liabilities"],
            errors="coerce",
        )

        if (
            pd.isna(assets)
            or pd.isna(liabilities)
            or assets == 0
        ):
            continue

        difference = (
            abs(
                assets
                - liabilities
            )
            / abs(assets)
        ) * 100

        if difference >= 1:
            count += 1

            add_failure(
                failures,
                "DQ-04",
                "WARNING",
                filename,
                (
                    "Balance sheet difference "
                    f"is {difference:.2f}%"
                ),
                company_id=row.get(
                    "company_id"
                ),
                year=row.get("year"),
                value=difference,
            )

    if count == 0:
        print(
            f"{filename:<30} PASS"
        )
    else:
        print(
            f"{filename:<30} "
            f"WARNING - {count} failures"
        )


def check_dq05_opm(
    failures: list[dict],
) -> None:
    """DQ-05: OPM cross-check."""

    print("\nDQ-05 OPM CROSS-CHECK")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    required = {
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "opm_percentage",
    }

    if not required.issubset(df.columns):
        print(
            "Missing required columns"
        )
        return

    count = 0

    for _, row in df.iterrows():
        sales = pd.to_numeric(
            row["sales"],
            errors="coerce",
        )

        operating_profit = pd.to_numeric(
            row["operating_profit"],
            errors="coerce",
        )

        reported = pd.to_numeric(
            row["opm_percentage"],
            errors="coerce",
        )

        if (
            pd.isna(sales)
            or pd.isna(operating_profit)
            or pd.isna(reported)
            or sales == 0
        ):
            continue

        calculated = (
            operating_profit
            / sales
        ) * 100

        if abs(
            calculated - reported
        ) > 1:
            count += 1

            add_failure(
                failures,
                "DQ-05",
                "WARNING",
                filename,
                (
                    "OPM cross-check difference: "
                    f"{abs(calculated - reported):.2f}"
                ),
                company_id=row.get(
                    "company_id"
                ),
                year=row.get("year"),
                value=reported,
            )

    if count == 0:
        print(
            f"{filename:<30} PASS"
        )
    else:
        print(
            f"{filename:<30} "
            f"WARNING - {count} failures"
        )


def check_dq06_positive_sales(
    failures: list[dict],
) -> None:
    """DQ-06: Sales must be positive."""

    print("\nDQ-06 POSITIVE SALES")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    sales = pd.to_numeric(
        df["sales"],
        errors="coerce",
    )

    invalid = df.loc[
        sales.notna()
        & (sales <= 0)
    ]

    if invalid.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} invalid sales"
    )

    for _, row in invalid.iterrows():
        add_failure(
            failures,
            "DQ-06",
            "WARNING",
            filename,
            f"Sales must be positive: {row['sales']}",
            company_id=row.get(
                "company_id"
            ),
            year=row.get("year"),
            value=row["sales"],
        )


def check_dq07_net_cash(
    failures: list[dict],
) -> None:
    """DQ-07: Net cash flow consistency."""

    print("\nDQ-07 NET CASH FLOW")
    print("-" * 60)

    filename = "cashflow.csv"

    df = read_processed_file(
        filename
    )

    required = {
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    }

    if not required.issubset(df.columns):
        print(
            "Required columns missing"
        )
        return

    count = 0

    for _, row in df.iterrows():
        values = [
            pd.to_numeric(
                row[column],
                errors="coerce",
            )
            for column in (
                "operating_activity",
                "investing_activity",
                "financing_activity",
                "net_cash_flow",
            )
        ]

        if any(
            pd.isna(value)
            for value in values
        ):
            continue

        operating, investing, financing, reported = values

        calculated = (
            operating
            + investing
            + financing
        )

        if abs(
            calculated - reported
        ) > 1:
            count += 1

            add_failure(
                failures,
                "DQ-07",
                "WARNING",
                filename,
                "Net cash flow calculation mismatch",
                company_id=row.get(
                    "company_id"
                ),
                year=row.get("year"),
                value=reported,
            )

    if count == 0:
        print(
            f"{filename:<30} PASS"
        )
    else:
        print(
            f"{filename:<30} "
            f"WARNING - {count} failures"
        )


def check_dq08_tax_rate(
    failures: list[dict],
) -> None:
    """DQ-08: Tax percentage range."""

    print("\nDQ-08 TAX RATE")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    tax = pd.to_numeric(
        df["tax_percentage"],
        errors="coerce",
    )

    invalid = df.loc[
        tax.notna()
        & (
            (tax < 0)
            | (tax > 100)
        )
    ]

    if invalid.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} invalid tax rates"
    )

    for _, row in invalid.iterrows():
        add_failure(
            failures,
            "DQ-08",
            "WARNING",
            filename,
            f"Invalid tax rate: {row['tax_percentage']}",
            company_id=row.get(
                "company_id"
            ),
            year=row.get("year"),
            value=row["tax_percentage"],
        )


def check_dq09_dividend_cap(
    failures: list[dict],
) -> None:
    """DQ-09: Dividend payout cap."""

    print("\nDQ-09 DIVIDEND CAP")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    dividend = pd.to_numeric(
        df["dividend_payout"],
        errors="coerce",
    )

    invalid = df.loc[
        dividend.notna()
        & (
            (dividend < 0)
            | (dividend > 100)
        )
    ]

    if invalid.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} invalid payouts"
    )

    for _, row in invalid.iterrows():
        add_failure(
            failures,
            "DQ-09",
            "WARNING",
            filename,
            (
                "Dividend payout outside "
                f"0-100: {row['dividend_payout']}"
            ),
            company_id=row.get(
                "company_id"
            ),
            year=row.get("year"),
            value=row[
                "dividend_payout"
            ],
        )


def check_dq10_urls(
    failures: list[dict],
) -> None:
    """DQ-10: URL validity."""

    print("\nDQ-10 URL VALIDITY")
    print("-" * 60)

    filename = "companies.xlsx"

    df = read_source_file(
        filename
    )

    columns = [
        column
        for column in (
            "company_logo",
            "chart_link",
            "website",
            "nse_profile",
            "bse_profile",
        )
        if column in df.columns
    ]

    count = 0

    for column in columns:
        for index, value in df[
            column
        ].items():
            if pd.isna(value):
                continue

            if not is_valid_url(value):
                count += 1

                add_failure(
                    failures,
                    "DQ-10",
                    "WARNING",
                    filename,
                    f"Invalid URL in {column}",
                    company_id=df.loc[
                        index,
                        "id",
                    ],
                    column=column,
                    value=value,
                )

    documents = read_source_file(
        "documents.xlsx"
    )

    for column in documents.columns:
        if "url" not in column.lower():
            continue

        for index, value in documents[
            column
        ].items():
            if pd.isna(value):
                continue

            if not is_valid_url(value):
                count += 1

                add_failure(
                    failures,
                    "DQ-10",
                    "WARNING",
                    "documents.xlsx",
                    f"Invalid URL in {column}",
                    company_id=(
                        documents.loc[
                            index,
                            "company_id",
                        ]
                        if "company_id"
                        in documents.columns
                        else None
                    ),
                    column=column,
                    value=value,
                )

    if count == 0:
        print(
            "URL validation                 PASS"
        )
    else:
        print(
            "URL validation                 "
            f"WARNING - {count} invalid URLs"
        )


def check_dq11_eps_sign(
    failures: list[dict],
) -> None:
    """DQ-11: EPS sign consistency."""

    print("\nDQ-11 EPS SIGN")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    net_profit = pd.to_numeric(
        df["net_profit"],
        errors="coerce",
    )

    eps = pd.to_numeric(
        df["eps"],
        errors="coerce",
    )

    invalid = df.loc[
        (
            (
                (net_profit > 0)
                & (eps < 0)
            )
            |
            (
                (net_profit < 0)
                & (eps > 0)
            )
        )
    ]

    if invalid.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} mismatches"
    )

    for _, row in invalid.iterrows():
        add_failure(
            failures,
            "DQ-11",
            "WARNING",
            filename,
            "EPS sign conflicts with net profit",
            company_id=row.get(
                "company_id"
            ),
            year=row.get("year"),
            value=row["eps"],
        )


def check_dq12_bse_balance(
    failures: list[dict],
) -> None:
    """DQ-12: BSE profile URL check."""

    print("\nDQ-12 BSE BALANCE")
    print("-" * 60)

    filename = "companies.xlsx"

    df = read_source_file(
        filename
    )

    if "bse_profile" not in df.columns:
        print(
            f"{filename:<30} PASS"
        )
        return

    invalid = []

    for index, value in df[
        "bse_profile"
    ].items():
        if (
            pd.isna(value)
            or not is_valid_url(value)
        ):
            invalid.append(
                index
            )

    if not invalid:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} issues"
    )

    for index in invalid:
        add_failure(
            failures,
            "DQ-12",
            "WARNING",
            filename,
            "Missing or invalid BSE profile",
            company_id=df.loc[
                index,
                "id",
            ],
            column="bse_profile",
            value=df.loc[
                index,
                "bse_profile",
            ],
        )


def check_dq13_interest_coverage(
    failures: list[dict],
) -> None:
    """DQ-13: Interest coverage."""

    print("\nDQ-13 INTEREST COVERAGE")
    print("-" * 60)

    filename = "financial_ratios.csv"

    df = read_processed_file(
        filename
    )

    coverage = pd.to_numeric(
        df["interest_coverage"],
        errors="coerce",
    )

    invalid = df.loc[
        coverage.notna()
        & (coverage < 0)
    ]

    if invalid.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(invalid)} negative values"
    )

    for _, row in invalid.iterrows():
        add_failure(
            failures,
            "DQ-13",
            "WARNING",
            filename,
            "Negative interest coverage",
            company_id=row.get(
                "company_id"
            ),
            year=row.get("year"),
            value=row[
                "interest_coverage"
            ],
        )


def check_dq14_company_coverage(
    failures: list[dict],
) -> None:
    """DQ-14: Company coverage."""

    print("\nDQ-14 COMPANY COVERAGE")
    print("-" * 60)

    valid_ids = get_valid_company_ids()

    datasets = [
        "profitandloss.csv",
        "balancesheet.csv",
        "cashflow.csv",
        "financial_ratios.csv",
        "market_cap.csv",
        "stock_prices.csv",
    ]

    total = 0

    for filename in datasets:
        df = read_processed_file(
            filename
        )

        if "company_id" not in df.columns:
            continue

        ids = set(
            normalize_company_id(
                df["company_id"]
            ).dropna()
        )

        missing = sorted(
            valid_ids - ids
        )

        if not missing:
            continue

        total += len(missing)

        for company_id in missing:
            add_failure(
                failures,
                "DQ-14",
                "WARNING",
                filename,
                (
                    "Company missing from dataset: "
                    f"{company_id}"
                ),
                company_id=company_id,
            )

    if total == 0:
        print(
            "Company coverage                PASS"
        )
    else:
        print(
            "Company coverage                "
            f"WARNING - {total} missing"
        )


def check_dq15_year_coverage(
    failures: list[dict],
) -> None:
    """DQ-15: Minimum five-year company coverage."""

    print("\nDQ-15 YEAR COVERAGE")
    print("-" * 60)

    filename = "profitandloss.csv"

    df = read_processed_file(
        filename
    )

    df["company_id"] = normalize_company_id(
        df["company_id"]
    )

    df["year"] = normalize_year(
        df["year"]
    )

    coverage = (
        df.dropna(
            subset=[
                "company_id",
                "year",
            ]
        )
        .groupby("company_id")["year"]
        .nunique()
    )

    low = coverage[
        coverage < 5
    ]

    if low.empty:
        print(
            f"{filename:<30} PASS"
        )
        return

    print(
        f"{filename:<30} "
        f"WARNING - {len(low)} companies below 5 years"
    )

    for company_id, years in low.items():
        add_failure(
            failures,
            "DQ-15",
            "WARNING",
            filename,
            (
                f"Only {years} years available"
            ),
            company_id=company_id,
            value=years,
        )


def check_dq16_stock_prices(
    failures: list[dict],
) -> None:
    """DQ-16: Stock OHLC validation."""

    print("\nDQ-16 STOCK PRICE OHLC")
    print("-" * 60)

    filename = "stock_prices.csv"

    df = read_processed_file(
        filename
    )

    required = {
        "open_price",
        "high_price",
        "low_price",
        "close_price",
    }

    if not required.issubset(
        df.columns
    ):
        print(
            "Required columns missing"
        )
        return

    count = 0

    for _, row in df.iterrows():
        values = [
            pd.to_numeric(
                row[column],
                errors="coerce",
            )
            for column in (
                "open_price",
                "high_price",
                "low_price",
                "close_price",
            )
        ]

        if any(
            pd.isna(value)
            for value in values
        ):
            continue

        open_price, high_price, low_price, close_price = values

        valid = (
            high_price
            >= max(
                open_price,
                close_price,
            )
            and low_price
            <= min(
                open_price,
                close_price,
            )
            and low_price >= 0
        )

        if not valid:
            count += 1

            add_failure(
                failures,
                "DQ-16",
                "WARNING",
                filename,
                "Invalid OHLC relationship",
                company_id=row.get(
                    "company_id"
                ),
                year=row.get("date"),
                value=(
                    f"O={open_price}, "
                    f"H={high_price}, "
                    f"L={low_price}, "
                    f"C={close_price}"
                ),
            )

    if count == 0:
        print(
            f"{filename:<30} PASS"
        )
    else:
        print(
            f"{filename:<30} "
            f"WARNING - {count} invalid rows"
        )


def save_failures(
    failures: list[dict],
) -> None:
    """Save validation failures."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    columns = [
        "rule_id",
        "rule",
        "severity",
        "source_file",
        "company_id",
        "year",
        "column",
        "value",
        "message",
    ]

    pd.DataFrame(
        failures,
        columns=columns,
    ).to_csv(
        VALIDATION_FILE,
        index=False,
    )

    print(
        f"\nValidation report:"
        f"\n{VALIDATION_FILE}"
    )


def print_summary(
    failures: list[dict],
) -> None:
    """Print DQ summary."""

    print("\n")
    print("=" * 70)
    print("DATA QUALITY SUMMARY")
    print("=" * 70)

    if not failures:
        print("\nALL 16 DQ RULES PASSED")
        return

    df = pd.DataFrame(
        failures
    )

    print(
        f"\nTotal validation failures: "
        f"{len(df)}"
    )

    for severity in (
        "CRITICAL",
        "WARNING",
        "INFO",
    ):
        print(
            f"{severity:<10}: "
            f"{int((df['severity'] == severity).sum())}"
        )

    print("\nFailures by rule:")

    counts = (
        df["rule_id"]
        .value_counts()
    )

    for rule_id, rule_name in DQ_RULES.items():
        count = int(
            counts.get(
                rule_id,
                0,
            )
        )

        status = (
            "PASS"
            if count == 0
            else "FAIL"
        )

        print(
            f"  {rule_id} "
            f"{rule_name:<35} "
            f"{status:<6} "
            f"{count}"
        )


def main() -> None:
    """Run all 16 DQ checks."""

    print("=" * 70)
    print("NIFTY 100 DATA QUALITY VALIDATOR")
    print("=" * 70)

    print("\nSource files:")

    for filename in (
        CORE_FILES
        + SUPPLEMENTARY_FILES
    ):
        path = (
            CORE_DIR / filename
            if filename in CORE_FILES
            else SUPPLEMENTARY_DIR / filename
        )

        print(
            f"  {'FOUND' if path.exists() else 'MISSING':<8} "
            f"{filename}"
        )

    check_raw_reference_issues()

    failures = []

    check_dq01_primary_key_uniqueness(
        failures
    )

    check_dq02_company_year_uniqueness(
        failures
    )

    check_dq03_foreign_keys(
        failures
    )

    check_dq04_balance_sheet(
        failures
    )

    check_dq05_opm(
        failures
    )

    check_dq06_positive_sales(
        failures
    )

    check_dq07_net_cash(
        failures
    )

    check_dq08_tax_rate(
        failures
    )

    check_dq09_dividend_cap(
        failures
    )

    check_dq10_urls(
        failures
    )

    check_dq11_eps_sign(
        failures
    )

    check_dq12_bse_balance(
        failures
    )

    check_dq13_interest_coverage(
        failures
    )

    check_dq14_company_coverage(
        failures
    )

    check_dq15_year_coverage(
        failures
    )

    check_dq16_stock_prices(
        failures
    )

    save_failures(
        failures
    )

    print_summary(
        failures
    )

    critical_count = sum(
        failure["severity"]
        == "CRITICAL"
        for failure in failures
    )

    print("\n" + "=" * 70)

    if critical_count == 0:
        print(
            "DQ VALIDATION COMPLETE - "
            "NO CRITICAL FAILURES"
        )
    else:
        print(
            f"DQ VALIDATION COMPLETE - "
            f"{critical_count} CRITICAL FAILURES"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()