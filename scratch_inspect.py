"""Quick inspection script for Day 08 schema understanding."""
import sqlite3

conn = sqlite3.connect("data/nifty100.db")
c = conn.cursor()

# TCS P&L sample
print("=== TCS P&L (5 rows) ===")
c.execute("""SELECT company_id, year, sales, operating_profit, net_profit,
             interest, other_income, eps, dividend_payout
             FROM profitandloss WHERE company_id='TCS' ORDER BY year LIMIT 5""")
for r in c.fetchall():
    print(r)

# TCS BS sample
print("\n=== TCS Balance Sheet (5 rows) ===")
c.execute("""SELECT company_id, year, equity_capital, reserves, borrowings,
             other_liabilities, total_assets, fixed_assets, other_asset
             FROM balancesheet WHERE company_id='TCS' ORDER BY year LIMIT 5""")
for r in c.fetchall():
    print(r)

# TCS CF sample
print("\n=== TCS Cash Flow (5 rows) ===")
c.execute("""SELECT company_id, year, operating_activity, investing_activity,
             financing_activity, net_cash_flow
             FROM cashflow WHERE company_id='TCS' ORDER BY year LIMIT 5""")
for r in c.fetchall():
    print(r)

# financial_ratios columns
print("\n=== financial_ratios existing columns (sample ABB) ===")
c.execute("""SELECT * FROM financial_ratios WHERE company_id='ABB' LIMIT 3""")
for r in c.fetchall():
    print(r)

# Years for JIOFIN
print("\n=== JIOFIN years ===")
c.execute("SELECT year FROM profitandloss WHERE company_id='JIOFIN' ORDER BY year")
for r in c.fetchall():
    print(r)

conn.close()
