import sqlite3

from fastapi import APIRouter, Query

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    """Create a SQLite connection with dictionary-style rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/screener")
def screen_companies(
    min_roe: float | None = Query(
        default=None,
        description="Minimum return on equity percentage",
    ),
    max_debt_to_equity: float | None = Query(
        default=None,
        description="Maximum debt-to-equity ratio",
    ),
    min_revenue_cagr: float | None = Query(
        default=None,
        description="Minimum 5-year revenue CAGR percentage",
    ),
    min_quality_score: float | None = Query(
        default=None,
        description="Minimum composite quality score",
    ),
):
    """
    Screen Nifty 100 companies using latest available financial ratios.

    Supported filters:
    - min_roe
    - max_debt_to_equity
    - min_revenue_cagr
    - min_quality_score
    """

    conn = get_connection()

    try:
        query = """
            SELECT DISTINCT
                fr.company_id,
                c.company_name,
                fr.year,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.revenue_cagr_5yr,
                fr.composite_quality_score
            FROM financial_ratios fr
            JOIN companies c
                ON c.id = fr.company_id
            WHERE fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = fr.company_id
            )
        """

        conditions = []
        params = []

        # Minimum ROE
        if min_roe is not None:
            conditions.append(
                "fr.return_on_equity_pct >= ?"
            )
            params.append(min_roe)

        # Maximum Debt-to-Equity
        if max_debt_to_equity is not None:
            conditions.append(
                "fr.debt_to_equity <= ?"
            )
            params.append(max_debt_to_equity)

        # Minimum Revenue CAGR
        if min_revenue_cagr is not None:
            conditions.append(
                "fr.revenue_cagr_5yr >= ?"
            )
            params.append(min_revenue_cagr)

        # Minimum Quality Score
        if min_quality_score is not None:
            conditions.append(
                "fr.composite_quality_score >= ?"
            )
            params.append(min_quality_score)

        # Add dynamic filters
        if conditions:
            query += " AND " + " AND ".join(conditions)

        # Highest quality score first
        query += """
            ORDER BY
                fr.composite_quality_score DESC
        """

        rows = conn.execute(
            query,
            params,
        ).fetchall()

        data = [dict(row) for row in rows]

        return {
            "count": len(data),
            "filters": {
                "min_roe": min_roe,
                "max_debt_to_equity": max_debt_to_equity,
                "min_revenue_cagr": min_revenue_cagr,
                "min_quality_score": min_quality_score,
            },
            "data": data,
        }

    finally:
        conn.close()