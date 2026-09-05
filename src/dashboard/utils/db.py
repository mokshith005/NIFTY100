from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# =========================================================
# DATABASE HELPER
# =========================================================

def _query(sql, params=None):
    """
    Execute a read-only SQL query and return a pandas DataFrame.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            sql,
            conn,
            params=params or (),
        )
    finally:
        conn.close()


# =========================================================
# COMPANIES
# =========================================================

@st.cache_data(ttl=600)
def get_companies():
    """
    Return all Nifty 100 companies.

    The physical companies table uses `id` as the company identifier.
    The dashboard uses `company_id`, so `id` is aliased accordingly.

    Sector information is added from the sectors table using exactly
    one sector record per company.
    """
    return _query(
        """
        WITH ranked_sectors AS (
            SELECT
                company_id,
                broad_sector,
                sub_sector,
                index_weight_pct,
                ROW_NUMBER() OVER (
                    PARTITION BY company_id
                    ORDER BY
                        COALESCE(index_weight_pct, 0) DESC,
                        broad_sector,
                        sub_sector,
                        id DESC
                ) AS rn
            FROM sectors
        )

        SELECT
            c.id AS company_id,
            c.company_name,
            c.company_logo,
            c.chart_link,
            c.about_company,
            c.website,
            c.nse_profile,
            c.bse_profile,
            c.face_value,
            c.book_value,
            c.roce_percentage,
            c.roe_percentage,

            COALESCE(
                rs.broad_sector,
                'Unknown'
            ) AS sector,

            rs.broad_sector,
            rs.sub_sector,
            rs.index_weight_pct

        FROM companies c

        LEFT JOIN ranked_sectors rs
            ON rs.company_id = c.id
           AND rs.rn = 1

        ORDER BY c.company_name
        """
    )


# =========================================================
# FINANCIAL RATIOS
# =========================================================

@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    """
    Return financial ratios for a company.

    If year is supplied, return that year's data.
    Otherwise return all available years.
    """
    if not ticker:
        return pd.DataFrame()

    if year is not None:
        return _query(
            """
            SELECT
                fr.*,
                c.company_name
            FROM financial_ratios fr
            LEFT JOIN companies c
                ON c.id = fr.company_id
            WHERE fr.company_id = ?
              AND CAST(fr.year AS TEXT) = CAST(? AS TEXT)
            ORDER BY fr.year DESC
            """,
            (ticker, year),
        )

    return _query(
        """
        SELECT
            fr.*,
            c.company_name
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON c.id = fr.company_id
        WHERE fr.company_id = ?
        ORDER BY
            CAST(fr.year AS INTEGER) DESC,
            fr.year DESC
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_latest_ratios(ticker):
    """
    Return the latest financial-ratio record for a company.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT *
        FROM (
            SELECT
                fr.*,
                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY
                        CAST(fr.year AS INTEGER) DESC,
                        fr.id DESC
                ) AS rn
            FROM financial_ratios fr
            WHERE fr.company_id = ?
        )
        WHERE rn = 1
        """,
        (ticker,),
    )


# =========================================================
# PROFIT & LOSS
# =========================================================

@st.cache_data(ttl=600)
def get_pl(ticker):
    """
    Return Profit & Loss history for a company.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            p.*,
            c.company_name
        FROM profitandloss p
        LEFT JOIN companies c
            ON c.id = p.company_id
        WHERE p.company_id = ?
        ORDER BY
            CAST(p.year AS INTEGER) ASC,
            p.year ASC
        """,
        (ticker,),
    )


# =========================================================
# BALANCE SHEET
# =========================================================

@st.cache_data(ttl=600)
def get_bs(ticker):
    """
    Return Balance Sheet history for a company.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            b.*,
            c.company_name
        FROM balancesheet b
        LEFT JOIN companies c
            ON c.id = b.company_id
        WHERE b.company_id = ?
        ORDER BY
            CAST(b.year AS INTEGER) ASC,
            b.year ASC
        """,
        (ticker,),
    )


# =========================================================
# CASH FLOW
# =========================================================

@st.cache_data(ttl=600)
def get_cf(ticker):
    """
    Return Cash Flow history.

    If the dedicated `cashflow` table exists, use it.
    Otherwise fall back to financial_ratios fields that
    contain CFO and FCF information.
    """
    if not ticker:
        return pd.DataFrame()

    # Check whether cashflow table exists.
    try:
        table_check = _query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'cashflow'
            """
        )

        cashflow_exists = not table_check.empty

    except Exception:
        cashflow_exists = False

    if cashflow_exists:
        try:
            return _query(
                """
                SELECT
                    cf.*,
                    c.company_name
                FROM cashflow cf
                LEFT JOIN companies c
                    ON c.id = cf.company_id
                WHERE cf.company_id = ?
                ORDER BY
                    CAST(cf.year AS INTEGER) ASC,
                    cf.year ASC
                """,
                (ticker,),
            )
        except Exception:
            pass

    # Fallback to financial_ratios
    return _query(
        """
        SELECT
            fr.company_id,
            c.company_name,
            fr.year,
            fr.free_cash_flow_cr,
            fr.capex_cr,
            fr.cash_from_operations_cr
        FROM financial_ratios fr
        LEFT JOIN companies c
            ON c.id = fr.company_id
        WHERE fr.company_id = ?
        ORDER BY
            CAST(fr.year AS INTEGER) ASC,
            fr.year ASC
        """,
        (ticker,),
    )


# =========================================================
# SECTORS
# =========================================================

@st.cache_data(ttl=600)
def get_sectors():
    """
    Return distinct broad sectors.
    """
    return _query(
        """
        SELECT DISTINCT
            broad_sector
        FROM sectors
        WHERE broad_sector IS NOT NULL
        ORDER BY broad_sector
        """
    )


@st.cache_data(ttl=600)
def get_sector_data():
    """
    Return exactly one latest financial/market/sector record
    for each company.

    This avoids duplicate companies caused by multiple records
    having the same maximum year.
    """

    return _query(
        """
        WITH ranked_pl AS (
            SELECT
                p.*,
                ROW_NUMBER() OVER (
                    PARTITION BY p.company_id
                    ORDER BY
                        CAST(p.year AS INTEGER) DESC,
                        p.id DESC
                ) AS rn
            FROM profitandloss p
        ),

        ranked_mc AS (
            SELECT
                m.*,
                ROW_NUMBER() OVER (
                    PARTITION BY m.company_id
                    ORDER BY
                        CAST(m.year AS INTEGER) DESC,
                        m.id DESC
                ) AS rn
            FROM market_cap m
        ),

        ranked_ratios AS (
            SELECT
                r.*,
                ROW_NUMBER() OVER (
                    PARTITION BY r.company_id
                    ORDER BY
                        CAST(r.year AS INTEGER) DESC,
                        r.id DESC
                ) AS rn
            FROM financial_ratios r
        ),

        ranked_sectors AS (
            SELECT
                s.*,
                ROW_NUMBER() OVER (
                    PARTITION BY s.company_id
                    ORDER BY
                        COALESCE(s.index_weight_pct, 0) DESC,
                        s.broad_sector,
                        s.sub_sector,
                        s.id DESC
                ) AS rn
            FROM sectors s
        )

        SELECT
            c.id AS company_id,
            c.company_name,

            rs.broad_sector,
            rs.sub_sector,
            rs.index_weight_pct,
            rs.market_cap_category,

            rp.year AS year,

            rp.sales AS revenue,
            rp.net_profit,
            rp.operating_profit,
            rp.opm_percentage,

            rr.net_profit_margin_pct,
            rr.operating_profit_margin_pct,
            rr.return_on_equity_pct,
            rr.debt_to_equity,
            rr.interest_coverage,
            rr.asset_turnover,
            rr.free_cash_flow_cr,
            rr.capex_cr,
            rr.cash_from_operations_cr,

            rm.market_cap_crore,
            rm.enterprise_value_crore,
            rm.pe_ratio,
            rm.pb_ratio,
            rm.ev_ebitda,
            rm.dividend_yield_pct

        FROM companies c

        LEFT JOIN ranked_pl rp
            ON rp.company_id = c.id
           AND rp.rn = 1

        LEFT JOIN ranked_mc rm
            ON rm.company_id = c.id
           AND rm.rn = 1

        LEFT JOIN ranked_ratios rr
            ON rr.company_id = c.id
           AND rr.rn = 1

        LEFT JOIN ranked_sectors rs
            ON rs.company_id = c.id
           AND rs.rn = 1

        ORDER BY c.company_name
        """
    )


# =========================================================
# PEER GROUPS
# =========================================================

@st.cache_data(ttl=600)
def get_peer_groups():
    """
    Return all available peer-group names.
    """
    return _query(
        """
        SELECT DISTINCT
            peer_group_name
        FROM peer_groups
        WHERE peer_group_name IS NOT NULL
        ORDER BY peer_group_name
        """
    )


@st.cache_data(ttl=600)
def get_peers(group_name):
    """
    Return companies belonging to a peer group.
    """
    if not group_name:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            pg.company_id,
            c.company_name,
            pg.peer_group_name,
            pg.is_benchmark
        FROM peer_groups pg
        LEFT JOIN companies c
            ON c.id = pg.company_id
        WHERE pg.peer_group_name = ?
        ORDER BY
            pg.is_benchmark DESC,
            c.company_name
        """,
        (group_name,),
    )


# =========================================================
# PROS & CONS
# =========================================================

@st.cache_data(ttl=600)
def get_proscons(ticker):
    """
    Return company pros and cons.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            pc.*,
            c.company_name
        FROM prosandcons pc
        LEFT JOIN companies c
            ON c.id = pc.company_id
        WHERE pc.company_id = ?
        """,
        (ticker,),
    )


# =========================================================
# MARKET CAP
# =========================================================

@st.cache_data(ttl=600)
def get_market_cap(ticker):
    """
    Return market-cap history for a company.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            m.*,
            c.company_name
        FROM market_cap m
        LEFT JOIN companies c
            ON c.id = m.company_id
        WHERE m.company_id = ?
        ORDER BY
            CAST(m.year AS INTEGER) ASC,
            m.year ASC
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_latest_market_data(ticker):
    """
    Return latest market-cap/valuation record.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT *
        FROM (
            SELECT
                m.*,
                ROW_NUMBER() OVER (
                    PARTITION BY m.company_id
                    ORDER BY
                        CAST(m.year AS INTEGER) DESC,
                        m.id DESC
                ) AS rn
            FROM market_cap m
            WHERE m.company_id = ?
        )
        WHERE rn = 1
        """,
        (ticker,),
    )


# =========================================================
# VALUATION
# =========================================================

@st.cache_data(ttl=600)
def get_valuation(ticker):
    """
    Return valuation information.

    Primary source:
        valuation_summary

    Fallback:
        market_cap + financial_ratios
    """
    if not ticker:
        return pd.DataFrame()

    # Try valuation_summary first.
    try:
        table_check = _query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'valuation_summary'
            """
        )

        if not table_check.empty:
            result = _query(
                """
                SELECT *
                FROM valuation_summary
                WHERE company_id = ?
                """,
                (ticker,),
            )

            if not result.empty:
                return result

    except Exception:
        pass

    # Try valuation table if present.
    try:
        table_check = _query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'valuation'
            """
        )

        if not table_check.empty:
            result = _query(
                """
                SELECT *
                FROM valuation
                WHERE company_id = ?
                """,
                (ticker,),
            )

            if not result.empty:
                return result

    except Exception:
        pass

    # Fallback to latest market data + latest ratios.
    market = get_latest_market_data(ticker)
    ratios = get_latest_ratios(ticker)

    if market.empty and ratios.empty:
        return pd.DataFrame()

    result = pd.DataFrame(
        {
            "company_id": [ticker],
        }
    )

    if not market.empty:
        m = market.iloc[0]

        result["year"] = [
            m.get("year")
        ]

        result["P/E"] = [
            m.get("pe_ratio")
        ]

        result["P/B"] = [
            m.get("pb_ratio")
        ]

        result["EV/EBITDA"] = [
            m.get("ev_ebitda")
        ]

        result["market_cap_crore"] = [
            m.get("market_cap_crore")
        ]

        result["enterprise_value_crore"] = [
            m.get("enterprise_value_crore")
        ]

        result["dividend_yield_pct"] = [
            m.get("dividend_yield_pct")
        ]

    if not ratios.empty:
        r = ratios.iloc[0]

        result["free_cash_flow_cr"] = [
            r.get("free_cash_flow_cr")
        ]

        market_cap = (
            result["market_cap_crore"].iloc[0]
            if "market_cap_crore" in result.columns
            else None
        )

        fcf = r.get("free_cash_flow_cr")

        if (
            pd.notna(market_cap)
            and pd.notna(fcf)
            and float(market_cap) != 0
        ):
            result["FCF_yield_pct"] = [
                float(fcf) / float(market_cap) * 100
            ]
        else:
            result["FCF_yield_pct"] = [pd.NA]

    return result


# =========================================================
# AVAILABLE YEARS
# =========================================================

@st.cache_data(ttl=600)
def get_available_years():
    """
    Return available financial years.
    """
    years = _query(
        """
        SELECT DISTINCT year
        FROM (
            SELECT year FROM profitandloss
            UNION
            SELECT year FROM financial_ratios
            UNION
            SELECT year FROM market_cap
        )
        WHERE year IS NOT NULL
        ORDER BY CAST(year AS INTEGER)
        """
    )

    if years.empty:
        return []

    return years["year"].tolist()


# =========================================================
# UTILITY: COMPANY LOOKUP
# =========================================================

@st.cache_data(ttl=600)
def get_company(ticker):
    """
    Return a single company record.
    """
    if not ticker:
        return pd.DataFrame()

    return _query(
        """
        SELECT
            id AS company_id,
            company_name,
            company_logo,
            chart_link,
            about_company,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        WHERE id = ?
        """,
        (ticker,),
    )


# =========================================================
# UTILITY: COMPANY EXISTS
# =========================================================

@st.cache_data(ttl=600)
def company_exists(ticker):
    """
    Check whether a company exists.
    """
    if not ticker:
        return False

    result = _query(
        """
        SELECT 1
        FROM companies
        WHERE id = ?
        LIMIT 1
        """,
        (ticker,),
    )

    return not result.empty