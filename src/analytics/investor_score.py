from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"

VALUATION_FILE = OUTPUT_DIR / "valuation_summary.xlsx"
PEER_FILE = OUTPUT_DIR / "peer_comparison.xlsx"
CAPITAL_FILE = OUTPUT_DIR / "capital_allocation.csv"

OUTPUT_FILE = OUTPUT_DIR / "investor_score.xlsx"


def normalize_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Convert a metric into a 0-100 score using min-max normalization."""
    numeric = pd.to_numeric(series, errors="coerce")

    if not higher_is_better:
        numeric = -numeric

    minimum = numeric.min()
    maximum = numeric.max()

    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(50.0, index=series.index)

    return ((numeric - minimum) / (maximum - minimum) * 100).clip(0, 100)


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column from a list of possible names."""
    normalized = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in df.columns
    }

    for candidate in candidates:
        key = candidate.lower().replace(" ", "_")
        if key in normalized:
            return normalized[key]

    return None


def load_data() -> pd.DataFrame:
    """Load and merge the available Day 27 analytics outputs."""

    if not VALUATION_FILE.exists():
        raise FileNotFoundError(f"Missing file: {VALUATION_FILE}")

    valuation = pd.read_excel(VALUATION_FILE)

    frames = [valuation]

    if PEER_FILE.exists():
        peer = pd.read_excel(PEER_FILE)
        if "company_id" in peer.columns:
            peer = peer.drop_duplicates("company_id")
            frames.append(peer)

    if CAPITAL_FILE.exists():
        capital = pd.read_csv(CAPITAL_FILE)
        if "company_id" in capital.columns:
            capital = capital.drop_duplicates("company_id")
            frames.append(capital)

    result = frames[0].copy()

    for frame in frames[1:]:
        common_keys = [
            column
            for column in ["company_id", "company_name"]
            if column in result.columns and column in frame.columns
        ]

        if common_keys:
            result = result.merge(
                frame,
                on=common_keys[0],
                how="left",
                suffixes=("", "_additional"),
            )

    return result


def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate valuation, quality and overall investor scores."""

    result = df.copy()

    # -----------------------------
    # Valuation score
    # -----------------------------
    valuation_components = []

    pe_col = find_column(result, ["P/E", "PE", "pe_ratio"])
    pb_col = find_column(result, ["P/B", "PB", "pb_ratio"])
    ev_col = find_column(result, ["EV/EBITDA", "ev_ebitda"])
    fcf_col = find_column(result, ["FCF_yield_pct", "FCF Yield", "fcf_yield"])

    if pe_col:
        valuation_components.append(
            normalize_score(result[pe_col], higher_is_better=False)
        )

    if pb_col:
        valuation_components.append(
            normalize_score(result[pb_col], higher_is_better=False)
        )

    if ev_col:
        valuation_components.append(
            normalize_score(result[ev_col], higher_is_better=False)
        )

    if fcf_col:
        valuation_components.append(
            normalize_score(result[fcf_col], higher_is_better=True)
        )

    if valuation_components:
        result["valuation_score"] = (
        pd.concat(valuation_components, axis=1)
        .mean(axis=1, skipna=True)
        .fillna(50.0)
    )
    else:
        result["valuation_score"] = 50.0

    # -----------------------------
    # Quality / fundamentals score
    # -----------------------------
    quality_candidates = [
        "ROE",
        "ROCE",
        "ROA",
        "profit_margin_pct",
        "net_margin_pct",
        "operating_margin_pct",
        "revenue_growth_pct",
        "profit_growth_pct",
    ]

    quality_components = []

    for candidate in quality_candidates:
        column = find_column(result, [candidate])
        if column:
            quality_components.append(
                normalize_score(result[column], higher_is_better=True)
            )

    if quality_components:
        result["quality_score"] = (
        pd.concat(quality_components, axis=1)
        .mean(axis=1, skipna=True)
        .fillna(50.0)
    )
    else:
        result["quality_score"] = 50.0

    # -----------------------------
    # Capital allocation score
    # -----------------------------
    capital_components = []

    for candidate in [
        "dividend_yield_pct",
        "dividend_yield",
        "buyback_yield_pct",
        "capital_efficiency",
    ]:
        column = find_column(result, [candidate])
        if column:
            capital_components.append(
                normalize_score(result[column], higher_is_better=True)
            )

    if capital_components:
        result["capital_allocation_score"] = (
        pd.concat(capital_components, axis=1)
        .mean(axis=1, skipna=True)
        .fillna(50.0)
    )
    else:
        result["capital_allocation_score"] = 50.0

    # -----------------------------
    # Overall investor score
    # -----------------------------
    result["investor_score"] = (
        result["valuation_score"] * 0.40
        + result["quality_score"] * 0.40
        + result["capital_allocation_score"] * 0.20
    ).round(2)

    result["investor_rank"] = (
    result["investor_score"]
    .rank(method="min", ascending=False)
    .astype("Int64")
)

    # -----------------------------
    # Investor classification
    # -----------------------------
    def classify(score: float) -> str:
        if score >= 75:
            return "Strong"
        if score >= 60:
            return "Positive"
        if score >= 40:
            return "Neutral"
        if score >= 25:
            return "Weak"
        return "Very Weak"

    result["investor_signal"] = result["investor_score"].apply(classify)

    return result


def main() -> None:
    print("Loading Sprint 4 Day 27 analytics data...")

    df = load_data()

    print(f"Loaded {len(df)} companies.")

    result = calculate_scores(df)

    preferred_columns = [
        "company_id",
        "company_name",
        "sector",
        "valuation_score",
        "quality_score",
        "capital_allocation_score",
        "investor_score",
        "investor_rank",
        "investor_signal",
    ]

    output_columns = [
        column for column in preferred_columns if column in result.columns
    ]

    remaining_columns = [
        column for column in result.columns
        if column not in output_columns
    ]

    final = result[output_columns + remaining_columns]

    final = final.sort_values(
        ["investor_rank", "company_name"],
        ascending=[True, True],
    )

    final.to_excel(OUTPUT_FILE, index=False)

    print(f"Created: {OUTPUT_FILE}")
    print(f"Companies scored: {len(final)}")

    print("\nTop 10 companies:")
    print(
        final[
            [
                "company_name",
                "investor_score",
                "investor_rank",
                "investor_signal",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()