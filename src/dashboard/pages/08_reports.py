import sys
from pathlib import Path

import pandas as pd
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
    page_title="Reports | Nifty 100 Analytics",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Annual Reports")
st.caption(
    "Access company information and annual-report resources for Nifty 100 companies."
)


# =========================================================
# DATABASE
# =========================================================

try:
    from src.dashboard.utils.db import get_companies
except Exception as e:
    st.error(f"Unable to load database utilities: {e}")
    st.stop()


# =========================================================
# LOAD COMPANIES
# =========================================================

try:
    companies = get_companies()
except Exception as e:
    st.error(f"Unable to load companies: {e}")
    st.stop()


if companies is None or companies.empty:
    st.warning("No company data is available.")
    st.stop()


companies = companies.copy()

companies.columns = [
    str(c).strip()
    for c in companies.columns
]


# =========================================================
# REQUIRED COMPANY ID
# =========================================================

if "company_id" not in companies.columns:
    st.error(
        "Company ID is missing from the companies dataset."
    )
    st.stop()


companies["company_id"] = (
    companies["company_id"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# COMPANY NAME
# =========================================================

if "company_name" not in companies.columns:
    companies["company_name"] = companies["company_id"]

companies["company_name"] = (
    companies["company_name"]
    .fillna(companies["company_id"])
    .astype(str)
    .str.strip()
)


# =========================================================
# COMPANY SEARCH
# =========================================================

search_text = st.text_input(
    "🔎 Search Company",
    placeholder="Type company name or ticker...",
)


filtered = companies.copy()

if search_text.strip():

    query = search_text.strip().lower()

    mask = (
        filtered["company_id"]
        .str.lower()
        .str.contains(query, na=False)
        |
        filtered["company_name"]
        .str.lower()
        .str.contains(query, na=False)
    )

    filtered = filtered[mask]


if filtered.empty:
    st.warning(
        "No company found. Try another company name or ticker."
    )
    st.stop()


# =========================================================
# COMPANY SELECTOR
# =========================================================

filtered["display"] = (
    filtered["company_id"]
    + " — "
    + filtered["company_name"]
)


selected_display = st.selectbox(
    "Select Company",
    filtered["display"].tolist(),
)


selected_row = filtered[
    filtered["display"] == selected_display
].iloc[0]


ticker = selected_row["company_id"]
company_name = selected_row["company_name"]


# =========================================================
# COMPANY HEADER
# =========================================================

st.markdown("---")

st.subheader(
    f"🏢 {company_name}"
)

st.caption(
    f"Ticker: **{ticker}**"
)


# =========================================================
# COMPANY INFORMATION
# =========================================================

c1, c2, c3 = st.columns(3)


if "sector" in selected_row.index:
    sector = selected_row["sector"]
elif "broad_sector" in selected_row.index:
    sector = selected_row["broad_sector"]
else:
    sector = "N/A"


if pd.isna(sector) or not str(sector).strip():
    sector = "N/A"


c1.metric(
    "Company",
    ticker,
)

c2.metric(
    "Sector",
    str(sector),
)

c3.metric(
    "Reports",
    "2019–2024",
)


# =========================================================
# COMPANY LINKS
# =========================================================

st.markdown("---")
st.subheader("🔗 Company Resources")


website = selected_row.get("website", None)
nse_profile = selected_row.get("nse_profile", None)
bse_profile = selected_row.get("bse_profile", None)


def valid_url(value):
    if value is None:
        return False

    if pd.isna(value):
        return False

    value = str(value).strip()

    return (
        value.startswith("http://")
        or value.startswith("https://")
    )


link_cols = st.columns(3)


with link_cols[0]:

    if valid_url(website):
        st.link_button(
            "🌐 Company Website",
            str(website),
            use_container_width=True,
        )
    else:
        st.button(
            "🌐 Website unavailable",
            disabled=True,
            use_container_width=True,
        )


with link_cols[1]:

    if valid_url(nse_profile):
        st.link_button(
            "📈 NSE Profile",
            str(nse_profile),
            use_container_width=True,
        )
    else:
        st.button(
            "📈 NSE Profile unavailable",
            disabled=True,
            use_container_width=True,
        )


with link_cols[2]:

    if valid_url(bse_profile):
        st.link_button(
            "🏦 BSE Profile",
            str(bse_profile),
            use_container_width=True,
        )
    else:
        st.button(
            "🏦 BSE Profile unavailable",
            disabled=True,
            use_container_width=True,
        )


# =========================================================
# ANNUAL REPORTS
# =========================================================

st.markdown("---")
st.subheader("📑 Annual Reports")


st.info(
    "Annual-report resources are organized by financial year. "
    "Use the BSE company profile when a direct PDF is not available."
)


# =========================================================
# REPORT YEARS
# =========================================================

report_years = list(range(2024, 2018, -1))


# =========================================================
# REPORT RESOURCE TABLE
# =========================================================

report_rows = []

for year in report_years:

    # BSE profile is the authoritative company resource
    # available in the current database.
    if valid_url(bse_profile):

        report_rows.append(
            {
                "Year": year,
                "Status": "BSE Profile Available",
                "BSE Resource": str(bse_profile),
            }
        )

    else:

        report_rows.append(
            {
                "Year": year,
                "Status": "Report unavailable",
                "BSE Resource": "",
            }
        )


report_df = pd.DataFrame(report_rows)


# =========================================================
# CLICKABLE YEAR LINKS
# =========================================================

for _, row in report_df.iterrows():

    year = int(row["Year"])

    col1, col2, col3 = st.columns(
        [1, 2, 2]
    )

    with col1:
        st.markdown(
            f"### FY {year}"
        )

    with col2:

        if row["BSE Resource"]:

            st.link_button(
                f"Open BSE Resource — {year}",
                row["BSE Resource"],
                use_container_width=True,
            )

        else:

            st.markdown(
                '<span style="color:red; font-weight:600;">'
                '🔴 Report unavailable'
                '</span>',
                unsafe_allow_html=True,
            )

    with col3:

        if row["BSE Resource"]:

            st.success(
                "BSE resource available"
            )

        else:

            st.error(
                "Report unavailable"
            )


# =========================================================
# REPORT AVAILABILITY SUMMARY
# =========================================================

st.markdown("---")
st.subheader("📊 Report Availability")


available_count = int(
    (report_df["Status"] == "BSE Profile Available").sum()
)

unavailable_count = int(
    (report_df["Status"] == "Report unavailable").sum()
)


k1, k2, k3 = st.columns(3)

k1.metric(
    "Years Listed",
    len(report_df),
)

k2.metric(
    "Resources Available",
    available_count,
)

k3.metric(
    "Unavailable",
    unavailable_count,
)


# =========================================================
# ABOUT COMPANY
# =========================================================

about = selected_row.get(
    "about_company",
    None,
)

if (
    about is not None
    and not pd.isna(about)
    and str(about).strip()
):

    st.markdown("---")
    st.subheader("ℹ️ About the Company")

    st.write(
        str(about).strip()
    )


# =========================================================
# COMPANY LOGO
# =========================================================

logo = selected_row.get(
    "company_logo",
    None,
)

if valid_url(logo):

    st.markdown("---")

    st.image(
        str(logo),
        width=120,
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    f"Reports and company resources for "
    f"{company_name} ({ticker})."
)