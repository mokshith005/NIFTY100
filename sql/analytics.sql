-- ============================================================
-- NIFTY 100 ANALYTICS QUERIES
-- ============================================================
-- Database: db/database.db
-- Purpose : Analytical SQL for NIFTY 100 data foundation
--
-- Duplicate handling:
-- P&L, Balance Sheet, Cash Flow and Financial Ratios can contain
-- multiple records for the same company/year. These queries use
-- ROW_NUMBER() and select one analytical record per company/year.
--
-- Raw data is NOT modified by these queries.
-- ============================================================


-- ============================================================
-- QUERY 1
-- DATABASE QUALITY CHECK
-- Count companies and major financial records
-- ============================================================

SELECT
    (SELECT COUNT(*) FROM companies) AS companies,
    (SELECT COUNT(*) FROM profitandloss) AS profit_loss_rows,
    (SELECT COUNT(*) FROM balancesheet) AS balance_sheet_rows,
    (SELECT COUNT(*) FROM cashflow) AS cashflow_rows,
    (SELECT COUNT(*) FROM financial_ratios) AS financial_ratio_rows,
    (SELECT COUNT(*) FROM stock_prices) AS stock_price_rows;


-- ============================================================
-- QUERY 2
-- TOTAL DATABASE ROWS
-- ============================================================

SELECT
    SUM(row_count) AS total_database_rows
FROM (
    SELECT COUNT(*) AS row_count FROM companies
    UNION ALL
    SELECT COUNT(*) FROM profitandloss
    UNION ALL
    SELECT COUNT(*) FROM balancesheet
    UNION ALL
    SELECT COUNT(*) FROM cashflow
    UNION ALL
    SELECT COUNT(*) FROM documents
    UNION ALL
    SELECT COUNT(*) FROM analysis
    UNION ALL
    SELECT COUNT(*) FROM prosandcons
    UNION ALL
    SELECT COUNT(*) FROM financial_ratios
    UNION ALL
    SELECT COUNT(*) FROM market_cap
    UNION ALL
    SELECT COUNT(*) FROM peer_groups
    UNION ALL
    SELECT COUNT(*) FROM sectors
    UNION ALL
    SELECT COUNT(*) FROM stock_prices
);


-- ============================================================
-- QUERY 3
-- COMPANY MASTER LIST
-- ============================================================

SELECT
    id AS company_id,
    company_name
FROM companies
ORDER BY id;


-- ============================================================
-- QUERY 4
-- COMPANY COUNT BY BROAD SECTOR
-- ============================================================

SELECT
    broad_sector,
    COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC, broad_sector;


-- ============================================================
-- QUERY 5
-- TOP 10 COMPANIES BY MARKET CAPITALISATION
-- Latest available market-cap record per company
-- ============================================================

WITH ranked_market_cap AS (
    SELECT
        m.*,
        ROW_NUMBER() OVER (
            PARTITION BY m.company_id
            ORDER BY CAST(m.year AS INTEGER) DESC, m.id DESC
        ) AS rn
    FROM market_cap m
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.market_cap_crore,
    r.enterprise_value_crore
FROM ranked_market_cap r
JOIN companies c
    ON c.id = r.company_id
WHERE r.rn = 1
ORDER BY r.market_cap_crore DESC
LIMIT 10;


-- ============================================================
-- QUERY 6
-- TOP 10 COMPANIES BY NET PROFIT
-- Latest unique company/year P&L record
-- ============================================================

WITH ranked_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id, p.year
            ORDER BY p.id DESC
        ) AS rn
    FROM profitandloss p
    WHERE p.year IS NOT NULL
),
latest_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id
            ORDER BY CAST(p.year AS REAL) DESC, p.id DESC
        ) AS latest_rn
    FROM ranked_pl p
    WHERE p.rn = 1
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.sales,
    p.net_profit,
    p.eps
FROM latest_pl p
JOIN companies c
    ON c.id = p.company_id
WHERE p.latest_rn = 1
ORDER BY p.net_profit DESC
LIMIT 10;


-- ============================================================
-- QUERY 7
-- TOP 10 COMPANIES BY ROE
-- Latest unique financial-ratio record
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.return_on_equity_pct,
    r.net_profit_margin_pct,
    r.operating_profit_margin_pct
FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
ORDER BY r.return_on_equity_pct DESC
LIMIT 10;


-- ============================================================
-- QUERY 8
-- TOP 10 COMPANIES BY SALES
-- Latest unique P&L record per company
-- ============================================================

WITH ranked_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id, p.year
            ORDER BY p.id DESC
        ) AS rn
    FROM profitandloss p
    WHERE p.year IS NOT NULL
),
latest_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id
            ORDER BY CAST(p.year AS REAL) DESC, p.id DESC
        ) AS latest_rn
    FROM ranked_pl p
    WHERE p.rn = 1
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.sales,
    p.operating_profit,
    p.net_profit
FROM latest_pl p
JOIN companies c
    ON c.id = p.company_id
WHERE p.latest_rn = 1
ORDER BY p.sales DESC
LIMIT 10;


-- ============================================================
-- QUERY 9
-- TOP 10 COMPANIES BY OPERATING PROFIT MARGIN
-- ============================================================

WITH ranked_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id, p.year
            ORDER BY p.id DESC
        ) AS rn
    FROM profitandloss p
    WHERE p.year IS NOT NULL
),
latest_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id
            ORDER BY CAST(p.year AS REAL) DESC, p.id DESC
        ) AS latest_rn
    FROM ranked_pl p
    WHERE p.rn = 1
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.opm_percentage,
    p.sales,
    p.operating_profit
FROM latest_pl p
JOIN companies c
    ON c.id = p.company_id
WHERE p.latest_rn = 1
ORDER BY p.opm_percentage DESC
LIMIT 10;


-- ============================================================
-- QUERY 10
-- SECTOR-WISE COMPANY DISTRIBUTION
-- ============================================================

SELECT
    s.broad_sector,
    s.sub_sector,
    COUNT(*) AS company_count,
    ROUND(AVG(s.index_weight_pct), 4) AS average_index_weight_pct
FROM sectors s
GROUP BY
    s.broad_sector,
    s.sub_sector
ORDER BY
    company_count DESC,
    average_index_weight_pct DESC;


-- ============================================================
-- QUERY 11
-- LATEST MARKET VALUATION METRICS
-- ============================================================

WITH ranked_market_cap AS (
    SELECT
        m.*,
        ROW_NUMBER() OVER (
            PARTITION BY m.company_id
            ORDER BY CAST(m.year AS INTEGER) DESC, m.id DESC
        ) AS rn
    FROM market_cap m
)
SELECT
    m.company_id,
    c.company_name,
    m.year,
    m.pe_ratio,
    m.pb_ratio,
    m.ev_ebitda,
    m.dividend_yield_pct
FROM ranked_market_cap m
JOIN companies c
    ON c.id = m.company_id
WHERE m.rn = 1
ORDER BY m.pe_ratio DESC
LIMIT 10;


-- ============================================================
-- QUERY 12
-- HIGHEST DIVIDEND YIELD COMPANIES
-- ============================================================

WITH ranked_market_cap AS (
    SELECT
        m.*,
        ROW_NUMBER() OVER (
            PARTITION BY m.company_id
            ORDER BY CAST(m.year AS INTEGER) DESC, m.id DESC
        ) AS rn
    FROM market_cap m
)
SELECT
    m.company_id,
    c.company_name,
    m.year,
    m.dividend_yield_pct,
    m.market_cap_crore
FROM ranked_market_cap m
JOIN companies c
    ON c.id = m.company_id
WHERE m.rn = 1
  AND m.dividend_yield_pct IS NOT NULL
ORDER BY m.dividend_yield_pct DESC
LIMIT 10;


-- ============================================================
-- QUERY 13
-- LOW DEBT-TO-EQUITY COMPANIES
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.debt_to_equity,
    r.total_debt_cr,
    r.return_on_equity_pct
FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
  AND r.debt_to_equity IS NOT NULL
ORDER BY r.debt_to_equity ASC
LIMIT 10;


-- ============================================================
-- QUERY 14
-- HIGHEST INTEREST COVERAGE
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.interest_coverage,
    r.debt_to_equity
FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
  AND r.interest_coverage IS NOT NULL
ORDER BY r.interest_coverage DESC
LIMIT 10;


-- ============================================================
-- QUERY 15
-- LATEST BALANCE SHEET SUMMARY
-- ============================================================

WITH ranked_balance AS (
    SELECT
        b.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.company_id, b.year
            ORDER BY b.id DESC
        ) AS rn
    FROM balancesheet b
    WHERE b.year IS NOT NULL
),
latest_balance AS (
    SELECT
        b.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.company_id
            ORDER BY CAST(b.year AS REAL) DESC, b.id DESC
        ) AS latest_rn
    FROM ranked_balance b
    WHERE b.rn = 1
)
SELECT
    b.company_id,
    c.company_name,
    b.year,
    b.total_assets,
    b.total_liabilities,
    b.borrowings,
    b.reserves
FROM latest_balance b
JOIN companies c
    ON c.id = b.company_id
WHERE b.latest_rn = 1
ORDER BY b.total_assets DESC;


-- ============================================================
-- QUERY 16
-- HIGHEST FREE CASH FLOW COMPANIES
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.free_cash_flow_cr,
    r.cash_from_operations_cr,
    r.capex_cr
FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
ORDER BY r.free_cash_flow_cr DESC
LIMIT 10;


-- ============================================================
-- QUERY 17
-- HIGHEST CASH FROM OPERATIONS
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.cash_from_operations_cr,
    r.free_cash_flow_cr
FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
ORDER BY r.cash_from_operations_cr DESC
LIMIT 10;


-- ============================================================
-- QUERY 18
-- HIGHEST EPS COMPANIES
-- ============================================================

WITH ranked_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id, p.year
            ORDER BY p.id DESC
        ) AS rn
    FROM profitandloss p
    WHERE p.year IS NOT NULL
),
latest_pl AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.company_id
            ORDER BY CAST(p.year AS REAL) DESC, p.id DESC
        ) AS latest_rn
    FROM ranked_pl p
    WHERE p.rn = 1
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.eps,
    p.net_profit,
    p.sales
FROM latest_pl p
JOIN companies c
    ON c.id = p.company_id
WHERE p.latest_rn = 1
  AND p.eps IS NOT NULL
ORDER BY p.eps DESC
LIMIT 10;


-- ============================================================
-- QUERY 19
-- BENCHMARK COMPANIES IN PEER GROUPS
-- ============================================================

SELECT
    peer_group_name,
    COUNT(*) AS company_count,
    SUM(
        CASE
            WHEN is_benchmark = 1 THEN 1
            ELSE 0
        END
    ) AS benchmark_count
FROM peer_groups
GROUP BY peer_group_name
ORDER BY company_count DESC;


-- ============================================================
-- QUERY 20
-- STOCK PRICE SUMMARY BY COMPANY
-- ============================================================

SELECT
    s.company_id,
    c.company_name,
    COUNT(*) AS price_records,
    MIN(s.date) AS first_price_date,
    MAX(s.date) AS latest_price_date,
    MIN(s.low_price) AS minimum_price,
    MAX(s.high_price) AS maximum_price,
    ROUND(AVG(s.close_price), 2) AS average_close_price
FROM stock_prices s
JOIN companies c
    ON c.id = s.company_id
GROUP BY
    s.company_id,
    c.company_name
ORDER BY average_close_price DESC;


-- ============================================================
-- QUERY 21
-- COMPANY FINANCIAL HEALTH SCORE
--
-- Score components:
--   ROE > 15%          = +1
--   Net margin > 10%   = +1
--   Debt/equity < 1    = +1
--   Positive FCF       = +1
--   Positive CFO       = +1
--
-- Maximum score = 5
-- ============================================================

WITH ranked_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id, r.year
            ORDER BY r.id DESC
        ) AS rn
    FROM financial_ratios r
    WHERE r.year IS NOT NULL
),
latest_ratios AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.company_id
            ORDER BY CAST(r.year AS REAL) DESC, r.id DESC
        ) AS latest_rn
    FROM ranked_ratios r
    WHERE r.rn = 1
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.return_on_equity_pct,
    r.net_profit_margin_pct,
    r.debt_to_equity,
    r.free_cash_flow_cr,
    r.cash_from_operations_cr,

    (
        CASE
            WHEN r.return_on_equity_pct > 15 THEN 1
            ELSE 0
        END
        +
        CASE
            WHEN r.net_profit_margin_pct > 10 THEN 1
            ELSE 0
        END
        +
        CASE
            WHEN r.debt_to_equity < 1 THEN 1
            ELSE 0
        END
        +
        CASE
            WHEN r.free_cash_flow_cr > 0 THEN 1
            ELSE 0
        END
        +
        CASE
            WHEN r.cash_from_operations_cr > 0 THEN 1
            ELSE 0
        END
    ) AS financial_health_score

FROM latest_ratios r
JOIN companies c
    ON c.id = r.company_id
WHERE r.latest_rn = 1
ORDER BY
    financial_health_score DESC,
    r.return_on_equity_pct DESC,
    r.net_profit_margin_pct DESC
LIMIT 20;