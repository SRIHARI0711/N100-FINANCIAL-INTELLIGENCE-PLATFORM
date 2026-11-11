"""
N100 Financial Intelligence Platform — Sprint 2, Day 10
CAGR Engine: Multi-period Compound Annual Growth Rates with edge-case detection.

Computes 3Y, 5Y, and 10Y CAGRs for:
  - Revenue (sales)
  - PAT (net_profit)
  - EPS (earnings per share)

Handles all 6 CAGR edge cases:
  1. Positive + Positive: Compute normally
  2. Positive + Negative: Return None with flag DECLINE_TO_LOSS
  3. Negative + Positive: Return None with flag TURNAROUND
  4. Negative + Negative: Return None with flag BOTH_NEGATIVE
  5. Zero base: Return None with flag ZERO_BASE
  6. Less than n years of data: Return None with flag INSUFFICIENT
"""

from __future__ import annotations

import logging
import math
import sqlite3
import sys
from pathlib import Path
from typing import NamedTuple

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "nifty100.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Edge-case Flags
# ---------------------------------------------------------------------------
FLAG_DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
FLAG_TURNAROUND = "TURNAROUND"
FLAG_BOTH_NEGATIVE = "BOTH_NEGATIVE"
FLAG_ZERO_BASE = "ZERO_BASE"
FLAG_INSUFFICIENT = "INSUFFICIENT"
FLAG_NORMAL = None

# Companies with insufficient history for multi-year CAGR (< 3 years)
CAGR_EXCLUDE: set[str] = {"JIOFIN"}

# Standard CAGR windows
CAGR_WINDOWS: list[int] = [3, 5, 10]


class CAGRResult(NamedTuple):
    """Container for CAGR computation result and status flag."""
    value: float | None
    flag: str | None


# ---------------------------------------------------------------------------
# Core CAGR Formulas
# ---------------------------------------------------------------------------


def calculate_cagr(
    start_val: float | None,
    end_val: float | None,
    years: int,
) -> CAGRResult:
    """
    Compute CAGR with comprehensive 6 edge-case classification:
      - Positive + Positive: compute ((end/start)^(1/years) - 1) * 100, flag=None
      - Positive + Negative: return None, flag=DECLINE_TO_LOSS
      - Negative + Positive: return None, flag=TURNAROUND
      - Negative + Negative: return None, flag=BOTH_NEGATIVE
      - Zero base (start=0): return None, flag=ZERO_BASE
      - Insufficient data (None/NaN/years<=0): return None, flag=INSUFFICIENT
    """
    # Edge case 6: Insufficient data or invalid years
    if years is None or years <= 0:
        return CAGRResult(None, FLAG_INSUFFICIENT)
    if start_val is None or end_val is None:
        return CAGRResult(None, FLAG_INSUFFICIENT)
    if (isinstance(start_val, float) and math.isnan(start_val)) or (
        isinstance(end_val, float) and math.isnan(end_val)
    ):
        return CAGRResult(None, FLAG_INSUFFICIENT)

    # Edge case 5: Zero base
    if start_val == 0:
        return CAGRResult(None, FLAG_ZERO_BASE)

    # Edge case 4: Both negative
    if start_val < 0 and end_val < 0:
        return CAGRResult(None, FLAG_BOTH_NEGATIVE)

    # Edge case 3: Turnaround (Negative -> Positive)
    if start_val < 0 and end_val >= 0:
        return CAGRResult(None, FLAG_TURNAROUND)

    # Edge case 2: Decline to loss (Positive -> Negative or 0)
    if start_val > 0 and end_val < 0:
        return CAGRResult(None, FLAG_DECLINE_TO_LOSS)

    # Edge case 1: Positive + Positive -> Compute normally
    try:
        ratio = end_val / start_val
        if ratio <= 0:
            return CAGRResult(None, FLAG_DECLINE_TO_LOSS)
        cagr_val = ((ratio ** (1.0 / years)) - 1.0) * 100.0
        return CAGRResult(round(cagr_val, 4), FLAG_NORMAL)
    except (ZeroDivisionError, OverflowError, ValueError):
        return CAGRResult(None, FLAG_INSUFFICIENT)


def cagr(start_val: float | None, end_val: float | None, years: int) -> float | None:
    """
    Standard CAGR formula returning float or None.
    Backward-compatible interface for pure math callers.
    """
    res = calculate_cagr(start_val, end_val, years)
    return res.value


# ---------------------------------------------------------------------------
# Multi-period series computation
# ---------------------------------------------------------------------------


def compute_series_cagr(
    series: list[tuple[str, float | None]],  # [(year_str, val), ...] sorted ascending
    target_years: list[int] | None = None,
    company_id: str = "",
) -> dict[str, CAGRResult]:
    """
    Compute CAGRs for specified windows from a sorted (year, value) time series.
    Returns dict keyed by:
      - 'cagr_3y': CAGRResult(value, flag)
      - 'cagr_5y': CAGRResult(value, flag)
      - 'cagr_10y': CAGRResult(value, flag)
    """
    if target_years is None:
        target_years = CAGR_WINDOWS

    results: dict[str, CAGRResult] = {}

    for yrs in target_years:
        key = f"cagr_{yrs}y"

        # Explicit exclusion check (e.g. JIOFIN < 3 years history)
        if company_id in CAGR_EXCLUDE and yrs > 1:
            results[key] = CAGRResult(None, FLAG_INSUFFICIENT)
            continue

        # Filter out rows with None values to find contiguous valid history
        valid_rows = [(y, v) for y, v in series if v is not None]

        # Need at least yrs + 1 data points to compute an n-year CAGR
        if len(valid_rows) <= yrs:
            results[key] = CAGRResult(None, FLAG_INSUFFICIENT)
            continue

        end_val = valid_rows[-1][1]
        start_val = valid_rows[-(yrs + 1)][1]

        results[key] = calculate_cagr(start_val, end_val, yrs)

    return results


# ---------------------------------------------------------------------------
# Database Schema Migration & Update
# ---------------------------------------------------------------------------

_CAGR_COLUMNS: list[tuple[str, str]] = [
    # 3-year, 5-year, 10-year Revenue CAGR + flags
    ("revenue_cagr_3y", "NUMERIC"),
    ("revenue_cagr_3y_flag", "VARCHAR(20)"),
    ("revenue_cagr_3yr_flag", "VARCHAR(20)"),
    ("revenue_cagr_5y", "NUMERIC"),
    ("revenue_cagr_5y_flag", "VARCHAR(20)"),
    ("revenue_cagr_5yr_flag", "VARCHAR(20)"),
    ("revenue_cagr_10y", "NUMERIC"),
    ("revenue_cagr_10y_flag", "VARCHAR(20)"),
    ("revenue_cagr_10yr_flag", "VARCHAR(20)"),
    # 3-year, 5-year, 10-year PAT CAGR + flags
    ("pat_cagr_3y", "NUMERIC"),
    ("pat_cagr_3y_flag", "VARCHAR(20)"),
    ("pat_cagr_3yr_flag", "VARCHAR(20)"),
    ("pat_cagr_5y", "NUMERIC"),
    ("pat_cagr_5y_flag", "VARCHAR(20)"),
    ("pat_cagr_5yr_flag", "VARCHAR(20)"),
    ("pat_cagr_10y", "NUMERIC"),
    ("pat_cagr_10y_flag", "VARCHAR(20)"),
    ("pat_cagr_10yr_flag", "VARCHAR(20)"),
    # 3-year, 5-year, 10-year EPS CAGR + flags
    ("eps_cagr_3y", "NUMERIC"),
    ("eps_cagr_3y_flag", "VARCHAR(20)"),
    ("eps_cagr_3yr_flag", "VARCHAR(20)"),
    ("eps_cagr_5y", "NUMERIC"),
    ("eps_cagr_5y_flag", "VARCHAR(20)"),
    ("eps_cagr_5yr_flag", "VARCHAR(20)"),
    ("eps_cagr_10y", "NUMERIC"),
    ("eps_cagr_10y_flag", "VARCHAR(20)"),
    ("eps_cagr_10yr_flag", "VARCHAR(20)"),
]


def migrate_cagr_schema(conn: sqlite3.Connection) -> None:
    """Ensure all CAGR and flag columns exist in financial_ratios table."""
    cur = conn.execute("PRAGMA table_info(financial_ratios)")
    existing = {r["name"] for r in cur.fetchall()}
    for col_name, col_type in _CAGR_COLUMNS:
        if col_name not in existing:
            conn.execute(
                f"ALTER TABLE financial_ratios ADD COLUMN {col_name} {col_type}"
            )
            log.info("  Schema migration: added column %s", col_name)
    conn.commit()


def compute_and_update_all_cagrs(conn: sqlite3.Connection) -> int:
    """
    Computes Revenue, PAT, and EPS CAGRs (3Y, 5Y, 10Y) with flags
    and updates the latest available year row for each company in financial_ratios.
    Returns number of companies updated.
    """
    migrate_cagr_schema(conn)

    # 1. Load historical series from profitandloss
    sql = """
    SELECT company_id, year, sales, net_profit, eps
    FROM profitandloss
    ORDER BY company_id, year ASC
    """
    cur = conn.execute(sql)
    rows_by_company: dict[str, list[sqlite3.Row]] = {}
    for r in cur.fetchall():
        rows_by_company.setdefault(r["company_id"], []).append(r)

    updated_count = 0

    for cid, rows in rows_by_company.items():
        if not rows:
            continue

        latest_year = rows[-1]["year"]

        rev_series = [(r["year"], r["sales"]) for r in rows]
        pat_series = [(r["year"], r["net_profit"]) for r in rows]
        eps_series = [(r["year"], r["eps"]) for r in rows]

        rev_cagr = compute_series_cagr(rev_series, CAGR_WINDOWS, cid)
        pat_cagr = compute_series_cagr(pat_series, CAGR_WINDOWS, cid)
        eps_cagr = compute_series_cagr(eps_series, CAGR_WINDOWS, cid)

        update_fields: dict[str, float | str | None] = {}

        for yrs in CAGR_WINDOWS:
            k = f"cagr_{yrs}y"
            # Revenue
            update_fields[f"revenue_{k}"] = rev_cagr[k].value
            update_fields[f"revenue_{k}_flag"] = rev_cagr[k].flag
            update_fields[f"revenue_cagr_{yrs}yr_flag"] = rev_cagr[k].flag
            # PAT
            update_fields[f"pat_{k}"] = pat_cagr[k].value
            update_fields[f"pat_{k}_flag"] = pat_cagr[k].flag
            update_fields[f"pat_cagr_{yrs}yr_flag"] = pat_cagr[k].flag
            # EPS
            update_fields[f"eps_{k}"] = eps_cagr[k].value
            update_fields[f"eps_{k}_flag"] = eps_cagr[k].flag
            update_fields[f"eps_cagr_{yrs}yr_flag"] = eps_cagr[k].flag

        set_clauses = [f"{col} = ?" for col in update_fields]
        values = list(update_fields.values()) + [cid, latest_year]

        sql_update = f"""
        UPDATE financial_ratios
        SET {', '.join(set_clauses)}
        WHERE company_id = ? AND year = ?
        """
        conn.execute(sql_update, values)
        updated_count += 1

    conn.commit()
    log.info("CAGR Engine: Updated CAGR metrics & flags for %d companies", updated_count)
    return updated_count


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    count = compute_and_update_all_cagrs(conn)
    conn.close()
    print(f"CAGR Engine finished successfully. {count} companies updated.")
