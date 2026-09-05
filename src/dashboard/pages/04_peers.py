import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------
# Project path
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_peers, get_ratios


# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="Peer Comparison | Nifty 100 Analytics",
    page_icon="👥",
    layout="wide",
)

st.title("👥 Peer Comparison")
st.caption("Compare Nifty 100 companies against their sector peer groups.")


# ------------------------------------------------------------
# Peer groups
# ------------------------------------------------------------
PEER_GROUPS = [
    "Automobiles",
    "Consumer Finance",
    "FMCG",
    "IT Services",
    "Life Insurance",
    "Oil & Gas",
    "Pharmaceuticals",
    "Power & Utilities",
    "Private Banks",
    "Public Sector Banks",
    "Steel",
]


# ------------------------------------------------------------
# Metric configuration
# ------------------------------------------------------------
METRICS = {
    "NPM (%)": "net_profit_margin_pct",
    "OPM (%)": "operating_profit_margin_pct",
    "ROE (%)": "return_on_equity_pct",
    "D/E": "debt_to_equity",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
    "FCF (₹ Cr)": "free_cash_flow_cr",
    "Cash From Operations (₹ Cr)": "cash_from_operations_cr",
}


# ------------------------------------------------------------
# Helper
# ------------------------------------------------------------
def safe_number(value):
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except (TypeError, ValueError):
        pass

    return np.nan


@st.cache_data(ttl=600)
def build_peer_data(group_name):
    """
    Load all companies in a peer group and obtain their
    latest available financial ratios.
    """

    peers = get_peers(group_name)

    if peers.empty:
        return pd.DataFrame()

    rows = []

    for _, peer in peers.iterrows():

        ticker = peer["company_id"]

        try:
            ratios = get_ratios(ticker)

            if ratios.empty:
                rows.append(
                    {
                        "company_id": ticker,
                        "company_name": peer["company_name"],
                        "is_benchmark": peer["is_benchmark"],
                        **{metric: np.nan for metric in METRICS.values()},
                    }
                )
                continue

            ratios = ratios.copy()

            if "year" in ratios.columns:
                ratios["year"] = pd.to_numeric(
                    ratios["year"],
                    errors="coerce",
                )

                ratios = ratios.sort_values("year")

            latest = ratios.iloc[-1]

            row = {
                "company_id": ticker,
                "company_name": peer["company_name"],
                "is_benchmark": peer["is_benchmark"],
            }

            for metric_column in METRICS.values():
                row[metric_column] = safe_number(
                    latest.get(metric_column, np.nan)
                )

            row["year"] = latest.get("year", np.nan)

            rows.append(row)

        except Exception:
            rows.append(
                {
                    "company_id": ticker,
                    "company_name": peer["company_name"],
                    "is_benchmark": peer["is_benchmark"],
                    "year": np.nan,
                    **{metric: np.nan for metric in METRICS.values()},
                }
            )

    return pd.DataFrame(rows)


# ------------------------------------------------------------
# Peer group selector
# ------------------------------------------------------------
selected_group = st.selectbox(
    "Select Peer Group",
    PEER_GROUPS,
)

peer_data = build_peer_data(selected_group)

if peer_data.empty:
    st.warning(
        f"No companies were found for the peer group: {selected_group}"
    )
    st.stop()


# ------------------------------------------------------------
# Clean company names
# ------------------------------------------------------------
peer_data["company_name"] = (
    peer_data["company_name"]
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
benchmark_rows = peer_data[
    peer_data["is_benchmark"].astype(bool)
]

benchmark_ticker = (
    benchmark_rows.iloc[0]["company_id"]
    if not benchmark_rows.empty
    else None
)


c1, c2, c3 = st.columns(3)

c1.metric(
    "Peer Group",
    selected_group,
)

c2.metric(
    "Companies",
    len(peer_data),
)

c3.metric(
    "Benchmark",
    benchmark_ticker if benchmark_ticker else "N/A",
)


# ------------------------------------------------------------
# Company selection
# ------------------------------------------------------------
st.subheader("🎯 Company Comparison")

company_options = peer_data["company_id"].tolist()

default_index = (
    company_options.index(benchmark_ticker)
    if benchmark_ticker in company_options
    else 0
)

selected_ticker = st.selectbox(
    "Select Company",
    company_options,
    index=default_index,
)

selected_row = peer_data[
    peer_data["company_id"] == selected_ticker
]

if selected_row.empty:
    st.warning("Selected company data is unavailable.")
    st.stop()

selected_row = selected_row.iloc[0]


# ------------------------------------------------------------
# Company heading
# ------------------------------------------------------------
st.markdown(
    f"### {selected_row['company_name']} "
    f"(`{selected_ticker}`)"
)

if bool(selected_row.get("is_benchmark", 0)):
    st.success("This company is the benchmark company for this peer group.")


# ------------------------------------------------------------
# Radar chart data
# ------------------------------------------------------------
metric_names = list(METRICS.keys())

selected_values = []
peer_average_values = []

for display_name, db_column in METRICS.items():

    selected_value = safe_number(
        selected_row.get(db_column, np.nan)
    )

    peer_values = pd.to_numeric(
        peer_data[db_column],
        errors="coerce",
    ).dropna()

    peer_average = (
        peer_values.mean()
        if not peer_values.empty
        else np.nan
    )

    selected_values.append(selected_value)
    peer_average_values.append(peer_average)


# ------------------------------------------------------------
# Normalize metrics for radar
# ------------------------------------------------------------
def normalize_for_radar(values, averages):
    """
    Normalize each metric using the combined selected-company
    and peer-average values.

    This keeps metrics with very different scales readable.
    """

    result_values = []
    result_averages = []

    for value, average in zip(values, averages):

        numbers = [
            x
            for x in [value, average]
            if pd.notna(x)
        ]

        if not numbers:
            result_values.append(0)
            result_averages.append(0)
            continue

        minimum = min(numbers)
        maximum = max(numbers)

        if maximum == minimum:
            result_values.append(1)
            result_averages.append(1)
            continue

        result_values.append(
            (value - minimum) / (maximum - minimum)
            if pd.notna(value)
            else 0
        )

        result_averages.append(
            (average - minimum) / (maximum - minimum)
            if pd.notna(average)
            else 0
        )

    return result_values, result_averages


radar_selected, radar_average = normalize_for_radar(
    selected_values,
    peer_average_values,
)


# ------------------------------------------------------------
# Radar chart
# ------------------------------------------------------------
st.subheader("📡 Financial Radar")

fig = go.Figure()

fig.add_trace(
    go.Scatterpolar(
        r=radar_selected + [radar_selected[0]],
        theta=metric_names + [metric_names[0]],
        fill="toself",
        name=selected_ticker,
    )
)

fig.add_trace(
    go.Scatterpolar(
        r=radar_average + [radar_average[0]],
        theta=metric_names + [metric_names[0]],
        fill="toself",
        name="Peer Average",
    )
)

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 1],
        )
    ),
    showlegend=True,
    height=600,
    margin=dict(
        l=60,
        r=60,
        t=50,
        b=50,
    ),
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


st.caption(
    "Radar values are normalized for visualization because the "
    "underlying financial metrics have different units and scales."
)


# ------------------------------------------------------------
# KPI comparison
# ------------------------------------------------------------
st.subheader("📊 Selected Company vs Peer Average")

kpi_columns = st.columns(4)

for index, (display_name, db_column) in enumerate(METRICS.items()):

    selected_value = safe_number(
        selected_row.get(db_column, np.nan)
    )

    peer_values = pd.to_numeric(
        peer_data[db_column],
        errors="coerce",
    ).dropna()

    peer_average = (
        peer_values.mean()
        if not peer_values.empty
        else np.nan
    )

    column = kpi_columns[index % 4]

    if pd.notna(selected_value):
        if "₹ Cr" in display_name:
            selected_text = f"₹{selected_value:,.2f}"
        else:
            selected_text = f"{selected_value:,.2f}"
    else:
        selected_text = "N/A"

    if pd.notna(peer_average):
        if "₹ Cr" in display_name:
            average_text = f"₹{peer_average:,.2f}"
        else:
            average_text = f"{peer_average:,.2f}"
    else:
        average_text = "N/A"

    column.metric(
        display_name,
        selected_text,
        f"Peer avg: {average_text}",
    )


# ------------------------------------------------------------
# Full peer comparison table
# ------------------------------------------------------------
st.subheader("📋 All Peer Companies")

table = peer_data.copy()

table["Benchmark"] = table["is_benchmark"].apply(
    lambda x: "⭐ Benchmark" if bool(x) else ""
)

table = table.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "Benchmark": "Status",
        "net_profit_margin_pct": "NPM %",
        "operating_profit_margin_pct": "OPM %",
        "return_on_equity_pct": "ROE %",
        "debt_to_equity": "D/E",
        "interest_coverage": "Interest Coverage",
        "asset_turnover": "Asset Turnover",
        "free_cash_flow_cr": "FCF ₹Cr",
        "cash_from_operations_cr": "CFO ₹Cr",
    }
)

display_columns = [
    "Ticker",
    "Company",
    "Status",
    "NPM %",
    "OPM %",
    "ROE %",
    "D/E",
    "Interest Coverage",
    "Asset Turnover",
    "FCF ₹Cr",
    "CFO ₹Cr",
]

table = table[
    [col for col in display_columns if col in table.columns]
]


# Round numeric columns
numeric_columns = table.select_dtypes(
    include=["number"]
).columns

table[numeric_columns] = table[numeric_columns].round(2)


# ------------------------------------------------------------
# Highlight benchmark
# ------------------------------------------------------------
def highlight_benchmark(row):
    if row.get("Status") == "⭐ Benchmark":
        return [
            "font-weight: bold"
            for _ in row
        ]

    return [""] * len(row)


st.dataframe(
    table.style.apply(
        highlight_benchmark,
        axis=1,
    ),
    hide_index=True,
    use_container_width=True,
)


# ------------------------------------------------------------
# Data availability
# ------------------------------------------------------------
all_metric_columns = list(METRICS.values())

missing_values = peer_data[all_metric_columns].isna().sum()

missing_total = int(missing_values.sum())

if missing_total > 0:
    st.info(
        "Some peer companies have incomplete financial data. "
        "Unavailable values are shown as N/A."
    )


st.success(
    f"Peer comparison loaded successfully for {selected_group}."
)