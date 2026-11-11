"""
src/analytics/cashflow.py
Backward-compatible wrapper for src/analytics/cashflow_kpis.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analytics.cashflow_kpis import (  # noqa: F401
    _PATTERN_MAP,
    OUTPUT_CSV,
    SHAREHOLDER_RETURNS_THRESHOLD,
    _sign,
    capex,
    capex_intensity,
    capex_intensity_label,
    cfo_quality_label,
    cfo_quality_score,
    cfo_quality_score_5yr,
    classify_capital_allocation,
    fcf_conversion_rate,
    free_cash_flow,
    generate_capital_allocation_csv,
    main,
)


def write_csv(records: list[dict], path: Path) -> int:
    """Compatibility helper to write records to CSV."""
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    return len(records)


def run() -> None:
    main()


if __name__ == "__main__":
    run()
