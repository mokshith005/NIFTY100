from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"

INPUT_FILE = OUTPUT_DIR / "investor_score.xlsx"
OUTPUT_FILE = OUTPUT_DIR / "investment_recommendations.xlsx"


def classify_recommendation(score):
    if score >= 70:
        return "BUY"
    elif score >= 55:
        return "HOLD"
    elif score >= 40:
        return "WATCH"
    return "AVOID"


def calculate_confidence(row):
    scores = [
        row.get("valuation_score"),
        row.get("quality_score"),
        row.get("capital_allocation_score"),
    ]

    values = pd.to_numeric(pd.Series(scores), errors="coerce").dropna()

    if len(values) == 0:
        return 0.0

    dispersion = values.max() - values.min()

    confidence = 100 - dispersion

    return round(max(0.0, min(100.0, confidence)), 2)


def generate_reason(row):
    score = row["investor_score"]
    valuation = row["valuation_score"]
    quality = row["quality_score"]

    if score >= 70:
        action = "Strong overall investor score"
    elif score >= 55:
        action = "Moderate overall investor score"
    elif score >= 40:
        action = "Mixed investor profile"
    else:
        action = "Weak overall investor score"

    if valuation >= 60:
        valuation_text = "attractive valuation"
    elif valuation >= 40:
        valuation_text = "moderate valuation"
    else:
        valuation_text = "expensive valuation"

    if quality >= 60:
        quality_text = "strong fundamentals"
    elif quality >= 40:
        quality_text = "average fundamentals"
    else:
        quality_text = "weak fundamentals"

    return f"{action}; {valuation_text}; {quality_text}."


def risk_flag(row):
    score = row["investor_score"]

    if score < 40:
        return "High"

    if score < 55:
        return "Medium"

    return "Low"


def main():
    print("Loading Day 27 investor scores...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Required input not found: {INPUT_FILE}"
        )

    df = pd.read_excel(INPUT_FILE)

    required_columns = [
        "company_id",
        "company_name",
        "investor_score",
        "valuation_score",
        "quality_score",
        "capital_allocation_score",
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    print(f"Loaded {len(df)} companies.")

    df["recommendation"] = df["investor_score"].apply(
        classify_recommendation
    )

    df["confidence_score"] = df.apply(
        calculate_confidence,
        axis=1,
    )

    df["recommendation_reason"] = df.apply(
        generate_reason,
        axis=1,
    )

    df["risk_flag"] = df.apply(
        risk_flag,
        axis=1,
    )

    preferred_columns = [
        "company_id",
        "company_name",
        "sector",
        "investor_rank",
        "investor_score",
        "valuation_score",
        "quality_score",
        "capital_allocation_score",
        "recommendation",
        "confidence_score",
        "risk_flag",
        "recommendation_reason",
    ]

    output_columns = [
        column for column in preferred_columns
        if column in df.columns
    ]

    remaining_columns = [
        column for column in df.columns
        if column not in output_columns
    ]

    result = df[
        output_columns + remaining_columns
    ].sort_values(
        "investor_rank",
        ascending=True,
    )

    result.to_excel(
        OUTPUT_FILE,
        index=False,
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Companies processed: {len(result)}")

    print("\nRecommendation distribution:")
    print(
        result["recommendation"]
        .value_counts()
        .to_string()
    )

    print("\nTop 10 recommendations:")
    print(
        result[
            [
                "company_name",
                "investor_score",
                "recommendation",
                "confidence_score",
                "risk_flag",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()