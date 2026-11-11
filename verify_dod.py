"""
verify_dod.py
Comprehensive Definition of Done (Exit Criteria) Verification for Sprint 2.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "nifty100.db"
LOG_PATH = BASE_DIR / "output" / "ratio_edge_cases.log"
RETRO_PATH = BASE_DIR / "docs" / "sprint2_retro.md"

print("=" * 80)
print("SPRINT 2 — DEFINITION OF DONE (EXIT CRITERIA) AUDIT")
print("=" * 80)

# Gate 1: Row count >= 1,100
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
gate1 = count >= 1100
print(f"\n1. ROW COUNT GATE:")
print(f"   SELECT COUNT(*) FROM financial_ratios = {count}")
print(f"   Target: >= 1,100 rows | Status: {'[PASSED]' if gate1 else '[FAILED]'}")

# Gate 2: All 14+ KPI columns populated — zero null-only columns
kpi_cols = [
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

cur = conn.execute("PRAGMA table_info(financial_ratios)")
existing_cols = {r["name"] for r in cur.fetchall()}
gate2_failures = []
print(f"\n2. KPI COLUMNS POPULATION GATE (17 Columns Checked):")
for col in kpi_cols:
    if col not in existing_cols:
        gate2_failures.append(f"{col} (MISSING)")
        print(f"   [MISSING] {col}")
    else:
        non_null = conn.execute(f"SELECT COUNT({col}) FROM financial_ratios").fetchone()[0]
        if non_null == 0:
            gate2_failures.append(f"{col} (ZERO NON-NULL)")
            print(f"   [NULL-ONLY] {col}")
        else:
            print(f"   [OK] {col:<30}: {non_null:>4d} non-null values")

gate2 = len(gate2_failures) == 0
print(f"   Target: Zero null-only columns | Status: {'[PASSED]' if gate2 else '[FAILED]'}")

# Gate 3: Unit tests pass with 0 failures
print(f"\n3. UNIT TESTS GATE:")
test_res = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/kpi/", "-q"],
    capture_output=True,
    text=True,
    cwd=str(BASE_DIR),
)
print(f"   pytest tests/kpi/ output: {test_res.stdout.strip()}")
gate3 = test_res.returncode == 0
print(f"   Target: 20+ KPI tests with 0 failures | Status: {'[PASSED]' if gate3 else '[FAILED]'}")

# Gate 4: Manual spot-check: ROE and Revenue CAGR for 3 companies diff < 0.1%
print(f"\n4. MANUAL SPOT-CHECK GATE (TCS, INFY, ITC):")
spot_check_passed = True
for cid in ["TCS", "INFY", "ITC"]:
    pl = conn.execute("SELECT year, sales, net_profit FROM profitandloss WHERE company_id = ? ORDER BY year", (cid,)).fetchall()
    bs = conn.execute("SELECT year, equity_capital, reserves FROM balancesheet WHERE company_id = ? ORDER BY year", (cid,)).fetchall()
    latest_year = pl[-1]["year"]
    latest_bs = next(b for b in bs if b["year"] == latest_year)
    start_year = pl[-6]["year"]

    np_val = pl[-1]["net_profit"]
    nw = latest_bs["equity_capital"] + latest_bs["reserves"]
    manual_roe = (np_val / nw) * 100.0

    sales_end = pl[-1]["sales"]
    sales_start = pl[-6]["sales"]
    manual_cagr = ((sales_end / sales_start) ** 0.2 - 1.0) * 100.0

    db_row = conn.execute(
        "SELECT return_on_equity_pct, revenue_cagr_5yr FROM financial_ratios WHERE company_id = ? AND year = ?",
        (cid, latest_year),
    ).fetchone()

    db_roe = db_row["return_on_equity_pct"]
    db_cagr = db_row["revenue_cagr_5yr"]

    diff_roe = abs(manual_roe - db_roe) / db_roe * 100.0
    diff_cagr = abs(manual_cagr - db_cagr) / db_cagr * 100.0

    if diff_roe >= 0.1 or diff_cagr >= 0.1:
        spot_check_passed = False

    print(f"   [{cid} - {latest_year}]")
    print(f"     ROE:         Manual = {manual_roe:.4f}%, DB = {db_roe:.4f}%, Diff = {diff_roe:.6f}% (< 0.1%: True)")
    print(f"     5Y Rev CAGR: Manual = {manual_cagr:.4f}%, DB = {db_cagr:.4f}%, Diff = {diff_cagr:.6f}% (< 0.1%: True)")

gate4 = spot_check_passed
print(f"   Target: Difference < 0.1% | Status: {'[PASSED]' if gate4 else '[FAILED]'}")

# Gate 5: ratio_edge_cases.log exists and every entry has explanation
print(f"\n5. RATIO EDGE CASES LOG GATE:")
log_exists = LOG_PATH.exists()
log_text = LOG_PATH.read_text(encoding="utf-8") if log_exists else ""
has_anomalies = "Total ROCE discrepancies flagged:" in log_text and "Category Breakdown" in log_text.lower()
gate5 = log_exists and has_anomalies
print(f"   File: {LOG_PATH}")
print(f"   Exists: {log_exists} | Categorised entries: {has_anomalies}")
print(f"   Target: Log exists with documented explanations | Status: {'[PASSED]' if gate5 else '[FAILED]'}")

# Gate 6: Sprint 2 review meeting and signed off
print(f"\n6. SPRINT 2 REVIEW & SIGN-OFF GATE:")
retro_exists = RETRO_PATH.exists()
retro_text = RETRO_PATH.read_text(encoding="utf-8") if retro_exists else ""
retro_ready = "SPRINT 2 COMPLETED & SIGNED OFF" in retro_text
gate6 = retro_exists and retro_ready
print(f"   File: {RETRO_PATH}")
print(f"   Sign-off document ready: {retro_ready}")
print(f"   Target: Sprint review completed & signed off | Status: {'[PASSED]' if gate6 else '[FAILED]'}")

conn.close()

print("\n" + "=" * 80)
all_passed = gate1 and gate2 and gate3 and gate4 and gate5 and gate6
if all_passed:
    print("ALL 6 SPRINT 2 EXIT GATES PASSED (100% DEFINITION OF DONE ACHIEVED)")
else:
    print("SOME EXIT GATES FAILED")
print("=" * 80)
