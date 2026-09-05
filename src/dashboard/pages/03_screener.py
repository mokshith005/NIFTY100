import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# Project path
# -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_ratios


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Stock Screener | Nifty 100 Analytics",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Stock Screener")
st.caption("Filter Nifty 100 companies using fundamental financial metrics.")


# -------------------------------------------------------------------
# Load companies
# -------------------------------------------------------------------
companies = get_companies()

if companies.empty:
    st.error("Company data is unavailable.")
    st.stop()


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def latest_value(df, candidates):
    """Return the latest available value from candidate column names."""
    if df.empty:
        return np.nan

    for col in candidates:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty:
                return series.iloc[-1]

    return np.nan


def calculate_cagr(df, candidates, years=5):
    """Calculate CAGR from a financial-history dataframe."""
    if df.empty:
        return np.nan

    column = None
    for col in candidates:
        if col in df.columns:
            column = col
            break

    if column is None or "year" not in df.columns:
        return np.nan

    temp = df[["year", column]].copy()
    temp[column] = pd.to_numeric(temp[column], errors="coerce")
    temp["year"] = pd.to_numeric(temp["year"], errors="coerce")
    temp = temp.dropna().sort_values("year")

    if len(temp) < 2:
        return np.nan

    latest = temp.iloc[-1]
    target_year = latest["year"] - years

    older = temp[temp["year"] <= target_year]

    if older.empty:
        older = temp.iloc[:1]

    old = older.iloc[-1]

    start = old[column]
    end = latest[column]

    if pd.isna(start) or pd.isna(end) or start <= 0 or end <= 0:
        return np.nan

    actual_years = latest["year"] - old["year"]

    if actual_years <= 0:
        return np.nan

    return ((end / start) ** (1 / actual_years) - 1) * 100


@st.cache_data(ttl=600)
def build_screener_data(company_df):
    """Build one latest-fundamentals row for every company."""

    rows = []

    for _, company in company_df.iterrows():
        ticker = company["company_id"]

        try:
            ratios = get_ratios(ticker)

            if ratios.empty:
                rows.append({
                    "company_id": ticker,
                    "company_name": company["company_name"],
                    "sector": company.get("sector", "N/A"),
                    "roe": np.nan,
                    "de": np.nan,
                    "fcf": np.nan,
                    "revenue_cagr": np.nan,
                    "pat_cagr": np.nan,
                    "opm": np.nan,
                    "pe": np.nan,
                    "pb": np.nan,
                    "dividend_yield": np.nan,
                    "icr": np.nan,
                })
                continue

            ratios = ratios.copy()

            if "year" in ratios.columns:
                ratios["year"] = pd.to_numeric(
                    ratios["year"], errors="coerce"
                )
                ratios = ratios.sort_values("year")

            latest = ratios.iloc[-1]

            roe = latest_value(
                ratios,
                [
                    "return_on_equity_pct",
                    "roe_percentage",
                    "roe_pct",
                    "roe",
                ],
            )

            de = latest_value(
                ratios,
                [
                    "debt_to_equity",
                    "de_ratio",
                    "de",
                ],
            )

            fcf = latest_value(
                ratios,
                [
                    "free_cash_flow_cr",
                    "free_cash_flow",
                    "fcf_cr",
                    "fcf",
                ],
            )

            opm = latest_value(
                ratios,
                [
                    "operating_profit_margin_pct",
                    "operating_margin_pct",
                    "opm_pct",
                    "opm",
                ],
            )

            pe = latest_value(
                ratios,
                [
                    "price_to_earnings",
                    "pe_ratio",
                    "pe",
                    "p_e",
                ],
            )

            pb = latest_value(
                ratios,
                [
                    "price_to_book",
                    "pb_ratio",
                    "pb",
                    "p_b",
                ],
            )

            dividend_yield = latest_value(
                ratios,
                [
                    "dividend_yield_pct",
                    "dividend_yield",
                    "yield_pct",
                ],
            )

            icr = latest_value(
                ratios,
                [
                    "interest_coverage",
                    "interest_coverage_ratio",
                    "icr",
                ],
            )

            # -------------------------------------------------------
            # CAGR values
            # -------------------------------------------------------
            revenue_cagr = np.nan
            pat_cagr = np.nan

            try:
                pl = None

                # Import lazily so the page remains robust.
                from src.dashboard.utils.db import get_pl

                pl = get_pl(ticker)

                revenue_cagr = calculate_cagr(
                    pl,
                    [
                        "revenue_cr",
                        "revenue",
                        "sales_cr",
                        "sales",
                        "total_revenue",
                    ],
                    5,
                )

                pat_cagr = calculate_cagr(
                    pl,
                    [
                        "net_profit_cr",
                        "net_profit",
                        "profit_after_tax",
                        "pat_cr",
                        "pat",
                    ],
                    5,
                )

            except Exception:
                pass

            rows.append({
                "company_id": ticker,
                "company_name": company["company_name"],
                "sector": company.get("sector", "N/A"),
                "roe": roe,
                "de": de,
                "fcf": fcf,
                "revenue_cagr": revenue_cagr,
                "pat_cagr": pat_cagr,
                "opm": opm,
                "pe": pe,
                "pb": pb,
                "dividend_yield": dividend_yield,
                "icr": icr,
            })

        except Exception:
            rows.append({
                "company_id": ticker,
                "company_name": company["company_name"],
                "sector": company.get("sector", "N/A"),
                "roe": np.nan,
                "de": np.nan,
                "fcf": np.nan,
                "revenue_cagr": np.nan,
                "pat_cagr": np.nan,
                "opm": np.nan,
                "pe": np.nan,
                "pb": np.nan,
                "dividend_yield": np.nan,
                "icr": np.nan,
            })

    return pd.DataFrame(rows)


# -------------------------------------------------------------------
# Build dataset
# -------------------------------------------------------------------
with st.spinner("Loading Nifty 100 fundamentals..."):
    data = build_screener_data(companies)


# -------------------------------------------------------------------
# Composite score
# -------------------------------------------------------------------
def calculate_score(row):
    score = 0
    checks = 0

    metrics = [
        ("roe", lambda x: x >= 15),
        ("de", lambda x: x <= 1),
        ("fcf", lambda x: x > 0),
        ("revenue_cagr", lambda x: x >= 10),
        ("pat_cagr", lambda x: x >= 10),
        ("opm", lambda x: x >= 15),
        ("pe", lambda x: x <= 30),
        ("pb", lambda x: x <= 5),
        ("dividend_yield", lambda x: x >= 1),
        ("icr", lambda x: x >= 3),
    ]

    for metric, condition in metrics:
        value = row.get(metric)

        if pd.notna(value):
            checks += 1
            if condition(value):
                score += 1

    if checks == 0:
        return np.nan

    return round((score / checks) * 100, 2)


data["composite_score"] = data.apply(calculate_score, axis=1)


# -------------------------------------------------------------------
# Presets
# -------------------------------------------------------------------
st.subheader("⚡ Screening Presets")

if "preset" not in st.session_state:
    st.session_state.preset = "Custom"

preset_cols = st.columns(6)

presets = {
    "Quality": {
        "roe": 20,
        "de": 1.0,
        "fcf": 0,
        "revenue_cagr": 5,
        "pat_cagr": 5,
        "opm": 15,
        "pe": 50,
        "pb": 8,
        "dividend_yield": 0,
        "icr": 3,
    },
    "Value": {
        "roe": 10,
        "de": 2,
        "fcf": 0,
        "revenue_cagr": 0,
        "pat_cagr": 0,
        "opm": 0,
        "pe": 20,
        "pb": 3,
        "dividend_yield": 1,
        "icr": 1,
    },
    "Growth": {
        "roe": 15,
        "de": 1.5,
        "fcf": 0,
        "revenue_cagr": 15,
        "pat_cagr": 15,
        "opm": 10,
        "pe": 60,
        "pb": 10,
        "dividend_yield": 0,
        "icr": 2,
    },
    "Dividend": {
        "roe": 10,
        "de": 2,
        "fcf": 0,
        "revenue_cagr": 0,
        "pat_cagr": 0,
        "opm": 0,
        "pe": 40,
        "pb": 8,
        "dividend_yield": 3,
        "icr": 2,
    },
    "Debt-Free": {
        "roe": 10,
        "de": 0.1,
        "fcf": 0,
        "revenue_cagr": 0,
        "pat_cagr": 0,
        "opm": 0,
        "pe": 50,
        "pb": 10,
        "dividend_yield": 0,
        "icr": 5,
    },
    "Turnaround": {
        "roe": 5,
        "de": 2,
        "fcf": 0,
        "revenue_cagr": 5,
        "pat_cagr": 5,
        "opm": 5,
        "pe": 50,
        "pb": 8,
        "dividend_yield": 0,
        "icr": 1,
    },
}


for col, name in zip(preset_cols, presets):
    if col.button(name, use_container_width=True):
        for key, value in presets[name].items():
            st.session_state[f"screen_{key}"] = value
        st.session_state.preset = name
        st.rerun()


st.caption(f"Active preset: **{st.session_state.preset}**")


# -------------------------------------------------------------------
# Sliders
# -------------------------------------------------------------------
st.subheader("🎚️ Fundamental Filters")

c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)
c7, c8, c9 = st.columns(3)
c10, _, _ = st.columns(3)


def slider_state(key, label, min_value, max_value, default, step):
    return st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=st.session_state.get(f"screen_{key}", default),
        step=step,
        key=f"screen_{key}",
    )


roe_min = c1.slider(
    "ROE minimum (%)",
    0.0,
    100.0,
    float(st.session_state.get("screen_roe", 0.0)),
    1.0,
    key="screen_roe",
)

de_max = c2.slider(
    "Debt / Equity maximum",
    0.0,
    10.0,
    float(st.session_state.get("screen_de", 10.0)),
    0.1,
    key="screen_de",
)

fcf_min = c3.slider(
    "FCF minimum (₹ Cr)",
    -5000.0,
    50000.0,
    float(st.session_state.get("screen_fcf", -5000.0)),
    100.0,
    key="screen_fcf",
)

revenue_cagr_min = c4.slider(
    "Revenue CAGR minimum (%)",
    -50.0,
    100.0,
    float(st.session_state.get("screen_revenue_cagr", -50.0)),
    1.0,
    key="screen_revenue_cagr",
)

pat_cagr_min = c5.slider(
    "PAT CAGR minimum (%)",
    -50.0,
    100.0,
    float(st.session_state.get("screen_pat_cagr", -50.0)),
    1.0,
    key="screen_pat_cagr",
)

opm_min = c6.slider(
    "OPM minimum (%)",
    -50.0,
    100.0,
    float(st.session_state.get("screen_opm", -50.0)),
    1.0,
    key="screen_opm",
)

pe_max = c7.slider(
    "P/E maximum",
    0.0,
    150.0,
    float(st.session_state.get("screen_pe", 150.0)),
    1.0,
    key="screen_pe",
)

pb_max = c8.slider(
    "P/B maximum",
    0.0,
    30.0,
    float(st.session_state.get("screen_pb", 30.0)),
    0.5,
    key="screen_pb",
)

dividend_yield_min = c9.slider(
    "Dividend Yield minimum (%)",
    0.0,
    20.0,
    float(st.session_state.get("screen_dividend_yield", 0.0)),
    0.5,
    key="screen_dividend_yield",
)

icr_min = c10.slider(
    "Interest Coverage minimum",
    0.0,
    30.0,
    float(st.session_state.get("screen_icr", 0.0)),
    0.5,
    key="screen_icr",
)


# -------------------------------------------------------------------
# Apply filters
# -------------------------------------------------------------------
filtered = data.copy()

filters = [
    ("roe", roe_min, ">="),
    ("de", de_max, "<="),
    ("fcf", fcf_min, ">="),
    ("revenue_cagr", revenue_cagr_min, ">="),
    ("pat_cagr", pat_cagr_min, ">="),
    ("opm", opm_min, ">="),
    ("pe", pe_max, "<="),
    ("pb", pb_max, "<="),
    ("dividend_yield", dividend_yield_min, ">="),
    ("icr", icr_min, ">="),
]

for column, threshold, operator in filters:
    if operator == ">=":
        filtered = filtered[
            filtered[column].isna() | (filtered[column] >= threshold)
        ]
    else:
        filtered = filtered[
            filtered[column].isna() | (filtered[column] <= threshold)
        ]


# -------------------------------------------------------------------
# Result summary
# -------------------------------------------------------------------
st.divider()

m1, m2, m3 = st.columns(3)

m1.metric("Companies Matching", len(filtered))
m2.metric("Companies Analysed", len(data))
m3.metric(
    "Average Composite Score",
    "N/A"
    if filtered["composite_score"].dropna().empty
    else f"{filtered['composite_score'].mean():.1f}/100",
)


# -------------------------------------------------------------------
# Results table
# -------------------------------------------------------------------
st.subheader("📋 Screener Results")

display = filtered.copy()

display = display.rename(
    columns={
        "company_id": "Ticker",
        "company_name": "Company",
        "sector": "Sector",
        "composite_score": "Composite Score",
        "roe": "ROE %",
        "de": "D/E",
        "fcf": "FCF ₹Cr",
        "revenue_cagr": "Revenue CAGR %",
        "pat_cagr": "PAT CAGR %",
        "opm": "OPM %",
        "pe": "P/E",
        "pb": "P/B",
        "dividend_yield": "Dividend Yield %",
        "icr": "Interest Coverage",
    }
)

display_columns = [
    "Ticker",
    "Company",
    "Sector",
    "Composite Score",
    "ROE %",
    "D/E",
    "FCF ₹Cr",
    "Revenue CAGR %",
    "PAT CAGR %",
    "OPM %",
    "P/E",
    "P/B",
    "Dividend Yield %",
    "Interest Coverage",
]

display = display[
    [c for c in display_columns if c in display.columns]
]

if "Composite Score" in display.columns:
    display = display.sort_values(
        "Composite Score",
        ascending=False,
        na_position="last",
    )

st.dataframe(
    display,
    hide_index=True,
    use_container_width=True,
)


# -------------------------------------------------------------------
# CSV download
# -------------------------------------------------------------------
csv_data = display.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Screener Results CSV",
    data=csv_data,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
    use_container_width=False,
)


# -------------------------------------------------------------------
# Data availability note
# -------------------------------------------------------------------
missing_count = int(
    filtered[
        [
            "roe",
            "de",
            "fcf",
            "revenue_cagr",
            "pat_cagr",
            "opm",
            "pe",
            "pb",
            "dividend_yield",
            "icr",
        ]
    ].isna().all(axis=1).sum()
)

if missing_count:
    st.info(
        f"{missing_count} companies have limited fundamental data. "
        "Missing values are displayed as N/A and do not cause the screener to crash."
    )

st.success("Screener loaded successfully.")