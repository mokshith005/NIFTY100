import sqlite3

from fastapi import APIRouter

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/portfolio/stats")
def get_portfolio_stats():
    conn = get_connection()

    try:
        query = """
            SELECT
                COUNT(*) AS company_count,
                AVG(return_on_equity_pct) AS avg_roe,
                AVG(debt_to_equity) AS avg_debt_to_equity,
                AVG(revenue_cagr_5yr) AS avg_revenue_cagr_5yr,
                AVG(composite_quality_score) AS avg_quality_score
            FROM (
                SELECT
                    company_id,
                    return_on_equity_pct,
                    debt_to_equity,
                    revenue_cagr_5yr,
                    composite_quality_score
                FROM financial_ratios
                WHERE year = (
                    SELECT MAX(year)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id = financial_ratios.company_id
                )
                GROUP BY company_id
            )
        """

        row = conn.execute(query).fetchone()

        return {
            "company_count": row["company_count"],
            "avg_roe": row["avg_roe"],
            "avg_debt_to_equity": row["avg_debt_to_equity"],
            "avg_revenue_cagr_5yr": row["avg_revenue_cagr_5yr"],
            "avg_quality_score": row["avg_quality_score"],
        }

    finally:
        conn.close()