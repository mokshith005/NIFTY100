import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.utils.db import get_companies, get_ratios, get_pl


st.set_page_config(
    page_title="Home | Nifty 100 Analytics",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Nifty 100 Analytics")
st.caption("Market overview and key financial indicators")

companies = get_companies()

if companies.empty:
    st.error("No company data available.")
    st.stop()

# ---------------------------------------------------------
# YEAR SELECTOR
# ---------------------------------------------------------

year = st.selectbox(
    "Select Financial Year",
    list(range(2019, 2025)),
    index=5,
)

# ---------------------------------------------------------
# LOAD FINANCIAL RATIOS
# ---------------------------------------------------------

ratio_rows = []

for ticker in companies["company_id"].dropna():
    try:
        df = get_ratios(ticker, year)

        if not df.empty:
            row = df.iloc[-1].to_dict()
            row["company_id"] = ticker
            ratio_rows.append(row)

    except Exception:
        continue

ratios = pd.DataFrame(ratio_rows)

if ratios.empty:
    st.warning(f"No financial data available for {year}.")
    st.stop()

# Keep only ratio columns before merging.
# This prevents company_name / sector duplicate-column problems.
ratio_columns = [
    "company_id",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
]

ratio_columns = [
    col for col in ratio_columns
    if col in ratios.columns
]

ratios = ratios[ratio_columns].copy()

data = companies.merge(
    ratios,
    on="company_id",
    how="left",
)

# ---------------------------------------------------------
# NUMERIC CONVERSION
# ---------------------------------------------------------

numeric_columns = [
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
]

for column in numeric_columns:
    if column in data.columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

# ---------------------------------------------------------
# KPI CALCULATIONS
# ---------------------------------------------------------

avg_roe = data["return_on_equity_pct"].mean()

median_de = data["debt_to_equity"].median()

total_companies = len(companies)

debt_free_count = (
    data["debt_to_equity"]
    .fillna(999)
    .le(0)
    .sum()
)

# P/E is not available in the current financial_ratios schema.
median_pe = None

# ---------------------------------------------------------
# REVENUE CAGR 5 YEAR
# ---------------------------------------------------------

cagr_values = []

for ticker in companies["company_id"].dropna():

    try:
        pl = get_pl(ticker)

        if pl.empty:
            continue

        if "revenue" not in pl.columns:
            continue

        temp = pl.copy()

        temp["year"] = pd.to_numeric(
            temp["year"],
            errors="coerce",
        )

        temp["revenue"] = pd.to_numeric(
            temp["revenue"],
            errors="coerce",
        )

        temp = temp.dropna(
            subset=["year", "revenue"]
        ).sort_values("year")

        if len(temp) >= 6:

            start_revenue = temp.iloc[-6]["revenue"]
            end_revenue = temp.iloc[-1]["revenue"]

            if start_revenue > 0 and end_revenue > 0:

                cagr = (
                    (end_revenue / start_revenue)
                    ** (1 / 5)
                    - 1
                ) * 100

                cagr_values.append(cagr)

    except Exception:
        continue

if cagr_values:
    median_revenue_cagr = pd.Series(cagr_values).median()
else:
    median_revenue_cagr = None

# ---------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric(
    "Average ROE",
    f"{avg_roe:.2f}%"
    if pd.notna(avg_roe)
    else "N/A",
)

k2.metric(
    "Median P/E",
    "N/A"
    if median_pe is None
    else f"{median_pe:.2f}",
)

k3.metric(
    "Median D/E",
    f"{median_de:.2f}"
    if pd.notna(median_de)
    else "N/A",
)

k4.metric(
    "Total Companies",
    str(total_companies),
)

k5.metric(
    "Median Revenue CAGR 5Y",
    f"{median_revenue_cagr:.2f}%"
    if median_revenue_cagr is not None
    and pd.notna(median_revenue_cagr)
    else "N/A",
)

k6.metric(
    "Debt-Free Companies",
    str(debt_free_count),
)

st.divider()

# ---------------------------------------------------------
# SECTOR DISTRIBUTION
# ---------------------------------------------------------

left, right = st.columns(2)

with left:

    st.subheader("📊 Sector Distribution")

    sector_counts = (
        companies["sector"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    sector_counts.columns = [
        "sector",
        "companies",
    ]

    fig = px.pie(
        sector_counts,
        names="sector",
        values="companies",
        hole=0.55,
    )

    fig.update_layout(
        height=450,
        margin=dict(
            l=20,
            r=20,
            t=40,
            b=20,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

# ---------------------------------------------------------
# TOP 5 QUALITY COMPANIES
# ---------------------------------------------------------

with right:

    st.subheader("🏆 Top 5 Quality Companies")

    quality = data.copy()

    score_parts = []

    if "return_on_equity_pct" in quality.columns:
        score_parts.append(
            quality[
                "return_on_equity_pct"
            ].rank(
                pct=True,
                na_option="keep",
            )
        )

    if "net_profit_margin_pct" in quality.columns:
        score_parts.append(
            quality[
                "net_profit_margin_pct"
            ].rank(
                pct=True,
                na_option="keep",
            )
        )

    if "operating_profit_margin_pct" in quality.columns:
        score_parts.append(
            quality[
                "operating_profit_margin_pct"
            ].rank(
                pct=True,
                na_option="keep",
            )
        )

    if "debt_to_equity" in quality.columns:
        debt_rank = quality[
            "debt_to_equity"
        ].rank(
            pct=True,
            na_option="keep",
        )

        score_parts.append(
            1 - debt_rank
        )

    if score_parts:

        score_df = pd.concat(
            score_parts,
            axis=1,
        )

        quality["composite_quality_score"] = (
            score_df.mean(axis=1)
            * 100
        )

        top5 = quality[
            [
                "company_id",
                "company_name",
                "sector",
                "composite_quality_score",
            ]
        ].copy()

        top5 = (
            top5
            .dropna(
                subset=[
                    "composite_quality_score"
                ]
            )
            .sort_values(
                "composite_quality_score",
                ascending=False,
            )
            .head(5)
        )

        top5[
            "composite_quality_score"
        ] = top5[
            "composite_quality_score"
        ].round(2)

        st.dataframe(
            top5,
            hide_index=True,
            use_container_width=True,
        )

    else:

        st.info(
            "Quality score data unavailable."
        )

st.success(
    f"Home dashboard loaded successfully for {year}."
)