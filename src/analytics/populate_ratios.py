"""
Sprint 2 - Day 12
Complete NIFTY 100 Financial Ratio Engine.

Populates financial_ratios with:
- Profitability ratios
- Leverage ratios
- Efficiency ratios
- Cash-flow KPIs
- 5-year CAGR metrics
- Composite quality score

Handles duplicate cash-flow company/year records by aggregating
their values before KPI calculation.
"""

from pathlib import Path
import sqlite3

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    interest_coverage,
    interest_coverage_label,
    interest_coverage_warning,
    high_leverage_flag,
    net_debt,
    asset_turnover,
)

from src.analytics.cagr import calculate_cagr

from src.analytics.cashflow_kpis import (
    free_cash_flow,
    calculate_cfo_pat_5yr,
    capex_intensity,
    fcf_conversion_rate,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "db" / "nifty100.db"


REQUIRED_COLUMNS = {
    "roce_pct": "REAL",
    "roa_pct": "REAL",
    "net_debt_cr": "REAL",
    "icr_label": "TEXT",
    "icr_warning_flag": "INTEGER",
    "high_leverage_flag": "INTEGER",
    "cfo_quality_score": "REAL",
    "capex_intensity_pct": "REAL",
    "fcf_conversion_rate_pct": "REAL",
    "revenue_cagr_5yr": "REAL",
    "revenue_cagr_5yr_flag": "TEXT",
    "pat_cagr_5yr": "REAL",
    "pat_cagr_5yr_flag": "TEXT",
    "eps_cagr_5yr": "REAL",
    "eps_cagr_5yr_flag": "TEXT",
    "composite_quality_score": "REAL",
}


def fetch_one(conn, query, params=()):
    """Return one database row."""
    return conn.execute(query, params).fetchone()


def add_missing_columns(conn):
    """Add Sprint 2 KPI columns if missing."""

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(financial_ratios)"
        ).fetchall()
    }

    for column, data_type in REQUIRED_COLUMNS.items():
        if column not in existing:
            conn.execute(
                f"""
                ALTER TABLE financial_ratios
                ADD COLUMN {column} {data_type}
                """
            )
            print(f"Added column: {column}")

    conn.commit()


def get_pl_data(conn, company_id, year):
    """Get P&L data for a company/year."""

    if year is not None:
        row = fetch_one(
            conn,
            """
            SELECT
                sales,
                expenses,
                operating_profit,
                opm_percentage,
                other_income,
                interest,
                depreciation,
                profit_before_tax,
                tax_percentage,
                net_profit,
                eps,
                dividend_payout
            FROM profitandloss
            WHERE company_id = ?
              AND CAST(year AS REAL) = CAST(? AS REAL)
            ORDER BY id
            LIMIT 1
            """,
            (company_id, year),
        )

        if row is not None:
            return row

    return fetch_one(
        conn,
        """
        SELECT
            sales,
            expenses,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (company_id,),
    )


def get_bs_data(conn, company_id, year):
    """Get Balance Sheet data for a company/year."""

    if year is not None:
        row = fetch_one(
            conn,
            """
            SELECT
                equity_capital,
                reserves,
                borrowings,
                investments,
                total_assets
            FROM balancesheet
            WHERE company_id = ?
              AND CAST(year AS REAL) = CAST(? AS REAL)
            ORDER BY id
            LIMIT 1
            """,
            (company_id, year),
        )

        if row is not None:
            return row

    return fetch_one(
        conn,
        """
        SELECT
            equity_capital,
            reserves,
            borrowings,
            investments,
            total_assets
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (company_id,),
    )


def get_cf_data(conn, company_id, year):
    """
    Get aggregated Cash Flow data for a company/year.

    Duplicate source cash-flow rows are summed rather than
    selecting only the first row.
    """

    if year is not None:
        row = conn.execute(
            """
            SELECT
                SUM(COALESCE(operating_activity, 0)),
                SUM(COALESCE(investing_activity, 0)),
                SUM(COALESCE(financing_activity, 0))
            FROM cashflow
            WHERE company_id = ?
              AND CAST(year AS REAL) = CAST(? AS REAL)
            """,
            (company_id, year),
        ).fetchone()

        if row is not None and any(
            value is not None for value in row
        ):
            return row

    row = conn.execute(
        """
        SELECT
            SUM(COALESCE(operating_activity, 0)),
            SUM(COALESCE(investing_activity, 0)),
            SUM(COALESCE(financing_activity, 0))
        FROM cashflow
        WHERE company_id = ?
        """,
        (company_id,),
    ).fetchone()

    if row is not None and any(
        value is not None for value in row
    ):
        return row

    return None


def get_sector(conn, company_id):
    """Return the company's broad sector."""

    row = fetch_one(
        conn,
        """
        SELECT broad_sector
        FROM sectors
        WHERE company_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (company_id,),
    )

    if row is None:
        return None

    return row[0]


def get_metric_history(conn, company_id, metric):
    """Get historical metric values."""

    query = f"""
        SELECT
            CAST(year AS REAL),
            {metric}
        FROM profitandloss
        WHERE company_id = ?
          AND {metric} IS NOT NULL
        ORDER BY CAST(year AS REAL)
    """

    return conn.execute(
        query,
        (company_id,),
    ).fetchall()


def calculate_5yr_cagr(
    conn,
    company_id,
    metric,
    current_year,
):
    """
    Calculate 5-year CAGR ending at current_year.

    Handles:
    - Missing years
    - Invalid years
    - Missing metric values
    - Insufficient history
    - Positive/negative CAGR edge cases
    """

    if current_year is None:
        return None, "INSUFFICIENT"

    try:
        current_year = float(current_year)
    except (TypeError, ValueError):
        return None, "INSUFFICIENT"

    rows = get_metric_history(
        conn,
        company_id,
        metric,
    )

    valid_rows = []

    for row in rows:
        year_value = row[0]
        metric_value = row[1]

        if year_value is None:
            continue

        try:
            year_value = float(year_value)
        except (TypeError, ValueError):
            continue

        if metric_value is None:
            continue

        if year_value <= current_year:
            valid_rows.append(
                (year_value, metric_value)
            )

    if len(valid_rows) < 6:
        return None, "INSUFFICIENT"

    start_year = current_year - 5

    exact_start = [
        row
        for row in valid_rows
        if row[0] == start_year
    ]

    exact_end = [
        row
        for row in valid_rows
        if row[0] == current_year
    ]

    if not exact_start or not exact_end:
        return None, "INSUFFICIENT"

    start = exact_start[-1][1]
    end = exact_end[-1][1]

    return calculate_cagr(
        start,
        end,
        5,
    )


def get_cfo_quality(conn, company_id, current_year):
    """
    Calculate average CFO/PAT ratio over up to five years.
    """

    if current_year is None:
        return None, None

    try:
        current_year = float(current_year)
    except (TypeError, ValueError):
        return None, None

    rows = conn.execute(
        """
        SELECT
            CAST(cf.year AS REAL),
            cf.operating_activity,
            pl.net_profit
        FROM cashflow cf
        JOIN profitandloss pl
            ON cf.company_id = pl.company_id
           AND CAST(cf.year AS REAL) = CAST(pl.year AS REAL)
        WHERE cf.company_id = ?
          AND CAST(cf.year AS REAL) <= ?
        ORDER BY CAST(cf.year AS REAL) DESC
        """,
        (
            company_id,
            current_year,
        ),
    ).fetchall()

    grouped = {}

    for year, cfo, pat in rows:

        if year is None:
            continue

        if year not in grouped:
            grouped[year] = {
                "cfo": 0,
                "pat": pat,
            }

        grouped[year]["cfo"] += cfo or 0

        if grouped[year]["pat"] is None and pat is not None:
            grouped[year]["pat"] = pat

    ratios = []

    for values in list(grouped.values())[:5]:

        pat = values["pat"]

        if pat is None or pat == 0:
            continue

        ratios.append(
            values["cfo"] / pat
        )

    if not ratios:
        return None, None

    score = sum(ratios) / len(ratios)

    if score > 1.0:
        label = "High Quality"
    elif score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return score, label


def composite_quality_score(
    npm,
    roe,
    debt_equity,
    asset_turnover_value,
    cfo_quality,
):
    """Calculate a bounded composite quality score."""

    components = []
    weights = []

    if npm is not None:
        components.append(
            max(0, min(npm, 30))
        )
        weights.append(20)

    if roe is not None:
        components.append(
            max(0, min(roe, 30))
        )
        weights.append(30)

    if debt_equity is not None:
        leverage_score = max(
            0,
            30 - min(debt_equity, 30),
        )
        components.append(
            leverage_score
        )
        weights.append(20)

    if asset_turnover_value is not None:
        components.append(
            max(
                0,
                min(asset_turnover_value * 10, 10),
            )
        )
        weights.append(10)

    if cfo_quality is not None:
        components.append(
            max(
                0,
                min(cfo_quality * 10, 10),
            )
        )
        weights.append(20)

    if not components:
        return None

    weighted_total = sum(
        value * weight
        for value, weight in zip(
            components,
            weights,
        )
    )

    total_weight = sum(weights)

    return weighted_total / total_weight * 100 / 100


def populate():
    """Populate all Sprint 2 KPI columns."""

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    add_missing_columns(conn)

    ratio_rows = conn.execute(
        """
        SELECT
            id,
            company_id,
            year
        FROM financial_ratios
        ORDER BY id
        """
    ).fetchall()

    print("=" * 70)
    print("SPRINT 2 - DAY 12 RATIO ENGINE")
    print("=" * 70)
    print(
        f"Ratio rows: {len(ratio_rows)}"
    )

    updated = 0

    for ratio_id, company_id, year in ratio_rows:

        pl = get_pl_data(
            conn,
            company_id,
            year,
        )

        bs = get_bs_data(
            conn,
            company_id,
            year,
        )

        cf = get_cf_data(
            conn,
            company_id,
            year,
        )

        sector = get_sector(
            conn,
            company_id,
        )

        if pl is None:
            continue

        (
            sales,
            expenses,
            operating_profit,
            source_opm,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout,
        ) = pl

        if bs is not None:
            (
                equity_capital,
                reserves,
                borrowings,
                investments,
                total_assets,
            ) = bs
        else:
            equity_capital = None
            reserves = None
            borrowings = None
            investments = None
            total_assets = None

        if cf is not None:
            (
                operating_activity,
                investing_activity,
                financing_activity,
            ) = cf
        else:
            operating_activity = None
            investing_activity = None
            financing_activity = None

        # ----------------------------------------------------------
        # Profitability
        # ----------------------------------------------------------

        npm = net_profit_margin(
            net_profit,
            sales,
        )

        opm = operating_profit_margin(
            operating_profit,
            sales,
        )

        roe = return_on_equity(
            net_profit,
            equity_capital,
            reserves,
        )

        ebit = (
            (operating_profit or 0)
            + (other_income or 0)
        )

        roce = return_on_capital_employed(
            ebit,
            equity_capital,
            reserves,
            borrowings,
        )

        roa = return_on_assets(
            net_profit,
            total_assets,
        )

        # ----------------------------------------------------------
        # Leverage
        # ----------------------------------------------------------

        de = debt_to_equity(
            borrowings,
            equity_capital,
            reserves,
        )

        icr = interest_coverage(
            operating_profit,
            other_income,
            interest,
        )

        icr_label = interest_coverage_label(
            icr
        )

        icr_warning = interest_coverage_warning(
            icr
        )

        high_leverage = high_leverage_flag(
            de,
            sector,
        )

        net_debt_value = net_debt(
            borrowings,
            investments,
        )

        turnover = asset_turnover(
            sales,
            total_assets,
        )

        # ----------------------------------------------------------
        # Cash Flow
        # ----------------------------------------------------------

        fcf = free_cash_flow(
            operating_activity,
            investing_activity,
        )

        if operating_activity is not None:
            cfo_quality, _ = get_cfo_quality(
                conn,
                company_id,
                year,
            )
        else:
            cfo_quality = None

        capex_intensity_value = capex_intensity(
            investing_activity,
            sales,
        )

        fcf_conversion = fcf_conversion_rate(
            fcf,
            operating_profit,
        )

        # ----------------------------------------------------------
        # CAGR
        # ----------------------------------------------------------

        revenue_cagr, revenue_flag = calculate_5yr_cagr(
            conn,
            company_id,
            "sales",
            year,
        )

        pat_cagr, pat_flag = calculate_5yr_cagr(
            conn,
            company_id,
            "net_profit",
            year,
        )

        eps_cagr, eps_flag = calculate_5yr_cagr(
            conn,
            company_id,
            "eps",
            year,
        )

        # ----------------------------------------------------------
        # Other KPIs
        # ----------------------------------------------------------

        book_value = (
            (equity_capital or 0)
            + (reserves or 0)
        )

        dividend_payout_ratio = dividend_payout

        total_debt = borrowings

        composite = composite_quality_score(
            npm,
            roe,
            de,
            turnover,
            cfo_quality,
        )

        # ----------------------------------------------------------
        # Database update
        # ----------------------------------------------------------

        conn.execute(
            """
            UPDATE financial_ratios
            SET
                net_profit_margin_pct = ?,
                operating_profit_margin_pct = ?,
                return_on_equity_pct = ?,
                debt_to_equity = ?,
                interest_coverage = ?,
                asset_turnover = ?,
                free_cash_flow_cr = ?,
                capex_cr = ?,
                earnings_per_share = ?,
                book_value_per_share = ?,
                dividend_payout_ratio_pct = ?,
                total_debt_cr = ?,
                cash_from_operations_cr = ?,
                roce_pct = ?,
                roa_pct = ?,
                net_debt_cr = ?,
                icr_label = ?,
                icr_warning_flag = ?,
                high_leverage_flag = ?,
                cfo_quality_score = ?,
                capex_intensity_pct = ?,
                fcf_conversion_rate_pct = ?,
                revenue_cagr_5yr = ?,
                revenue_cagr_5yr_flag = ?,
                pat_cagr_5yr = ?,
                pat_cagr_5yr_flag = ?,
                eps_cagr_5yr = ?,
                eps_cagr_5yr_flag = ?,
                composite_quality_score = ?
            WHERE id = ?
            """,
            (
                npm,
                opm,
                roe,
                de,
                icr,
                turnover,
                fcf,
                abs(investing_activity)
                if investing_activity is not None
                else None,
                eps,
                book_value,
                dividend_payout_ratio,
                total_debt,
                operating_activity,
                roce,
                roa,
                net_debt_value,
                icr_label,
                int(icr_warning),
                int(high_leverage),
                cfo_quality,
                capex_intensity_value,
                fcf_conversion,
                revenue_cagr,
                revenue_flag,
                pat_cagr,
                pat_flag,
                eps_cagr,
                eps_flag,
                composite,
                ratio_id,
            ),
        )

        updated += 1

    conn.commit()

    # ----------------------------------------------------------
    # Validation
    # ----------------------------------------------------------

    ratio_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios
        """
    ).fetchone()[0]

    print(
        f"Rows updated: {updated}"
    )

    print(
        f"Financial ratios row count: {ratio_count}"
    )

    print("\nKPI population check:")

    columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for column in columns:

        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM financial_ratios
            WHERE {column} IS NOT NULL
            """
        ).fetchone()[0]

        print(
            f"{column:<32}"
            f"{count}/{ratio_count} populated"
        )

    print("\nForeign key check:")

    fk = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print(fk)

    conn.close()


if __name__ == "__main__":
    populate()