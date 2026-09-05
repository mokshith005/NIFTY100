import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -------------------------------------------------------------------
# Project path
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_ratios


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Financial Trends | Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Financial Trends")
st.caption("Analyze 10-year financial trends for Nifty 100 companies.")


# -------------------------------------------------------------------
# Load companies
# -------------------------------------------------------------------
companies = get_companies()

if companies.empty:
    st.warning("Company data is unavailable.")
    st.stop()


companies = companies.copy()

companies["company_id"] = companies["company_id"].astype(str)
companies["company_name"] = companies["company_name"].fillna("").astype(str)

companies["display_name"] = (
    companies["company_id"] + " — " + companies["company_name"]
)

company_options = companies["display_name"].tolist()


# -------------------------------------------------------------------
# Company selector
# -------------------------------------------------------------------
st.subheader("🏢 Select Company")

selected_display = st.selectbox(
    "Company",
    company_options,
    index=0,
)

selected_ticker = selected_display.split(" — ", 1)[0]

selected_company = companies[
    companies["company_id"] == selected_ticker
].iloc[0]


st.info(
    f"Showing historical trends for **{selected_company['company_name']} "
    f"({selected_ticker})**."
)


# -------------------------------------------------------------------
# Load ratio history
# -------------------------------------------------------------------
ratios = get_ratios(selected_ticker)

if ratios.empty:
    st.warning(
        f"No historical financial data is available for {selected_ticker}."
    )
    st.stop()


ratios = ratios.copy()

if "year" not in ratios.columns:
    st.error("Historical year information is unavailable.")
    st.stop()


ratios["year"] = pd.to_numeric(
    ratios["year"],
    errors="coerce",
)

ratios = ratios.dropna(subset=["year"])

ratios["year"] = ratios["year"].astype(int)

ratios = ratios.sort_values("year")


# -------------------------------------------------------------------
# Available trend metrics
# -------------------------------------------------------------------
metric_labels = {
    "return_on_equity_pct": "ROE (%)",
    "net_profit_margin_pct": "Net Profit Margin (%)",
    "operating_profit_margin_pct": "Operating Profit Margin (%)",
    "debt_to_equity": "Debt / Equity",
    "interest_coverage": "Interest Coverage",
    "asset_turnover": "Asset Turnover",
    "free_cash_flow_cr": "Free Cash Flow (₹ Cr)",
    "earnings_per_share": "EPS (₹)",
    "book_value_per_share": "Book Value / Share (₹)",
    "dividend_payout_ratio_pct": "Dividend Payout (%)",
    "total_debt_cr": "Total Debt (₹ Cr)",
    "cash_from_operations_cr": "Cash From Operations (₹ Cr)",
}


available_metrics = [
    column
    for column in metric_labels
    if column in ratios.columns
]


if not available_metrics:
    st.warning("No suitable financial metrics are available.")
    st.stop()


# -------------------------------------------------------------------
# Metric selector
# -------------------------------------------------------------------
st.subheader("📊 Select Metrics")

selected_metrics = st.multiselect(
    "Choose up to 3 metrics",
    options=available_metrics,
    default=available_metrics[:2],
    max_selections=3,
    format_func=lambda x: metric_labels.get(x, x),
)


if not selected_metrics:
    st.info("Select at least one metric to display the trend.")
    st.stop()


# -------------------------------------------------------------------
# Prepare data
# -------------------------------------------------------------------
trend_df = ratios[["year"] + selected_metrics].copy()

for metric in selected_metrics:
    trend_df[metric] = pd.to_numeric(
        trend_df[metric],
        errors="coerce",
    )

trend_df = trend_df.sort_values("year")


# Keep the latest 10 available years
trend_df = trend_df.tail(10).reset_index(drop=True)


if trend_df.empty:
    st.warning("No historical observations are available.")
    st.stop()


# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
st.subheader("📌 Trend Summary")

summary_cols = st.columns(len(selected_metrics))

for col, metric in zip(summary_cols, selected_metrics):

    series = trend_df[metric].dropna()

    if series.empty:
        latest_text = "N/A"
        change_text = "N/A"
    else:
        latest_value = series.iloc[-1]

        if "pct" in metric:
            latest_text = f"{latest_value:.2f}%"
        elif metric in {
            "free_cash_flow_cr",
            "total_debt_cr",
            "cash_from_operations_cr",
        }:
            latest_text = f"₹{latest_value:,.2f} Cr"
        elif metric in {
            "earnings_per_share",
            "book_value_per_share",
        }:
            latest_text = f"₹{latest_value:,.2f}"
        else:
            latest_text = f"{latest_value:.2f}"

        if len(series) >= 2 and series.iloc[-2] != 0:
            yoy = (
                (series.iloc[-1] - series.iloc[-2])
                / abs(series.iloc[-2])
            ) * 100

            change_text = f"{yoy:+.2f}% YoY"
        else:
            change_text = "N/A"

    with col:
        st.metric(
            label=metric_labels.get(metric, metric),
            value=latest_text,
            delta=change_text,
        )


# -------------------------------------------------------------------
# Plotly trend chart
# -------------------------------------------------------------------
st.subheader("📈 10-Year Financial Trend")

fig = go.Figure()

for metric in selected_metrics:

    plot_data = trend_df[
        ["year", metric]
    ].dropna()

    if plot_data.empty:
        continue

    fig.add_trace(
        go.Scatter(
            x=plot_data["year"],
            y=plot_data[metric],
            mode="lines+markers",
            name=metric_labels.get(metric, metric),
            hovertemplate=(
                "<b>%{x}</b><br>"
                + metric_labels.get(metric, metric)
                + ": %{y:.2f}"
                + "<extra></extra>"
            ),
        )
    )

    # ---------------------------------------------------------------
    # YoY annotations
    # ---------------------------------------------------------------
    for i in range(1, len(plot_data)):

        current_value = plot_data.iloc[i][metric]
        previous_value = plot_data.iloc[i - 1][metric]

        if pd.isna(current_value) or pd.isna(previous_value):
            continue

        if previous_value == 0:
            continue

        yoy = (
            (current_value - previous_value)
            / abs(previous_value)
        ) * 100

        fig.add_annotation(
            x=plot_data.iloc[i]["year"],
            y=current_value,
            text=f"{yoy:+.1f}%",
            showarrow=False,
            yshift=12,
            font=dict(size=10),
        )


fig.update_layout(
    height=600,
    hovermode="x unified",
    xaxis_title="Financial Year",
    yaxis_title="Metric Value",
    legend_title="Metrics",
    margin=dict(l=50, r=30, t=50, b=50),
)

fig.update_xaxes(
    dtick=1,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# -------------------------------------------------------------------
# Historical data table
# -------------------------------------------------------------------
with st.expander("📋 View Historical Data"):

    display_df = trend_df.copy()

    display_df.columns = [
        "Year"
        if column == "year"
        else metric_labels.get(column, column)
        for column in display_df.columns
    ]

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
    )


# -------------------------------------------------------------------
# Data availability note
# -------------------------------------------------------------------
available_years = sorted(
    trend_df["year"].dropna().unique().tolist()
)

if len(available_years) < 10:
    st.warning(
        f"Only {len(available_years)} years of data are available "
        f"for {selected_ticker}. The chart displays all available years."
    )
else:
    st.success(
        f"10-year trend loaded successfully for "
        f"{selected_company['company_name']}."
    )