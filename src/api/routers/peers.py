import sqlite3

from fastapi import APIRouter, HTTPException

router = APIRouter()

DB_PATH = "db/nifty100.db"


def get_connection():
    """Create a SQLite connection with dictionary-style rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/peers/{group_name}")
def get_peer_group(group_name: str):
    """
    Return companies belonging to a peer group.
    """

    conn = get_connection()

    try:
        check_query = """
            SELECT DISTINCT peer_group_name
            FROM peer_groups
            WHERE LOWER(peer_group_name) = LOWER(?)
        """

        group_row = conn.execute(
            check_query,
            (group_name,),
        ).fetchone()

        if group_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Peer group '{group_name}' not found",
            )

        actual_group = group_row["peer_group_name"]

        query = """
            SELECT DISTINCT
                pg.company_id,
                c.company_name,
                pg.peer_group_name,
                pg.is_benchmark
            FROM peer_groups pg
            LEFT JOIN companies c
                ON c.id = pg.company_id
            WHERE LOWER(pg.peer_group_name) = LOWER(?)
            ORDER BY c.company_name
        """

        rows = conn.execute(
            query,
            (actual_group,),
        ).fetchall()

        return {
            "group_name": actual_group,
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    finally:
        conn.close()


@router.get("/companies/{ticker}/peers/compare")
def compare_company_with_peers(ticker: str):
    """
    Compare a company with the other companies in its peer group.

    Uses the latest available financial ratio year for each company.
    """

    conn = get_connection()

    try:
        # ---------------------------------------------------------
        # 1. Find the requested company
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

        company_id = company["id"]

        # ---------------------------------------------------------
        # 2. Find the company's peer group
        # ---------------------------------------------------------
        peer_group_query = """
            SELECT DISTINCT peer_group_name
            FROM peer_groups
            WHERE company_id = ?
        """

        peer_group_rows = conn.execute(
            peer_group_query,
            (company_id,),
        ).fetchall()

        if not peer_group_rows:
            raise HTTPException(
                status_code=404,
                detail=f"No peer group found for company '{ticker}'",
            )

        peer_groups = [
            row["peer_group_name"]
            for row in peer_group_rows
        ]

        # ---------------------------------------------------------
        # 3. Get peer companies
        # ---------------------------------------------------------
        placeholders = ",".join("?" for _ in peer_groups)

        peers_query = f"""
            SELECT DISTINCT
                pg.company_id,
                c.company_name,
                pg.peer_group_name,
                pg.is_benchmark
            FROM peer_groups pg
            LEFT JOIN companies c
                ON c.id = pg.company_id
            WHERE pg.peer_group_name IN ({placeholders})
            ORDER BY c.company_name
        """

        peers = conn.execute(
            peers_query,
            peer_groups,
        ).fetchall()

        # ---------------------------------------------------------
        # 4. Get latest financial ratios for peer companies
        # ---------------------------------------------------------
        peer_company_ids = list(
            dict.fromkeys(row["company_id"] for row in peers)
        )

        if not peer_company_ids:
            return {
                "company_id": company_id,
                "company_name": company["company_name"],
                "peer_groups": peer_groups,
                "peer_count": 0,
                "data": [],
            }

        company_placeholders = ",".join(
            "?" for _ in peer_company_ids
        )

        ratios_query = f"""
            SELECT
                fr.company_id,
                fr.year,
                fr.net_profit_margin_pct,
                fr.operating_profit_margin_pct,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.interest_coverage,
                fr.asset_turnover,
                fr.free_cash_flow_cr,
                fr.earnings_per_share,
                fr.book_value_per_share,
                fr.roce_pct,
                fr.roa_pct,
                fr.net_debt_cr,
                fr.composite_quality_score
            FROM financial_ratios fr
            INNER JOIN (
                SELECT
                    company_id,
                    MAX(year) AS latest_year
                FROM financial_ratios
                WHERE company_id IN ({company_placeholders})
                GROUP BY company_id
            ) latest
                ON fr.company_id = latest.company_id
                AND fr.year = latest.latest_year
            WHERE fr.company_id IN ({company_placeholders})
            ORDER BY fr.company_id
        """

        ratio_params = peer_company_ids + peer_company_ids

        ratio_rows = conn.execute(
            ratios_query,
            ratio_params,
        ).fetchall()

        ratio_map = {
            row["company_id"]: dict(row)
            for row in ratio_rows
        }

        # ---------------------------------------------------------
        # 5. Build comparison response
        # ---------------------------------------------------------
        data = []

        for peer in peers:
            peer_data = {
                "company_id": peer["company_id"],
                "company_name": peer["company_name"],
                "peer_group_name": peer["peer_group_name"],
                "is_benchmark": bool(peer["is_benchmark"]),
                "ratios": ratio_map.get(peer["company_id"]),
            }

            data.append(peer_data)

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "peer_groups": peer_groups,
            "peer_count": len(data),
            "data": data,
        }

    finally:
        conn.close()