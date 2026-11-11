"""
tests/kpi/test_cagr.py
Sprint 2 — Day 10: Unit tests for CAGR Engine (src/analytics/cagr.py)

10 Unit Tests covering:
  1. Normal CAGR calculation (positive growth)
  2. Normal zero growth (flat series)
  3. Turnaround flag (negative -> positive)
  4. Decline-to-loss flag (positive -> negative)
  5. Both negative flag (negative -> negative)
  6. Zero base flag (start = 0)
  7. Insufficient data flag (less than n years of data)
  8. Insufficient data flag (None and NaN values)
  9. JIOFIN exclusion handling (flagged as INSUFFICIENT for multi-year)
  10. Full multi-period series computation for Revenue, PAT, and EPS
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analytics.cagr import (
    FLAG_BOTH_NEGATIVE,
    FLAG_DECLINE_TO_LOSS,
    FLAG_INSUFFICIENT,
    FLAG_NORMAL,
    FLAG_TURNAROUND,
    FLAG_ZERO_BASE,
    CAGRResult,
    cagr,
    calculate_cagr,
    compute_series_cagr,
)


class TestDay10CagrEngine:
    """Sprint 2 Day 10 acceptance criteria unit tests."""

    def test_01_normal_cagr_positive_growth(self):
        """1. Normal CAGR: positive to positive computes ((end/start)^(1/n) - 1) * 100."""
        # 100 -> 133.1 over 3 years = 10.0% CAGR
        res = calculate_cagr(100.0, 133.1, 3)
        assert isinstance(res, CAGRResult)
        assert res.value == pytest.approx(10.0, rel=1e-3)
        assert res.flag == FLAG_NORMAL

        # Backward compatibility with pure float helper
        val = cagr(100.0, 133.1, 3)
        assert val == pytest.approx(10.0, rel=1e-3)

    def test_02_normal_cagr_zero_growth(self):
        """2. Normal zero growth: value remains constant over n years -> 0.0% CAGR."""
        res = calculate_cagr(500.0, 500.0, 5)
        assert res.value == pytest.approx(0.0, abs=1e-4)
        assert res.flag == FLAG_NORMAL

    def test_03_turnaround_flag(self):
        """3. Turnaround flag: negative start to positive end -> return None with flag TURNAROUND."""
        # Loss of -100 turning around to profit of 200 over 3 years
        res = calculate_cagr(-100.0, 200.0, 3)
        assert res.value is None
        assert res.flag == FLAG_TURNAROUND

        # Helper returns None
        assert cagr(-100.0, 200.0, 3) is None

    def test_04_decline_to_loss_flag(self):
        """4. Decline-to-loss: positive start to negative end -> return None with flag DECLINE_TO_LOSS."""
        # Profit of 150 deteriorating to loss of -50 over 3 years
        res = calculate_cagr(150.0, -50.0, 3)
        assert res.value is None
        assert res.flag == FLAG_DECLINE_TO_LOSS

        # Helper returns None
        assert cagr(150.0, -50.0, 3) is None

    def test_05_both_negative_flag(self):
        """5. Both negative: negative start to negative end -> return None with flag BOTH_NEGATIVE."""
        # Consecutive loss-making periods
        res = calculate_cagr(-200.0, -80.0, 3)
        assert res.value is None
        assert res.flag == FLAG_BOTH_NEGATIVE

        # Helper returns None
        assert cagr(-200.0, -80.0, 3) is None

    def test_06_zero_base_flag(self):
        """6. Zero base: start value = 0 -> return None with flag ZERO_BASE."""
        res = calculate_cagr(0.0, 100.0, 5)
        assert res.value is None
        assert res.flag == FLAG_ZERO_BASE

        # Helper returns None
        assert cagr(0.0, 100.0, 5) is None

    def test_07_insufficient_data_fewer_years(self):
        """7. Insufficient data: invalid or non-positive years -> return None with flag INSUFFICIENT."""
        res_zero_yrs = calculate_cagr(100.0, 200.0, 0)
        assert res_zero_yrs.value is None
        assert res_zero_yrs.flag == FLAG_INSUFFICIENT

        res_neg_yrs = calculate_cagr(100.0, 200.0, -2)
        assert res_neg_yrs.value is None
        assert res_neg_yrs.flag == FLAG_INSUFFICIENT

    def test_08_insufficient_data_none_and_nan(self):
        """8. Insufficient data: None or NaN input values -> return None with flag INSUFFICIENT."""
        res_none_start = calculate_cagr(None, 200.0, 3)
        assert res_none_start.value is None
        assert res_none_start.flag == FLAG_INSUFFICIENT

        res_none_end = calculate_cagr(100.0, None, 3)
        assert res_none_end.value is None
        assert res_none_end.flag == FLAG_INSUFFICIENT

        res_nan = calculate_cagr(math.nan, 200.0, 3)
        assert res_nan.value is None
        assert res_nan.flag == FLAG_INSUFFICIENT

    def test_09_jiofin_excluded_multi_year(self):
        """9. JIOFIN exclusion: companies with < 3 years history excluded from 3Y/5Y/10Y CAGRs."""
        # 4 data points available
        series = [
            ("2021-03", 100.0),
            ("2022-03", 120.0),
            ("2023-03", 140.0),
            ("2024-03", 160.0),
        ]
        results = compute_series_cagr(series, [3, 5, 10], company_id="JIOFIN")

        assert results["cagr_3y"].value is None
        assert results["cagr_3y"].flag == FLAG_INSUFFICIENT
        assert results["cagr_5y"].value is None
        assert results["cagr_5y"].flag == FLAG_INSUFFICIENT
        assert results["cagr_10y"].value is None
        assert results["cagr_10y"].flag == FLAG_INSUFFICIENT

    def test_10_multi_period_series_all_metrics(self):
        """10. Multi-period series: correctly computes 3Y, 5Y, and 10Y windows with flags."""
        # 11 years of data: 2014-03 to 2024-03
        years = [f"20{14 + i:02d}-03" for i in range(11)]

        # Revenue: Steady positive growth ~10%
        rev_values = [100.0 * (1.10**i) for i in range(11)]
        rev_series = list(zip(years, rev_values))
        rev_results = compute_series_cagr(rev_series, [3, 5, 10], "TESTCO")

        assert rev_results["cagr_3y"].value == pytest.approx(10.0, rel=1e-3)
        assert rev_results["cagr_3y"].flag == FLAG_NORMAL
        assert rev_results["cagr_5y"].value == pytest.approx(10.0, rel=1e-3)
        assert rev_results["cagr_5y"].flag == FLAG_NORMAL
        assert rev_results["cagr_10y"].value == pytest.approx(10.0, rel=1e-3)
        assert rev_results["cagr_10y"].flag == FLAG_NORMAL

        # PAT: Turnaround in 3Y window (-50 in 2021-03 -> +150 in 2024-03)
        pat_values = [50.0] * 7 + [-50.0, 20.0, 80.0, 150.0]
        pat_series = list(zip(years, pat_values))
        pat_results = compute_series_cagr(pat_series, [3, 5, 10], "TESTCO")

        assert pat_results["cagr_3y"].value is None
        assert pat_results["cagr_3y"].flag == FLAG_TURNAROUND

        # EPS: Decline to loss in 3Y window (+20 in 2021-03 -> -5 in 2024-03)
        eps_values = [10.0] * 7 + [20.0, 15.0, 5.0, -5.0]
        eps_series = list(zip(years, eps_values))
        eps_results = compute_series_cagr(eps_series, [3, 5, 10], "TESTCO")

        assert eps_results["cagr_3y"].value is None
        assert eps_results["cagr_3y"].flag == FLAG_DECLINE_TO_LOSS
