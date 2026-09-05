import streamlit as st


st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.title("Nifty 100 Analytics")
st.caption("Nifty 100 Financial Analytics Dashboard")

st.sidebar.title("Nifty 100 Analytics")
st.sidebar.markdown("---")

st.sidebar.success("Dashboard online")

st.markdown(
    """
    ## Welcome

    This dashboard provides financial and market analytics
    for the Nifty 100 universe.

    ### Dashboard Modules

    **🏠 Home**
    - Market overview
    - Key financial KPIs
    - Sector distribution
    - Top quality companies

    **👤 Profile**
    - Company fundamentals
    - Historical financial performance
    - ROE / ROCE trends
    - Pros and cons

    **🔎 Screener**
    - Financial filters
    - Preset strategies
    - Composite quality score
    - CSV export

    **👥 Peers**
    - Peer-group comparison
    - Radar charts
    - Peer benchmarks

    **📈 Trends**
    - Historical company trends
    - Revenue, profit and ratio analysis

    **🏢 Sectors**
    - Sector performance
    - Company-level bubble analysis

    **💰 Capital Allocation**
    - Capital allocation patterns
    - Company grouping

    **📑 Reports**
    - Annual reports
    - BSE document links
    """
)

st.info(
    "Day 22 dashboard scaffold is active. "
    "Detailed functionality will be implemented in Days 23–26."
)

st.markdown("---")
st.write("**Database:** `db/nifty100.db`")
st.write("**Companies available:** 92")