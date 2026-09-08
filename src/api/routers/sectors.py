import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    """Create a SQLite connection with dictionary-style rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/sectors")
def get_sectors():
    """
    Return all broad sectors with company counts.
    """

    conn = get_connection()

    try:
        query = """
            SELECT
                broad_sector,
                COUNT(DISTINCT company_id) AS company_count
            FROM sectors
            WHERE broad_sector IS NOT NULL
            GROUP BY broad_sector
            ORDER BY broad_sector
        """

        rows = conn.execute(query).fetchall()

        return {
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


@router.get("/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    """
    Return companies belonging to a specified broad sector.
    """

    conn = get_connection()

    try:
        # Check whether the sector exists.
        sector_query = """
            SELECT DISTINCT broad_sector
            FROM sectors
            WHERE LOWER(broad_sector) = LOWER(?)
        """

        sector_row = conn.execute(
            sector_query,
            (sector,),
        ).fetchone()

        if sector_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Sector '{sector}' not found",
            )

        actual_sector = sector_row["broad_sector"]

        query = """
            SELECT DISTINCT
                s.company_id,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                s.index_weight_pct,
                s.market_cap_category
            FROM sectors s
            LEFT JOIN companies c
                ON c.id = s.company_id
            WHERE LOWER(s.broad_sector) = LOWER(?)
            ORDER BY c.company_name
        """

        rows = conn.execute(
            query,
            (actual_sector,),
        ).fetchall()

        return {
            "sector": actual_sector,
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()