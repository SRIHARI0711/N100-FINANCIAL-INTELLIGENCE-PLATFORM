-- ============================================================================
-- N100 FINANCIAL INTELLIGENCE PLATFORM
-- SQLite Database Schema Definition
-- Enforces Foreign Key constraints and Unique composite indices
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. COMPANIES (Master Company Reference)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(12) PRIMARY KEY,
    company_logo TEXT,
    company_name VARCHAR(255) NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value NUMERIC,
    book_value NUMERIC,
    roce_percentage NUMERIC,
    roe_percentage NUMERIC
);

-- ----------------------------------------------------------------------------
-- 2. PROFIT AND LOSS (Annual P&L Statements)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year VARCHAR(7) NOT NULL,
    sales NUMERIC,
    expenses NUMERIC,
    operating_profit NUMERIC,
    opm_percentage NUMERIC,
    other_income NUMERIC,
    interest NUMERIC,
    depreciation NUMERIC,
    profit_before_tax NUMERIC,
    tax_percentage NUMERIC,
    net_profit NUMERIC,
    eps NUMERIC,
    dividend_payout NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, year)
);

-- ----------------------------------------------------------------------------
-- 3. BALANCE SHEET (Annual Balance Sheet Statements)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year VARCHAR(7) NOT NULL,
    equity_capital NUMERIC,
    reserves NUMERIC,
    borrowings NUMERIC,
    other_liabilities NUMERIC,
    total_liabilities NUMERIC,
    fixed_assets NUMERIC,
    cwip NUMERIC,
    investments NUMERIC,
    other_asset NUMERIC,
    total_assets NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, year)
);

-- ----------------------------------------------------------------------------
-- 4. CASH FLOW (Annual Cash Flow Statements)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year VARCHAR(7) NOT NULL,
    operating_activity NUMERIC,
    investing_activity NUMERIC,
    financing_activity NUMERIC,
    net_cash_flow NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, year)
);

-- ----------------------------------------------------------------------------
-- 5. ANALYSIS (Pre-computed Multi-period Growth Metrics)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 6. DOCUMENTS (Annual Report Filings & BSE Links)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year INTEGER NOT NULL,
    annual_report TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 7. PROS AND CONS (Qualitative Investment Highlights & Risks)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- 8. SECTORS (Company Sector & Sub-sector Taxonomy)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    broad_sector VARCHAR(100) NOT NULL,
    sub_sector VARCHAR(100),
    index_weight_pct NUMERIC,
    market_cap_category VARCHAR(50),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id)
);

-- ----------------------------------------------------------------------------
-- 9. STOCK PRICES (Monthly Historical OHLCV Series)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    date VARCHAR(10) NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume INTEGER,
    adjusted_close NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, date)
);

-- ----------------------------------------------------------------------------
-- 10. MARKET CAP (Annual Valuation Multiples)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market_cap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year INTEGER NOT NULL,
    market_cap_crore NUMERIC,
    enterprise_value_crore NUMERIC,
    pe_ratio NUMERIC,
    pb_ratio NUMERIC,
    ev_ebitda NUMERIC,
    dividend_yield_pct NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, year)
);

-- ----------------------------------------------------------------------------
-- 11. FINANCIAL RATIOS (Computed / Pre-computed KPI Table)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(12) NOT NULL,
    year VARCHAR(7) NOT NULL,
    net_profit_margin_pct NUMERIC,
    operating_profit_margin_pct NUMERIC,
    return_on_equity_pct NUMERIC,
    debt_to_equity NUMERIC,
    interest_coverage NUMERIC,
    asset_turnover NUMERIC,
    free_cash_flow_cr NUMERIC,
    capex_cr NUMERIC,
    earnings_per_share NUMERIC,
    book_value_per_share NUMERIC,
    dividend_payout_ratio_pct NUMERIC,
    total_debt_cr NUMERIC,
    cash_from_operations_cr NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (company_id, year)
);

-- ----------------------------------------------------------------------------
-- 12. PEER GROUPS (Industry Peer Groups & Benchmarks)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS peer_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_group_name VARCHAR(100) NOT NULL,
    company_id VARCHAR(12) NOT NULL,
    is_benchmark BOOLEAN DEFAULT 0,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE (peer_group_name, company_id)
);

-- ----------------------------------------------------------------------------
-- INDEXES FOR QUERY OPTIMISATION
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pl_company_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_bs_company_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cf_company_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_docs_company_year ON documents(company_id, year);
CREATE INDEX IF NOT EXISTS idx_stock_prices_company_date ON stock_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_market_cap_company_year ON market_cap(company_id, year);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_company_year ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_sectors_broad ON sectors(broad_sector);
CREATE INDEX IF NOT EXISTS idx_peer_groups_name ON peer_groups(peer_group_name);
