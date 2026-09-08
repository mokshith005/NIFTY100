import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter()

DB_PATH = Path("db/nifty100.db")


def get_connection():
    """Create a SQLite database connection."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Database not found",
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dict(rows):
    """Convert SQLite rows to dictionaries."""
    return [dict(row) for row in rows]


@router.get("/companies")
def get_companies():
    """Return all Nifty 100 companies."""
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                id AS company_id,
                company_name,
                website,
                face_value,
                book_value,
                roce_percentage,
                roe_percentage
            FROM companies
            ORDER BY company_name
            """
        ).fetchall()

        return {
            "count": len(rows),
            "companies": rows_to_dict(rows),
        }
    finally:
        conn.close()


@router.get("/companies/{ticker}")
def get_company(ticker: str):
    """Return company profile information."""
    conn = get_connection()

    try:
        row = conn.execute(
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
            (ticker.upper(),),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        return dict(row)
    finally:
        conn.close()


@router.get("/companies/{ticker}/pl")
def get_profit_and_loss(ticker: str):
    """Return profit and loss history for a company."""
    conn = get_connection()

    try:
        company = conn.execute(
            "SELECT id FROM companies WHERE id = ?",
            (ticker.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year
            """,
            (ticker.upper(),),
        ).fetchall()

        return {
            "company_id": ticker.upper(),
            "count": len(rows),
            "data": rows_to_dict(rows),
        }
    finally:
        conn.close()


@router.get("/companies/{ticker}/bs")
def get_balance_sheet(ticker: str):
    """Return balance sheet history for a company."""
    conn = get_connection()

    try:
        company = conn.execute(
            "SELECT id FROM companies WHERE id = ?",
            (ticker.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM balancesheet
            WHERE company_id = ?
            ORDER BY year
            """,
            (ticker.upper(),),
        ).fetchall()

        return {
            "company_id": ticker.upper(),
            "count": len(rows),
            "data": rows_to_dict(rows),
        }
    finally:
        conn.close()


@router.get("/companies/{ticker}/cashflow")
def get_cashflow(ticker: str):
    """Return cash-flow history for a company."""
    conn = get_connection()

    try:
        company = conn.execute(
            "SELECT id FROM companies WHERE id = ?",
            (ticker.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM cashflow
            WHERE company_id = ?
            ORDER BY year
            """,
            (ticker.upper(),),
        ).fetchall()

        return {
            "company_id": ticker.upper(),
            "count": len(rows),
            "data": rows_to_dict(rows),
        }
    finally:
        conn.close()


@router.get("/companies/{ticker}/ratios")
def get_financial_ratios(ticker: str):
    """Return financial ratio history for a company."""
    conn = get_connection()

    try:
        company = conn.execute(
            "SELECT id FROM companies WHERE id = ?",
            (ticker.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            (ticker.upper(),),
        ).fetchall()

        return {
            "company_id": ticker.upper(),
            "count": len(rows),
            "data": rows_to_dict(rows),
        }
    finally:
        conn.close()


@router.get("/companies/{ticker}/tearsheet")
def get_tearsheet(ticker: str):
    """Return the available company tearsheet document."""
    conn = get_connection()

    try:
        company = conn.execute(
            "SELECT id FROM companies WHERE id = ?",
            (ticker.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{ticker.upper()}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM documents
            WHERE company_id = ?
            ORDER BY id
            """,
            (ticker.upper(),),
        ).fetchall()

        return {
            "company_id": ticker.upper(),
            "count": len(rows),
            "documents": rows_to_dict(rows),
        }
    finally:
        conn.close()