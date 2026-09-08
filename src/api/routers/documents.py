import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/companies/{ticker}/documents")
def get_company_documents(ticker: str):
    conn = get_connection()

    try:
        company = conn.execute(
            """
            SELECT id, company_name
            FROM companies
            WHERE UPPER(id) = UPPER(?)
            """,
            (ticker,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM documents
            WHERE UPPER(company_id) = UPPER(?)
            ORDER BY year DESC
            """,
            (company["id"],),
        ).fetchall()

        return {
            "company_id": company["id"],
            "company_name": company["company_name"],
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()