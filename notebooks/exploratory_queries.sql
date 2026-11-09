-- ============================================================================
-- N100 FINANCIAL INTELLIGENCE PLATFORM
-- Exploratory SQL Queries (Sprint 1 Wrap-up)
-- Database: data/nifty100.db
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Table Row Counts Across All 12 Database Tables
-- Verifies complete population of all tables in the unified warehouse.
-- ----------------------------------------------------------------------------
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL
SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- ----------------------------------------------------------------------------
-- 2. Foreign Key Relational Integrity Verification
-- Ensures PRAGMA foreign_key_check returns zero rows.
-- ----------------------------------------------------------------------------
PRAGMA foreign_keys = ON;
PRAGMA foreign_key_check;

-- ----------------------------------------------------------------------------
-- 3. Company Distribution by Broad Sector & Sub-Sector
-- Displays count of companies and total estimated index weight per sector.
-- ----------------------------------------------------------------------------
SELECT 
    broad_sector,
    COUNT(company_id) AS total_companies,
    ROUND(SUM(index_weight_pct), 2) AS total_index_weight_pct
FROM sectors
GROUP BY broad_sector
ORDER BY total_companies DESC;

-- ----------------------------------------------------------------------------
-- 4. Annual Statement Year Coverage Distribution per Company
-- Measures how many historical years of P&L, Balance Sheet, and CF each firm has.
-- ----------------------------------------------------------------------------
SELECT 
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT p.year) AS pl_years,
    COUNT(DISTINCT b.year) AS bs_years,
    COUNT(DISTINCT f.year) AS cf_years
FROM companies c
LEFT JOIN profitandloss p ON c.id = p.company_id
LEFT JOIN balancesheet b ON c.id = b.company_id
LEFT JOIN cashflow f ON c.id = f.company_id
GROUP BY c.id, c.company_name
ORDER BY pl_years ASC, c.id ASC
LIMIT 15;

-- ----------------------------------------------------------------------------
-- 5. Companies Flagged for Coverage < 5 Years (Rule DQ-16)
-- Flags newly listed / demerged entities for CAGR exclusion.
-- ----------------------------------------------------------------------------
SELECT 
    c.id AS company_id,
    c.company_name,
    COUNT(DISTINCT p.year) AS available_pl_years
FROM companies c
JOIN profitandloss p ON c.id = p.company_id
GROUP BY c.id, c.company_name
HAVING available_pl_years < 5;

-- ----------------------------------------------------------------------------
-- 6. Top 10 Revenue Generators in Latest Fiscal Year (2024-03)
-- Revenue leaders across the Nifty 100 universe in ₹ Crore.
-- ----------------------------------------------------------------------------
SELECT 
    p.company_id,
    c.company_name,
    s.broad_sector,
    p.sales AS revenue_crore,
    p.operating_profit AS op_profit_crore,
    p.net_profit AS pat_crore
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
JOIN sectors s ON c.id = s.company_id
WHERE p.year = '2024-03'
ORDER BY p.sales DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 7. Balance Sheet Equilibrium Check (DQ-04 & DQ-15)
-- Checks whether any record has Total Assets != Total Liabilities.
-- ----------------------------------------------------------------------------
SELECT 
    company_id,
    year,
    total_assets,
    total_liabilities,
    (total_assets - total_liabilities) AS delta
FROM balancesheet
WHERE total_assets != total_liabilities
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 8. Cash Flow Generation vs Net Profit Health Check
-- Compares Cash Flow from Operations (CFO) against Net Profit (PAT) for latest year.
-- ----------------------------------------------------------------------------
SELECT 
    p.company_id,
    p.year,
    p.net_profit,
    f.operating_activity AS cfo,
    f.net_cash_flow,
    ROUND(f.operating_activity / NULLIF(p.net_profit, 0), 2) AS cfo_to_pat_ratio
FROM profitandloss p
JOIN cashflow f ON p.company_id = f.company_id AND p.year = f.year
WHERE p.year = '2024-03' AND p.net_profit > 1000
ORDER BY cfo_to_pat_ratio DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 9. Stock Price Time-Series Horizon & Volume Audit
-- Checks start date, end date, total months, and average volume per company.
-- ----------------------------------------------------------------------------
SELECT 
    company_id,
    MIN(date) AS start_date,
    MAX(date) AS end_date,
    COUNT(date) AS total_months,
    ROUND(AVG(volume) / 1000000.0, 2) AS avg_monthly_volume_millions
FROM stock_prices
GROUP BY company_id
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 10. Annual Report Filing Completeness (2015 to 2024)
-- Audits document links availability across the last 10 calendar years.
-- ----------------------------------------------------------------------------
SELECT 
    c.id,
    c.company_name,
    COUNT(d.year) AS available_annual_reports,
    (10 - COUNT(d.year)) AS missing_reports_in_decade
FROM companies c
LEFT JOIN documents d ON c.id = d.company_id AND d.year >= 2015
GROUP BY c.id, c.company_name
ORDER BY available_annual_reports ASC
LIMIT 10;
