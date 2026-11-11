"""Day 08 verification — spot-check computed ratios in financial_ratios table."""
import sqlite3

conn = sqlite3.connect("data/nifty100.db")
c = conn.cursor()

print("=" * 70)
print("TABLE ROW COUNT")
c.execute("SELECT COUNT(*) FROM financial_ratios")
print(f"  financial_ratios rows: {c.fetchone()[0]}")

print("\nCOMPANIES WITH COMPUTED DATA")
c.execute("SELECT COUNT(DISTINCT company_id) FROM financial_ratios WHERE net_profit_margin_pct IS NOT NULL")
print(f"  Companies with NPM: {c.fetchone()[0]}")

print("\nTCS — latest 3 years (profitability)")
c.execute("""
    SELECT year, net_profit_margin_pct, return_on_equity_pct,
           return_on_capital_employed_pct, return_on_assets_pct
    FROM financial_ratios WHERE company_id='TCS'
    ORDER BY year DESC LIMIT 3
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nTCS — latest year (leverage & efficiency)")
c.execute("""
    SELECT year, debt_to_equity, interest_coverage, asset_turnover,
           free_cash_flow_cr, capex_cr, cfo_quality_score
    FROM financial_ratios WHERE company_id='TCS'
    ORDER BY year DESC LIMIT 1
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nTCS — CAGR metrics (latest year only)")
c.execute("""
    SELECT year, revenue_cagr_1y, revenue_cagr_3y, revenue_cagr_5y,
           pat_cagr_1y, pat_cagr_3y, pat_cagr_5y,
           eps_cagr_1y, eps_cagr_3y, eps_cagr_5y
    FROM financial_ratios WHERE company_id='TCS'
    AND revenue_cagr_1y IS NOT NULL
    ORDER BY year DESC LIMIT 1
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nHDFCBANK — OPM/ROCE should be NULL (Financials carve-out)")
c.execute("""
    SELECT year, operating_profit_margin_pct, return_on_capital_employed_pct,
           return_on_assets_pct, debt_to_equity
    FROM financial_ratios WHERE company_id='HDFCBANK'
    ORDER BY year DESC LIMIT 3
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nJIOFIN — only 1Y CAGR should be non-null")
c.execute("""
    SELECT year, revenue_cagr_1y, revenue_cagr_3y, revenue_cagr_5y,
           revenue_cagr_10y
    FROM financial_ratios WHERE company_id='JIOFIN'
    ORDER BY year DESC LIMIT 2
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nTCS — interest_coverage (debt-free check)")
c.execute("""
    SELECT year, total_debt_cr, interest_coverage
    FROM financial_ratios WHERE company_id='TCS'
    ORDER BY year DESC LIMIT 3
""")
for r in c.fetchall():
    print(f"  {r}")

print("\nNULL counts for key columns")
for col in ["net_profit_margin_pct", "return_on_equity_pct", "free_cash_flow_cr", "revenue_cagr_5y"]:
    c.execute(f"SELECT COUNT(*) FROM financial_ratios WHERE {col} IS NOT NULL")
    print(f"  {col}: {c.fetchone()[0]} non-null rows")

conn.close()
print("\nDone.")
