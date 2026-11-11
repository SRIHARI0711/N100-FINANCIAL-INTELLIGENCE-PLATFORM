"""
src/analytics/cashflow_kpis.py
N100 Financial Intelligence Platform — Sprint 2, Day 11 Deliverable
Cash Flow KPIs: CFO Quality, CapEx Intensity, FCF Conversion, and Capital Allocation.

KPIs:
  - Free Cash Flow (FCF) = operating_activity + investing_activity (negative allowed)
  - CapEx = abs(investing_activity)
  - CFO Quality Score (single-year & 5-year rolling average)
  - CapEx Intensity & Classification (Asset Light, Moderate, Capital Intensive)
  - FCF Conversion Rate = FCF / operating_profit * 100
  - Capital Allocation 8-Pattern Classifier based on sign of (CFO, CFI, CFF)
"""

from __future__ import annotations

import csv
import logging
import math
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_CSV = OUTPUT_DIR / "capital_allocation.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# CFO/PAT threshold to distinguish Shareholder Returns from Reinvestor
SHAREHOLDER_RETURNS_THRESHOLD = 1.0

# Pattern map: (cfo_sign, cfi_sign, cff_sign) -> pattern label
_PATTERN_MAP: dict[tuple[int, int, int], str] = {
    (1, -1, -1): "Reinvestor",  # May upgrade to "Shareholder Returns" if avg CFO/PAT > 1.0
    (1, 1, -1): "Liquidating Assets",
    (-1, 1, 1): "Distress Signal",
    (-1, -1, 1): "Growth Funded by Debt",
    (1, 1, 1): "Cash Accumulator",
    (-1, -1, -1): "Pre-Revenue",
    (1, -1, 1): "Mixed",
}


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Return numerator / denominator, or None if denominator is 0 / None / NaN."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0 or (isinstance(denominator, float) and math.isnan(denominator)):
        return None
    if isinstance(numerator, float) and math.isnan(numerator):
        return None
    return numerator / denominator


def _pct(ratio: float | None) -> float | None:
    """Multiply by 100 to convert ratio -> percentage."""
    return None if ratio is None else ratio * 100.0


def _sign(value: float | None) -> int | None:
    """Return +1, -1, or 0 for sign. None if value is None."""
    if value is None:
        return None
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Core Cash Flow KPIs
# ---------------------------------------------------------------------------


def free_cash_flow(
    operating_activity: float | None,
    investing_activity: float | None,
) -> float | None:
    """FCF = operating_activity + investing_activity.

    investing_activity is typically negative (cash outflow for capex).
    Adding it to CFO gives net free cash flow. Negative values are allowed.
    """
    if operating_activity is None:
        return None
    inv = investing_activity or 0.0
    return operating_activity + inv


def capex(investing_activity: float | None) -> float | None:
    """CapEx proxy = abs(investing_activity).
    Returns None if investing_activity is None.
    """
    if investing_activity is None:
        return None
    return abs(investing_activity)


def cfo_quality_score(
    operating_activity: float | None,
    net_profit: float | None,
) -> float | None:
    """Single-year CFO Quality Score = operating_activity / net_profit.
    Returns None if net_profit is None or 0.
    """
    return _safe_div(operating_activity, net_profit)


def cfo_quality_score_5yr(
    cfo_series: list[float | None],
    pat_series: list[float | None],
) -> float | None:
    """CFO Quality Score averaged over up to 5 historical years.
    Returns None if no valid pairs exist.
    """
    ratios: list[float] = []
    for cfo_val, pat_val in zip(cfo_series, pat_series):
        ratio = _safe_div(cfo_val, pat_val)
        if ratio is not None:
            ratios.append(ratio)
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def cfo_quality_label(score: float | None) -> str | None:
    """Classify CFO Quality Score:
      > 1.0   -> 'High Quality'
      0.5–1.0 -> 'Moderate'
      < 0.5   -> 'Accrual Risk'
    """
    if score is None:
        return None
    if score > 1.0:
        return "High Quality"
    if score >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(
    investing_activity: float | None,
    sales: float | None,
) -> float | None:
    """CapEx Intensity = |investing_activity| / sales * 100.
    Returns None if sales <= 0 or sales is None.
    """
    if sales is None or sales <= 0:
        return None
    capex_val = capex(investing_activity)
    return _pct(_safe_div(capex_val, sales))


def capex_intensity_label(capex_intensity_pct: float | None) -> str | None:
    """Classify CapEx Intensity percentage:
      < 3%  -> 'Asset Light'
      3–8%  -> 'Moderate'
      > 8%  -> 'Capital Intensive'
    """
    if capex_intensity_pct is None:
        return None
    if capex_intensity_pct < 3.0:
        return "Asset Light"
    if capex_intensity_pct <= 8.0:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: float | None,
    operating_profit: float | None,
) -> float | None:
    """FCF Conversion Rate = FCF / operating_profit * 100.
    Returns None if operating_profit is 0 or None.
    """
    if operating_profit is None or operating_profit == 0:
        return None
    return _pct(_safe_div(fcf, operating_profit))


def classify_capital_allocation(
    cfo: float | None,
    cfi: float | None,
    cff: float | None,
    cfo_pat_ratio_avg: float | None = None,
) -> tuple[int | None, int | None, int | None, str | None]:
    """Classify (CFO, CFI, CFF) triplet into one of 8 capital allocation patterns.

    Pattern rules:
      (+, -, -) -> Reinvestor / Shareholder Returns (if 5Y avg CFO/PAT > 1.0)
      (+, +, -) -> Liquidating Assets
      (-, +, +) -> Distress Signal
      (-, -, +) -> Growth Funded by Debt
      (+, +, +) -> Cash Accumulator
      (-, -, -) -> Pre-Revenue
      (+, -, +) -> Mixed

    Returns: (cfo_sign, cfi_sign, cff_sign, pattern_label)
    """
    s_cfo = _sign(cfo)
    s_cfi = _sign(cfi)
    s_cff = _sign(cff)

    if s_cfo is None or s_cfi is None or s_cff is None:
        return s_cfo, s_cfi, s_cff, None

    key = (
        s_cfo if s_cfo != 0 else 1,
        s_cfi if s_cfi != 0 else -1,
        s_cff if s_cff != 0 else -1,
    )

    label = _PATTERN_MAP.get(key, "Mixed")

    # Disambiguate (+, -, -) using CFO/PAT ratio
    if (
        key == (1, -1, -1)
        and label == "Reinvestor"
        and cfo_pat_ratio_avg is not None
        and cfo_pat_ratio_avg > SHAREHOLDER_RETURNS_THRESHOLD
    ):
        label = "Shareholder Returns"

    return s_cfo, s_cfi, s_cff, label


# ---------------------------------------------------------------------------
# CSV Generator
# ---------------------------------------------------------------------------


def generate_capital_allocation_csv(conn: sqlite3.Connection, output_path: Path = OUTPUT_CSV) -> int:
    """Generate output/capital_allocation.csv from cashflow & profitandloss tables."""
    sql = """
    SELECT
        cf.company_id,
        cf.year,
        cf.operating_activity,
        cf.investing_activity,
        cf.financing_activity,
        pl.net_profit
    FROM cashflow cf
    LEFT JOIN profitandloss pl
        ON cf.company_id = pl.company_id AND cf.year = pl.year
    ORDER BY cf.company_id, cf.year
    """
    rows = conn.execute(sql).fetchall()

    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r[0], []).append(r)

    records: list[dict] = []
    for cid, c_rows in grouped.items():
        for idx, r in enumerate(c_rows):
            # Rolling 5Y window for CFO/PAT
            window = c_rows[max(0, idx - 4) : idx + 1]
            ratios: list[float] = []
            for w in window:
                cfo_val = w[2]
                pat_val = w[5]
                if cfo_val is not None and pat_val is not None and pat_val != 0:
                    ratios.append(cfo_val / pat_val)
            avg_cfo_pat = (sum(ratios) / len(ratios)) if ratios else None

            s_cfo, s_cfi, s_cff, label = classify_capital_allocation(
                cfo=r[2],
                cfi=r[3],
                cff=r[4],
                cfo_pat_ratio_avg=avg_cfo_pat,
            )
            records.append({
                "company_id": cid,
                "year": r[1],
                "cfo_sign": s_cfo,
                "cfi_sign": s_cfi,
                "cff_sign": s_cff,
                "pattern_label": label,
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]
        )
        writer.writeheader()
        writer.writerows(records)

    return len(records)


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        written = generate_capital_allocation_csv(conn)
        log.info("Generated %s (%d rows)", OUTPUT_CSV, written)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
