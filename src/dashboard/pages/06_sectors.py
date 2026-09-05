import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# Project path
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_sector_data


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sectors | Nifty 100 Analytics",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Sector Analysis")
st.caption("Compare Nifty 100 companies across sectors using financial and market metrics.")

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
try:
    df = get_sector_data()
except Exception as e:
    st.error(f"Unable to load sector data: {e}")
    st.stop()

if df is None or df.empty:
    st.warning("No sector data available.")
    st.stop()

df = df.copy()

# ---------------------------------------------------------
# Normalize column names / numeric fields
# ---------------------------------------------------------
numeric_columns = [
    "revenue",
    "sales",
    "net_profit",
    "return_on_equity_pct",
    "roe_percentage",
    "market_cap_crore",
    "index_weight_pct",
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Revenue may come from either revenue or sales
if "revenue" not in df.columns:
    if "sales" in df.columns:
        df["revenue"] = df["sales"]
    else:
        df["revenue"] = pd.NA

# ROE may come from either ratio or companies table
if "return_on_equity_pct" not in df.columns:
    if "roe_percentage" in df.columns:
        df["return_on_equity_pct"] = df["roe_percentage"]
    else:
        df["return_on_equity_pct"] = pd.NA

# ---------------------------------------------------------
# Required display columns
# ---------------------------------------------------------
sector_col = "broad_sector" if "broad_sector" in df.columns else None
subsector_col = "sub_sector" if "sub_sector" in df.columns else None
company_id_col = "company_id" if "company_id" in df.columns else None
company_name_col = "company_name" if "company_name" in df.columns else None

if sector_col is None:
    st.error("Sector information is not available in the database.")
    st.stop()

# Clean sector names
df[sector_col] = df[sector_col].fillna("Unknown").astype(str)

sectors = sorted(
    [x for x in df[sector_col].unique().tolist() if x.strip()]
)

# ---------------------------------------------------------
# Sector selector
# ---------------------------------------------------------
selected_sector = st.selectbox(
    "Select Sector",
    sectors,
    index=0,
)

sector_df = df[df[sector_col] == selected_sector].copy()

if sector_df.empty:
    st.warning("No companies found for the selected sector.")
    st.stop()

# ---------------------------------------------------------
# KPIs
# ---------------------------------------------------------
company_count = len(sector_df)

median_revenue = sector_df["revenue"].median()

median_roe = sector_df["return_on_equity_pct"].median()

median_market_cap = (
    sector_df["market_cap_crore"].median()
    if "market_cap_crore" in sector_df.columns
    else float("nan")
)

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Companies",
    f"{company_count:,}",
)

k2.metric(
    "Median Revenue",
    f"₹{median_revenue:,.0f} Cr"
    if pd.notna(median_revenue)
    else "N/A",
)

k3.metric(
    "Median ROE",
    f"{median_roe:.2f}%"
    if pd.notna(median_roe)
    else "N/A",
)

k4.metric(
    "Median Market Cap",
    f"₹{median_market_cap:,.0f} Cr"
    if pd.notna(median_market_cap)
    else "N/A",
)

st.markdown("---")

# ---------------------------------------------------------
# Bubble chart
# X = Revenue
# Y = ROE
# Size = Market Cap
# Color = Sub-sector
# ---------------------------------------------------------
st.subheader("📊 Revenue vs ROE")

bubble_df = sector_df.copy()

bubble_df = bubble_df.dropna(
    subset=["revenue", "return_on_equity_pct"]
)

if "market_cap_crore" not in bubble_df.columns:
    bubble_df["market_cap_crore"] = 1.0

bubble_df["market_cap_crore"] = pd.to_numeric(
    bubble_df["market_cap_crore"],
    errors="coerce",
)

bubble_df["market_cap_crore"] = bubble_df["market_cap_crore"].fillna(1.0)

if subsector_col:
    bubble_df[subsector_col] = (
        bubble_df[subsector_col]
        .fillna("Unknown")
        .astype(str)
    )
else:
    bubble_df["display_subsector"] = "Unknown"
    subsector_col = "display_subsector"

if company_name_col:
    bubble_df["display_name"] = (
        bubble_df[company_name_col]
        .fillna(bubble_df[company_id_col] if company_id_col else "Company")
        .astype(str)
    )
elif company_id_col:
    bubble_df["display_name"] = bubble_df[company_id_col].astype(str)
else:
    bubble_df["display_name"] = "Company"

if not bubble_df.empty:
    fig = px.scatter(
        bubble_df,
        x="revenue",
        y="return_on_equity_pct",
        size="market_cap_crore",
        color=subsector_col,
        hover_name="display_name",
        hover_data={
            "revenue": ":,.2f",
            "return_on_equity_pct": ":.2f",
            "market_cap_crore": ":,.2f",
            subsector_col: True,
        },
        labels={
            "revenue": "Revenue (₹ Cr)",
            "return_on_equity_pct": "ROE (%)",
            "market_cap_crore": "Market Cap (₹ Cr)",
            subsector_col: "Sub-Sector",
        },
        title=f"{selected_sector} — Revenue vs ROE",
    )

    fig.update_layout(
        height=550,
        legend_title_text="Sub-Sector",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    fig.update_xaxes(
        tickformat=",.0f",
        zeroline=False,
    )

    fig.update_yaxes(
        ticksuffix="%",
        zeroline=True,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )
else:
    st.info("Insufficient Revenue/ROE data for the bubble chart.")

# ---------------------------------------------------------
# Median KPI comparison
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📈 Median KPI Comparison")

kpi_data = {
    "Metric": [],
    "Median": [],
}

if "revenue" in sector_df.columns:
    kpi_data["Metric"].append("Revenue (₹ Cr)")
    kpi_data["Median"].append(
        sector_df["revenue"].median()
    )

if "net_profit" in sector_df.columns:
    kpi_data["Metric"].append("Net Profit (₹ Cr)")
    kpi_data["Median"].append(
        sector_df["net_profit"].median()
    )

if "return_on_equity_pct" in sector_df.columns:
    kpi_data["Metric"].append("ROE (%)")
    kpi_data["Median"].append(
        sector_df["return_on_equity_pct"].median()
    )

if "market_cap_crore" in sector_df.columns:
    kpi_data["Metric"].append("Market Cap (₹ Cr)")
    kpi_data["Median"].append(
        sector_df["market_cap_crore"].median()
    )

kpi_df = pd.DataFrame(kpi_data)

if not kpi_df.empty:
    bar_fig = px.bar(
        kpi_df,
        x="Metric",
        y="Median",
        text="Median",
        title=f"{selected_sector} — Median KPIs",
    )

    bar_fig.update_traces(
        texttemplate="%{text:,.2f}",
        textposition="outside",
    )

    bar_fig.update_layout(
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        yaxis_title="Median Value",
        xaxis_title="",
    )

    st.plotly_chart(
        bar_fig,
        use_container_width=True,
    )

# ---------------------------------------------------------
# Company table
# ---------------------------------------------------------
st.markdown("---")
st.subheader(f"🏢 Companies in {selected_sector}")

display_columns = []

if company_id_col:
    display_columns.append(company_id_col)

if company_name_col:
    display_columns.append(company_name_col)

if subsector_col and subsector_col in sector_df.columns:
    display_columns.append(subsector_col)

for col in [
    "revenue",
    "net_profit",
    "return_on_equity_pct",
    "market_cap_crore",
    "index_weight_pct",
]:
    if col in sector_df.columns and col not in display_columns:
        display_columns.append(col)

table_df = sector_df[display_columns].copy()

rename_map = {
    "company_id": "Company ID",
    "company_name": "Company",
    "sub_sector": "Sub-Sector",
    "display_subsector": "Sub-Sector",
    "revenue": "Revenue (₹ Cr)",
    "net_profit": "Net Profit (₹ Cr)",
    "return_on_equity_pct": "ROE (%)",
    "market_cap_crore": "Market Cap (₹ Cr)",
    "index_weight_pct": "Index Weight (%)",
}

table_df = table_df.rename(
    columns={
        k: v
        for k, v in rename_map.items()
        if k in table_df.columns
    }
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# Missing data warning
# ---------------------------------------------------------
missing_summary = sector_df.isna().sum()
missing_summary = missing_summary[missing_summary > 0]

if not missing_summary.empty:
    st.warning(
        "Some financial fields contain missing values. "
        "Missing values are displayed as N/A where applicable."
    )

st.caption(
    f"Showing {len(sector_df)} companies in {selected_sector}."
)