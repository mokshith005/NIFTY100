import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    """Create a SQLite connection with dictionary-style rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/market-cap/{ticker}")
def get_market_cap(ticker: str):
    """
    Return the latest market-cap and valuation data for a company.
    """

    conn = get_connection()

    try:
        # ---------------------------------------------------------
        # 1. Verify company exists
        # ---------------------------------------------------------
        company_query = """
            SELECT
                id,
                company_name
            FROM companies
            WHERE UPPER(id) = UPPER(?)
        """

        company = conn.execute(
            company_query,
            (ticker,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        # ---------------------------------------------------------
        # 2. Get latest market-cap record
        # ---------------------------------------------------------
        query = """
            SELECT
                company_id,
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            WHERE UPPER(company_id) = UPPER(?)
            ORDER BY CAST(year AS INTEGER) DESC
            LIMIT 1
        """

        row = conn.execute(
            query,
            (company["id"],),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No market-cap data found for company '{ticker}'",
            )

        return {
            "company_id": company["id"],
            "company_name": company["company_name"],
            "data": dict(row),
        }

    finally:
        conn.close()