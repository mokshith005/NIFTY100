import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_companies, get_ratios, get_pl, get_proscons


st.set_page_config(page_title="Company Profile | Nifty 100 Analytics", layout="wide")

st.title("👤 Company Profile")
st.caption("Detailed financial profile and historical performance of Nifty 100 companies")

companies = get_companies()

if companies.empty:
    st.error("Company data unavailable.")
    st.stop()

companies = companies.copy()
companies["display"] = companies["company_id"] + " — " + companies["company_name"]

selected = st.selectbox(
    "Search Company / Ticker",
    companies["display"].tolist(),
    index=0,
)

company_id = selected.split(" — ")[0]
company = companies[companies["company_id"] == company_id].iloc[0]

ratios = get_ratios(company_id)
pl = get_pl(company_id)

# ---------- COMPANY HEADER ----------
st.markdown("---")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.subheader(str(company["company_name"]))
    st.write(f"**Ticker:** {company_id}")
    st.write(f"**Sector:** {company.get('sector', 'N/A')}")
    st.write(f"**Sub-sector:** {company.get('sub_sector', 'N/A')}")

with c2:
    website = company.get("website")
    if pd.notna(website) and str(website).strip():
        st.link_button("🌐 Company Website", str(website))

with c3:
    nse = company.get("nse_profile")
    if pd.notna(nse) and str(nse).strip():
        st.link_button("📈 NSE Profile", str(nse))

about = company.get("about_company")
if pd.notna(about) and str(about).strip():
    st.info(str(about))

# ---------- LATEST DATA ----------
if not ratios.empty:
    ratios = ratios.sort_values("year")
    latest = ratios.iloc[-1]

    def val(col):
        x = latest.get(col)
        return x if pd.notna(x) else None

    st.markdown("---")
    st.subheader("📊 Key Financial KPIs")

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        x = val("return_on_equity_pct")
        st.metric("ROE", f"{x:.2f}%" if x is not None else "N/A")

    with k2:
        x = val("net_profit_margin_pct")
        st.metric("NPM", f"{x:.2f}%" if x is not None else "N/A")

    with k3:
        x = val("debt_to_equity")
        st.metric("D/E", f"{x:.2f}" if x is not None else "N/A")

    with k4:
        x = val("interest_coverage")
        st.metric("Interest Coverage", f"{x:.2f}" if x is not None else "N/A")

    with k5:
        x = val("free_cash_flow_cr")
        st.metric("Latest FCF", f"₹{x:,.2f} Cr" if x is not None else "N/A")

    with k6:
        x = val("earnings_per_share")
        st.metric("EPS", f"₹{x:,.2f}" if x is not None else "N/A")

    # Revenue CAGR
    revenue_cagr = None
    revenue_col = next(
        (c for c in pl.columns if "revenue" in c.lower()),
        None
    )

    if revenue_col and len(pl) >= 6:
        temp = pl.sort_values("year")
        first = pd.to_numeric(temp.iloc[0][revenue_col], errors="coerce")
        last = pd.to_numeric(temp.iloc[-1][revenue_col], errors="coerce")

        if pd.notna(first) and pd.notna(last) and first > 0:
            years = max(1, int(temp.iloc[-1]["year"]) - int(temp.iloc[0]["year"]))
            revenue_cagr = ((last / first) ** (1 / years) - 1) * 100

    st.markdown("---")
    st.subheader("📈 Historical Financial Performance")

    if not pl.empty:
        pl = pl.copy()

        numeric_cols = [
            c for c in pl.columns
            if c != "year"
            and pd.api.types.is_numeric_dtype(pl[c])
        ]

        revenue_col = next(
            (c for c in numeric_cols if "revenue" in c.lower()),
            None
        )

        profit_col = next(
            (
                c for c in numeric_cols
                if "net_profit" in c.lower()
                or "net profit" in c.lower()
                or c.lower() == "profit"
            ),
            None
        )

        if revenue_col or profit_col:
            chart = go.Figure()

            if revenue_col:
                chart.add_trace(
                    go.Bar(
                        x=pl["year"],
                        y=pd.to_numeric(pl[revenue_col], errors="coerce"),
                        name="Revenue",
                    )
                )

            if profit_col:
                chart.add_trace(
                    go.Bar(
                        x=pl["year"],
                        y=pd.to_numeric(pl[profit_col], errors="coerce"),
                        name="Net Profit",
                    )
                )

            chart.update_layout(
                barmode="group",
                xaxis_title="Year",
                yaxis_title="₹ Crore",
                height=450,
            )

            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("Revenue / Net Profit historical data unavailable.")

    # ---------- ROE / ROCE ----------
    st.subheader("📉 ROE / ROCE Trend")

    trend = ratios.copy()

    fig = go.Figure()

    if "return_on_equity_pct" in trend.columns:
        fig.add_trace(
            go.Scatter(
                x=trend["year"],
                y=trend["return_on_equity_pct"],
                mode="lines+markers",
                name="ROE",
            )
        )

    roce_col = next(
        (
            c for c in trend.columns
            if "roce" in c.lower()
        ),
        None,
    )

    if roce_col:
        fig.add_trace(
            go.Scatter(
                x=trend["year"],
                y=trend[roce_col],
                mode="lines+markers",
                name="ROCE",
                yaxis="y2",
            )
        )
        fig.update_layout(
            yaxis2=dict(
                title="ROCE %",
                overlaying="y",
                side="right",
            )
        )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="ROE %",
        height=420,
    )

    if fig.data:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ROE / ROCE trend unavailable.")

    # ---------- CAGR ----------
    st.subheader("🚀 Growth Summary")

    g1, g2, g3 = st.columns(3)

    with g1:
        st.metric(
            "Revenue CAGR",
            f"{revenue_cagr:.2f}%" if revenue_cagr is not None else "N/A",
        )

    with g2:
        st.metric(
            "Latest Year",
            str(int(latest["year"])) if pd.notna(latest.get("year")) else "N/A",
        )

    with g3:
        st.metric(
            "Book Value",
            f"₹{company['book_value']:,.2f}"
            if pd.notna(company.get("book_value"))
            else "N/A",
        )

else:
    st.warning("Financial ratio data unavailable for this company.")

# ---------- PROS / CONS ----------
st.markdown("---")
st.subheader("⚖️ Pros and Cons")

try:
    pc = get_proscons(company_id)

    if pc is not None and not pc.empty:
        text_cols = [
            c for c in pc.columns
            if pc[c].dtype == "object"
        ]

        if text_cols:
            values = []
            for col in text_cols:
                for item in pc[col].dropna().astype(str):
                    if item.strip():
                        values.append((col, item.strip()))

            left, right = st.columns(2)

            with left:
                st.markdown("### ✅ Pros")
                pros = [
                    x for col, x in values
                    if "pro" in col.lower()
                ]
                if pros:
                    for x in pros[:10]:
                        st.success(x)
                else:
                    st.info("Pros data unavailable.")

            with right:
                st.markdown("### ⚠️ Cons")
                cons = [
                    x for col, x in values
                    if "con" in col.lower()
                ]
                if cons:
                    for x in cons[:10]:
                        st.warning(x)
                else:
                    st.info("Cons data unavailable.")
        else:
            st.info("Pros and cons data unavailable.")
    else:
        st.info("Pros and cons data unavailable.")

except Exception:
    st.info("Pros and cons data unavailable.")

st.markdown("---")
st.success(f"Profile loaded successfully for {company_id}.")