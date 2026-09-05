import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Capital Allocation | Nifty 100 Analytics",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Capital Allocation")
st.caption(
    "Analyze Nifty 100 companies by their capital allocation patterns."
)


# =========================================================
# LOAD DATA
# =========================================================

CSV_PATH = PROJECT_ROOT / "output" / "capital_allocation.csv"

if not CSV_PATH.exists():
    st.error(f"Capital allocation file not found: {CSV_PATH}")
    st.stop()

try:
    df = pd.read_csv(CSV_PATH)
except Exception as e:
    st.error(f"Unable to read capital allocation data: {e}")
    st.stop()


if df.empty:
    st.warning("No capital allocation data available.")
    st.stop()


df.columns = [str(c).strip() for c in df.columns]


# =========================================================
# VERIFY REQUIRED COLUMNS
# =========================================================

required_columns = [
    "company_id",
    "year",
    "cfo_sign",
    "cfi_sign",
    "cff_sign",
    "pattern_label",
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    st.error(
        f"Required columns are missing: {missing}\n\n"
        f"Available columns: {df.columns.tolist()}"
    )
    st.stop()


# =========================================================
# CLEAN DATA
# =========================================================

df["company_id"] = (
    df["company_id"]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)

df["pattern_label"] = (
    df["pattern_label"]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)

df["year"] = pd.to_numeric(
    df["year"],
    errors="coerce",
)


# =========================================================
# LATEST YEAR FOR EACH COMPANY
# =========================================================

latest_df = (
    df.sort_values(
        ["company_id", "year"],
        ascending=[True, False],
        na_position="last",
    )
    .drop_duplicates(
        subset=["company_id"],
        keep="first",
    )
    .copy()
)


# =========================================================
# KPI SUMMARY
# =========================================================

total_companies = latest_df["company_id"].nunique()

total_patterns = latest_df["pattern_label"].nunique()

pattern_counts = (
    latest_df["pattern_label"]
    .value_counts()
    .reset_index()
)

pattern_counts.columns = [
    "Pattern",
    "Companies",
]

if not pattern_counts.empty:
    largest_pattern = pattern_counts.iloc[0]["Pattern"]
    largest_count = int(pattern_counts.iloc[0]["Companies"])
else:
    largest_pattern = "N/A"
    largest_count = 0


# =========================================================
# KPI CARDS
# =========================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Companies",
    f"{total_companies:,}",
)

c2.metric(
    "Allocation Patterns",
    f"{total_patterns:,}",
)

c3.metric(
    "Largest Pattern",
    largest_pattern,
)

c4.metric(
    "Companies in Largest Pattern",
    f"{largest_count:,}",
)


# =========================================================
# TREEMAP
# =========================================================

st.markdown("---")
st.subheader("🗺️ Capital Allocation Pattern Distribution")

if not pattern_counts.empty:

    fig_tree = px.treemap(
        pattern_counts,
        path=["Pattern"],
        values="Companies",
        title="Nifty 100 Capital Allocation Patterns",
    )

    fig_tree.update_layout(
        height=550,
        margin=dict(
            l=10,
            r=10,
            t=60,
            b=10,
        ),
    )

    st.plotly_chart(
        fig_tree,
        use_container_width=True,
    )

else:
    st.info("No pattern data available.")


# =========================================================
# PATTERN DROPDOWN
# =========================================================

st.markdown("---")
st.subheader("🔎 Explore Companies by Pattern")

patterns = sorted(
    latest_df["pattern_label"]
    .dropna()
    .unique()
    .tolist()
)

if not patterns:
    st.warning("No capital allocation patterns available.")
    st.stop()

selected_pattern = st.selectbox(
    "Select Capital Allocation Pattern",
    patterns,
)


# =========================================================
# SELECTED COMPANIES
# =========================================================

selected_df = latest_df[
    latest_df["pattern_label"] == selected_pattern
].copy()


st.markdown(
    f"### {selected_pattern}"
)

st.info(
    f"{len(selected_df)} companies belong to the "
    f"**{selected_pattern}** pattern."
)


# =========================================================
# COMPANY TABLE
# =========================================================

display_df = selected_df[
    [
        "company_id",
        "year",
        "cfo_sign",
        "cfi_sign",
        "cff_sign",
        "pattern_label",
    ]
].copy()


display_df = display_df.rename(
    columns={
        "company_id": "Company",
        "year": "Year",
        "cfo_sign": "CFO Sign",
        "cfi_sign": "CFI Sign",
        "cff_sign": "CFF Sign",
        "pattern_label": "Pattern",
    }
)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# HISTORICAL DISTRIBUTION
# =========================================================

st.markdown("---")
st.subheader("📅 Historical Capital Allocation Patterns")

historical = (
    df.groupby(
        ["year", "pattern_label"],
        dropna=False,
    )
    .size()
    .reset_index(name="Companies")
)

historical = historical.dropna(
    subset=["year"]
)

if not historical.empty:

    historical["year"] = historical["year"].astype(int)

    fig_history = px.bar(
        historical,
        x="year",
        y="Companies",
        color="pattern_label",
        barmode="stack",
        title="Capital Allocation Patterns Over Time",
    )

    fig_history.update_layout(
        height=550,
        xaxis_title="Year",
        yaxis_title="Number of Companies",
        legend_title="Pattern",
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
    )

    st.plotly_chart(
        fig_history,
        use_container_width=True,
    )

else:
    st.info("Historical data is not available.")


# =========================================================
# SIGN ANALYSIS
# =========================================================

st.markdown("---")
st.subheader("📊 Cash Flow Sign Analysis")

sign_summary = pd.DataFrame({
    "Cash Flow": [
        "CFO",
        "CFI",
        "CFF",
    ],
    "Positive": [
        (latest_df["cfo_sign"].astype(str).str.upper() == "POSITIVE").sum(),
        (latest_df["cfi_sign"].astype(str).str.upper() == "POSITIVE").sum(),
        (latest_df["cff_sign"].astype(str).str.upper() == "POSITIVE").sum(),
    ],
    "Negative": [
        (latest_df["cfo_sign"].astype(str).str.upper() == "NEGATIVE").sum(),
        (latest_df["cfi_sign"].astype(str).str.upper() == "NEGATIVE").sum(),
        (latest_df["cff_sign"].astype(str).str.upper() == "NEGATIVE").sum(),
    ],
})


fig_sign = px.bar(
    sign_summary,
    x="Cash Flow",
    y=["Positive", "Negative"],
    barmode="group",
    title="Latest Capital Allocation Cash Flow Signals",
)

fig_sign.update_layout(
    height=450,
    yaxis_title="Companies",
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
)

st.plotly_chart(
    fig_sign,
    use_container_width=True,
)


# =========================================================
# RAW DATA
# =========================================================

with st.expander("View Raw Capital Allocation Data"):
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# FOOTER
# =========================================================

st.caption(
    f"Capital allocation analysis covering "
    f"{total_companies} companies and "
    f"{total_patterns} allocation patterns."
)