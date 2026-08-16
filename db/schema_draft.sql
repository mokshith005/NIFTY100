-- NIFTY100 Sprint 1
-- Preliminary schema draft
--
-- IMPORTANT:
-- Assignment states 10 tables but lists 11 table names.
-- Final schema.sql will be created after this is clarified
-- or after the source files reveal the intended structure.

PRAGMA foreign_keys = ON;


-- ============================================================
-- 1. COMPANIES
-- ============================================================

CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL
);


-- ============================================================
-- 2. PROFIT AND LOSS
-- ============================================================

CREATE TABLE IF NOT EXISTS profitandloss (
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    sales REAL,
    operating_profit REAL,
    opm REAL,
    profit_before_tax REAL,
    tax REAL,
    net_profit REAL,
    eps REAL,

    PRIMARY KEY (company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 3. BALANCE SHEET
-- ============================================================

CREATE TABLE IF NOT EXISTS balancesheet (
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    total_assets REAL,
    total_liabilities REAL,
    equity REAL,
    borrowings REAL,
    cash REAL,

    PRIMARY KEY (company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 4. CASH FLOW
-- ============================================================

CREATE TABLE IF NOT EXISTS cashflow (
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    operating_cash_flow REAL,
    investing_cash_flow REAL,
    financing_cash_flow REAL,
    net_cash_flow REAL,

    PRIMARY KEY (company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 5. ANALYSIS
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis (
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    metric TEXT,
    value REAL,

    PRIMARY KEY (company_id, year, metric),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 6. DOCUMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,

    document_type TEXT,
    document_url TEXT,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 7. PROS AND CONS
-- ============================================================

CREATE TABLE IF NOT EXISTS prosandcons (
    company_id INTEGER NOT NULL,

    item_type TEXT NOT NULL,
    description TEXT,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 8. SECTORS
-- ============================================================

CREATE TABLE IF NOT EXISTS sectors (
    sector_id INTEGER PRIMARY KEY,
    sector_name TEXT NOT NULL UNIQUE
);


-- ============================================================
-- 9. STOCK PRICES
-- ============================================================

CREATE TABLE IF NOT EXISTS stock_prices (
    company_id INTEGER NOT NULL,
    price_date TEXT NOT NULL,

    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,

    PRIMARY KEY (company_id, price_date),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 10. FINANCIAL RATIOS
-- ============================================================

CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    opm REAL,
    net_margin REAL,
    roe REAL,
    roce REAL,
    debt_equity REAL,

    PRIMARY KEY (company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
);


-- ============================================================
-- 11. PEER GROUPS
-- ============================================================

CREATE TABLE IF NOT EXISTS peer_groups (
    peer_group_id INTEGER PRIMARY KEY,

    company_id INTEGER NOT NULL,
    peer_company_id INTEGER NOT NULL,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id),

    FOREIGN KEY (peer_company_id)
        REFERENCES companies(company_id)
);