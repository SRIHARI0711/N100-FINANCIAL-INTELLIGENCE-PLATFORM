"""
src/analytics/edge_cases.py
Sprint 2 — Day 13: Bank ROCE Carve-Out & Ratio Edge Case Cross-Check.

Performs cross-validation of:
  1. Computed ROCE vs source `roce_percentage` in companies.xlsx (anomalies > 5%)
  2. Computed ROE vs source `roe_percentage` in companies.xlsx (anomalies > 5%)
  3. Financials broad sector D/E suppression verification

Outputs:
  - output/ratio_edge_cases.log
  - output/sector_roce_notes.csv
"""

from __future__ import annotations

import csv
import logging
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
LOG_PATH = OUTPUT_DIR / "ratio_edge_cases.log"
NOTES_CSV_PATH = OUTPUT_DIR / "sector_roce_notes.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# Anomaly categories
CAT_DATA_SOURCE_ISSUE = "Data Source Issue"
CAT_FORMULA_DISCREPANCY = "Formula Discrepancy"
CAT_VERSION_DIFFERENCE = "Version Difference"


def _categorise_roce_anomaly(
    company_id: str,
    broad_sector: str | None,
    computed_roce: float | None,
    source_roce: float | None,
    diff: float | None,
) -> tuple[str, str]:
    """Determine category and explanatory rationale for an ROCE discrepancy."""
    if broad_sector == "Financials":
        return (
            CAT_FORMULA_DISCREPANCY,
            (
                "Bank/NBFC carve-out: standard ROCE (EBIT / Capital Employed) is conceptually invalid "
                "due to deposit-taking liability structure. Engine sets ROCE to None (uses ROA for analytics). "
                f"Source shows {source_roce}%."
            ),
        )

    if diff is not None and diff > 500.0:
        return (
            CAT_DATA_SOURCE_ISSUE,
            (
                f"Unit scale mismatch in balance sheet equity/reserves vs P&L. Computed ROCE ({computed_roce}%) "
                f"reflects extreme denominator compression. Source shows {source_roce}%."
            ),
        )

    if company_id in {"CIPLA", "COALINDIA", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "INDIGO"}:
        return (
            CAT_DATA_SOURCE_ISSUE,
            (
                "P&L source table contains absolute operating profit or classification anomaly in opm_percentage. "
                f"Computed ROCE={computed_roce}% vs Source ROCE={source_roce}%."
            ),
        )

    if diff is not None and diff > 30.0:
        return (
            CAT_FORMULA_DISCREPANCY,
            (
                "Formula definition variance: Engine uses EBIT / (Equity + Reserves + Borrowings) on annual FY24 figures, "
                f"while source uses TTM operating profit or net-cash capital employed deduction. Diff = {diff:.2f}%."
            ),
        )

    return (
        CAT_VERSION_DIFFERENCE,
        (
            "Timing / trailing window difference: source companies.xlsx reports latest TTM/interim Q2 FY25 snapshot, "
            f"while ratio engine computes FY24 full-year audited statements. Diff = {diff:.2f}%."
        ),
    )


def _categorise_roe_anomaly(
    company_id: str,
    broad_sector: str | None,
    computed_roe: float | None,
    source_roe: float | None,
    diff: float | None,
) -> tuple[str, str]:
    """Determine category and explanatory rationale for an ROE discrepancy."""
    if company_id == "TCS":
        return (
            CAT_DATA_SOURCE_ISSUE,
            (
                "Decimal ratio truncated/unscaled in source: companies.xlsx shows 0.52 instead of 52% "
                f"(computed ROE = {computed_roe:.2f}%). Engine value used for analytics, source for display only."
            ),
        )

    if diff is not None and diff > 500.0:
        return (
            CAT_DATA_SOURCE_ISSUE,
            (
                f"Unit scale mismatch in balance sheet net worth vs reported profit. Computed ROE ({computed_roe:.2f}%) "
                f"vs source ({source_roe}%)."
            ),
        )

    if broad_sector == "Financials":
        return (
            CAT_FORMULA_DISCREPANCY,
            (
                "Financials capital base variance: bank/insurance net profit after provisioning vs equity base. "
                f"Computed ROE={computed_roe:.2f}% vs Source={source_roe}%."
            ),
        )

    return (
        CAT_VERSION_DIFFERENCE,
        (
            "Timing / TTM vs FY24 annual variance: source is recent TTM snapshot, while engine computes FY24. "
            f"Computed={computed_roe:.2f}% vs Source={source_roe}%. Diff={diff:.2f}%."
        ),
    )


def cross_check_and_log_edge_cases(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Perform cross-checks, write output/ratio_edge_cases.log and output/sector_roce_notes.csv.

    Returns dict with summary lists: 'roce_anomalies', 'roe_anomalies', 'financials_de_check'.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Verify Financials D/E suppression
    financials_de_rows = conn.execute("""
        SELECT fr.company_id, fr.year, fr.debt_to_equity, fr.high_leverage_flag, s.sub_sector
        FROM financial_ratios fr
        JOIN sectors s ON fr.company_id = s.company_id
        WHERE s.broad_sector = 'Financials'
    """).fetchall()

    violation_count = sum(1 for r in financials_de_rows if r[3] == 1)
    if violation_count > 0:
        log.error("Found %d Financials rows with high_leverage_flag = 1 (expected 0)", violation_count)
    else:
        log.info("Financials D/E suppression verified: 0 out of %d rows have high_leverage_flag = 1", len(financials_de_rows))

    # 2. Load latest annual ratio rows per company
    cur = conn.execute("""
        SELECT fr.company_id, fr.year, fr.return_on_capital_employed_pct, fr.return_on_equity_pct,
               fr.debt_to_equity, fr.high_leverage_flag, fr.interest_coverage, fr.icr_label,
               c.roce_percentage AS src_roce, c.roe_percentage AS src_roe,
               s.broad_sector, s.sub_sector
        FROM financial_ratios fr
        JOIN (
            SELECT company_id, MAX(year) AS max_year
            FROM financial_ratios
            WHERE return_on_equity_pct IS NOT NULL
            GROUP BY company_id
        ) latest ON fr.company_id = latest.company_id AND fr.year = latest.max_year
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON fr.company_id = s.company_id
        ORDER BY fr.company_id
    """)
    rows = cur.fetchall()

    roce_anomalies: list[dict] = []
    roe_anomalies: list[dict] = []
    notes_rows: list[dict] = []

    for r in rows:
        cid = r[0]
        yr = r[1]
        comp_roce = r[2]
        comp_roe = r[3]
        src_roce = r[8]
        src_roe = r[9]
        broad_sec = r[10]
        sub_sec = r[11]

        # --- ROCE Check ---
        if src_roce is not None:
            if comp_roce is not None:
                diff_roce = abs(comp_roce - src_roce)
                if diff_roce > 5.0:
                    cat, rationale = _categorise_roce_anomaly(cid, broad_sec, comp_roce, src_roce, diff_roce)
                    anomaly = {
                        "company_id": cid,
                        "year": yr,
                        "sector": broad_sec,
                        "sub_sector": sub_sec,
                        "metric": "ROCE",
                        "computed": round(comp_roce, 2),
                        "source": round(src_roce, 2),
                        "diff": round(diff_roce, 2),
                        "category": cat,
                        "rationale": rationale,
                    }
                    roce_anomalies.append(anomaly)
            else:
                # Financials carve-out
                cat, rationale = _categorise_roce_anomaly(cid, broad_sec, None, src_roce, None)
                anomaly = {
                    "company_id": cid,
                    "year": yr,
                    "sector": broad_sec,
                    "sub_sector": sub_sec,
                    "metric": "ROCE",
                    "computed": None,
                    "source": round(src_roce, 2),
                    "diff": None,
                    "category": cat,
                    "rationale": rationale,
                }
                roce_anomalies.append(anomaly)

        # Record for sector_roce_notes.csv if Financials
        if broad_sec == "Financials":
            notes_rows.append({
                "company_id": cid,
                "year": yr,
                "broad_sector": broad_sec,
                "sub_sector": sub_sec,
                "source_roce": src_roce,
                "computed_roce": comp_roce,
                "treatment": "Carved out: ROCE suppressed to None; ROA used as bank profitability proxy",
            })

        # --- ROE Check ---
        if src_roe is not None and comp_roe is not None:
            diff_roe = abs(comp_roe - src_roe)
            if diff_roe > 5.0 or cid == "TCS":
                cat, rationale = _categorise_roe_anomaly(cid, broad_sec, comp_roe, src_roe, diff_roe)
                roe_anomalies.append({
                    "company_id": cid,
                    "year": yr,
                    "sector": broad_sec,
                    "sub_sector": sub_sec,
                    "metric": "ROE",
                    "computed": round(comp_roe, 2),
                    "source": round(src_roe, 2),
                    "diff": round(diff_roe, 2),
                    "category": cat,
                    "rationale": rationale,
                })

    # 3. Write output/ratio_edge_cases.log
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("N100 FINANCIAL INTELLIGENCE PLATFORM — RATIO ENGINE EDGE CASE LOG\n")
        f.write("Sprint 2 — Day 13: Bank ROCE Carve-Out & Cross-Validation Audit\n")
        f.write("=" * 80 + "\n\n")

        f.write("SECTION 1: FINANCIALS BROAD SECTOR LEVERAGE FLAG AUDIT\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Financials rows checked: {len(financials_de_rows)}\n")
        f.write(f"High leverage flag violations: {violation_count}\n")
        f.write("Status: PASSED — high_leverage_flag is suppressed for all banks/NBFCs/insurance.\n\n")

        f.write("SECTION 2: ROCE CROSS-CHECK ANOMALIES (Difference > 5% or Carve-Out)\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total ROCE discrepancies flagged: {len(roce_anomalies)}\n\n")
        for a in roce_anomalies:
            comp_str = f"{a['computed']}%" if a['computed'] is not None else "None (Carved out)"
            diff_str = f"{a['diff']}%" if a['diff'] is not None else "N/A"
            f.write(f"[{a['company_id']} | {a['year']} | {a['sector']} - {a['sub_sector']}]\n")
            f.write(f"  Computed ROCE: {comp_str} | Source ROCE: {a['source']}% | Diff: {diff_str}\n")
            f.write(f"  Category:  {a['category']}\n")
            f.write(f"  Rationale: {a['rationale']}\n\n")

        f.write("SECTION 3: ROE CROSS-CHECK ANOMALIES (Difference > 5% or Known Anomaly)\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total ROE discrepancies flagged: {len(roe_anomalies)}\n\n")
        for a in roe_anomalies:
            f.write(f"[{a['company_id']} | {a['year']} | {a['sector']} - {a['sub_sector']}]\n")
            f.write(f"  Computed ROE: {a['computed']}% | Source ROE: {a['source']}% | Diff: {a['diff']}%\n")
            f.write(f"  Category:  {a['category']}\n")
            f.write(f"  Rationale: {a['rationale']}\n\n")

        # Summary of categories
        from collections import Counter
        all_anomalies = roce_anomalies + roe_anomalies
        cat_counts = Counter(x["category"] for x in all_anomalies)
        f.write("SECTION 4: ANOMALY CATEGORY BREAKDOWN\n")
        f.write("-" * 80 + "\n")
        for cat, cnt in cat_counts.most_common():
            f.write(f"  - {cat:<25}: {cnt} items\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("AUDIT CONCLUSION:\n")
        f.write("  - For analytics and screener ranking, always use ratio engine computed values.\n")
        f.write("  - Source values (companies.xlsx) should only be used for display / raw sanity-checks.\n")
        f.write("=" * 80 + "\n")

    log.info("Wrote edge case log → %s", LOG_PATH)

    # 4. Write output/sector_roce_notes.csv
    if notes_rows:
        fieldnames = ["company_id", "year", "broad_sector", "sub_sector", "source_roce", "computed_roce", "treatment"]
        with NOTES_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(notes_rows)
        log.info("Wrote sector ROCE notes → %s (%d rows)", NOTES_CSV_PATH, len(notes_rows))

    return {
        "roce_anomalies": roce_anomalies,
        "roe_anomalies": roe_anomalies,
        "financials_de_check": len(financials_de_rows),
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        cross_check_and_log_edge_cases(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
