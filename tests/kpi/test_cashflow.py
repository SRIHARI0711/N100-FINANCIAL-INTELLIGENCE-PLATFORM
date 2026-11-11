"""
tests/kpi/test_cashflow.py
Sprint 2 — Day 11: Unit tests for Cash Flow KPIs & Capital Allocation.

Covers:
  1. Free Cash Flow allows positive, negative, and zero values
  2. CFO Quality Score (5-year average) and classification bands (>1.0, 0.5-1.0, <0.5)
  3. CFO Quality Score returns None when PAT = 0 or data missing
  4. CapEx Intensity computation and classification (<3% Asset Light, 3-8% Moderate, >8% Capital Intensive)
  5. FCF Conversion Rate: FCF / operating_profit * 100, None if operating_profit = 0
  6. Capital Allocation Classifier — all 8 pattern combinations
  7. Capital Allocation Classifier — disambiguation between Reinvestor and Shareholder Returns via CFO/PAT
  8. Output CSV generation and integrity checks
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analytics.cashflow import (
    classify_capital_allocation,
    write_csv,
)
from src.analytics.ratios import (
    capex_intensity,
    capex_intensity_label,
    cfo_quality_label,
    cfo_quality_score,
    cfo_quality_score_5yr,
    fcf_conversion_rate,
    free_cash_flow,
)


class TestDay11CashFlowKPIs:
    """Sprint 2 Day 11 unit tests for Cash Flow KPIs & Capital Allocation."""

    def test_01_free_cash_flow_allows_negative_values(self):
        """1. FCF = operating_activity + investing_activity. Negative value is allowed."""
        # Positive FCF: strong operating cash flow exceeding capex outflow
        assert free_cash_flow(operating_activity=1000.0, investing_activity=-400.0) == pytest.approx(600.0)

        # Negative FCF: heavy investing outflow exceeds operating cash flow
        assert free_cash_flow(operating_activity=300.0, investing_activity=-800.0) == pytest.approx(-500.0)

        # Negative FCF: negative operating cash flow plus investing outflow
        assert free_cash_flow(operating_activity=-200.0, investing_activity=-300.0) == pytest.approx(-500.0)

        # Zero or None handling
        assert free_cash_flow(operating_activity=0.0, investing_activity=0.0) == pytest.approx(0.0)
        assert free_cash_flow(operating_activity=None, investing_activity=-100.0) is None
        assert free_cash_flow(operating_activity=500.0, investing_activity=None) == pytest.approx(500.0)

    def test_02_cfo_quality_score_5yr_and_classification(self):
        """2. CFO Quality Score: CFO / PAT averaged over 5 years.
        > 1.0 = High Quality, 0.5-1.0 = Moderate, < 0.5 = Accrual Risk.
        """
        # High Quality: average ratio = 1.3 > 1.0
        cfo_high = [130.0, 120.0, 140.0, 125.0, 135.0]
        pat_high = [100.0, 100.0, 100.0, 100.0, 100.0]
        score_high = cfo_quality_score_5yr(cfo_high, pat_high)
        assert score_high == pytest.approx(1.3)
        assert cfo_quality_label(score_high) == "High Quality"

        # Moderate: average ratio = 0.75 (0.5 to 1.0)
        cfo_mod = [70.0, 80.0, 75.0, 70.0, 80.0]
        pat_mod = [100.0, 100.0, 100.0, 100.0, 100.0]
        score_mod = cfo_quality_score_5yr(cfo_mod, pat_mod)
        assert score_mod == pytest.approx(0.75)
        assert cfo_quality_label(score_mod) == "Moderate"

        # Accrual Risk: average ratio = 0.35 < 0.5
        cfo_low = [30.0, 40.0, 35.0, 30.0, 40.0]
        pat_low = [100.0, 100.0, 100.0, 100.0, 100.0]
        score_low = cfo_quality_score_5yr(cfo_low, pat_low)
        assert score_low == pytest.approx(0.35)
        assert cfo_quality_label(score_low) == "Accrual Risk"

        # Boundary checks
        assert cfo_quality_label(1.0) == "Moderate"
        assert cfo_quality_label(1.001) == "High Quality"
        assert cfo_quality_label(0.5) == "Moderate"
        assert cfo_quality_label(0.499) == "Accrual Risk"

    def test_03_cfo_quality_score_edge_cases(self):
        """3. CFO Quality Score returns None if PAT = 0 or data missing."""
        # Single-year cfo_quality_score
        assert cfo_quality_score(operating_activity=100.0, net_profit=0.0) is None
        assert cfo_quality_score(operating_activity=100.0, net_profit=None) is None
        assert cfo_quality_score(operating_activity=None, net_profit=100.0) is None

        # 5-year series with all zero PAT
        assert cfo_quality_score_5yr([100.0, 200.0], [0.0, 0.0]) is None

        # 5-year series with empty lists
        assert cfo_quality_score_5yr([], []) is None

        # Label for None
        assert cfo_quality_label(None) is None

    def test_04_capex_intensity_and_classification(self):
        """4. CapEx Intensity: |investing_activity| / sales x 100.
        <3% = Asset Light, 3-8% = Moderate, >8% = Capital Intensive.
        """
        # Asset Light: 2% (< 3%)
        # investing_activity = -20.0, sales = 1000.0 -> 2.0%
        int_light = capex_intensity(investing_activity=-20.0, sales=1000.0)
        assert int_light == pytest.approx(2.0)
        assert capex_intensity_label(int_light) == "Asset Light"

        # Moderate: 5% (3% to 8%)
        # investing_activity = -50.0, sales = 1000.0 -> 5.0%
        int_mod = capex_intensity(investing_activity=-50.0, sales=1000.0)
        assert int_mod == pytest.approx(5.0)
        assert capex_intensity_label(int_mod) == "Moderate"

        # Capital Intensive: 12% (> 8%)
        # investing_activity = -120.0, sales = 1000.0 -> 12.0%
        int_heavy = capex_intensity(investing_activity=-120.0, sales=1000.0)
        assert int_heavy == pytest.approx(12.0)
        assert capex_intensity_label(int_heavy) == "Capital Intensive"

        # Edge cases: sales <= 0, None
        assert capex_intensity(investing_activity=-50.0, sales=0.0) is None
        assert capex_intensity(investing_activity=-50.0, sales=-100.0) is None
        assert capex_intensity(investing_activity=-50.0, sales=None) is None
        assert capex_intensity(investing_activity=None, sales=1000.0) is None
        assert capex_intensity_label(None) is None

        # Boundary checks
        assert capex_intensity_label(3.0) == "Moderate"
        assert capex_intensity_label(2.999) == "Asset Light"
        assert capex_intensity_label(8.0) == "Moderate"
        assert capex_intensity_label(8.001) == "Capital Intensive"

    def test_05_fcf_conversion_rate(self):
        """5. FCF Conversion Rate: FCF / operating_profit x 100. Return None if operating_profit = 0."""
        # Normal: FCF = 600, operating_profit = 1000 -> 60.0%
        assert fcf_conversion_rate(fcf=600.0, operating_profit=1000.0) == pytest.approx(60.0)

        # Negative FCF conversion: FCF = -200, operating_profit = 1000 -> -20.0%
        assert fcf_conversion_rate(fcf=-200.0, operating_profit=1000.0) == pytest.approx(-20.0)

        # Zero denominator: return None
        assert fcf_conversion_rate(fcf=500.0, operating_profit=0.0) is None

        # Missing values
        assert fcf_conversion_rate(fcf=None, operating_profit=1000.0) is None
        assert fcf_conversion_rate(fcf=500.0, operating_profit=None) is None

    def test_06_capital_allocation_8_patterns(self):
        """6. Capital allocation 8-pattern classifier based on sign of (CFO, CFI, CFF)."""
        # 1. (+, -, -) = Reinvestor (default when CFO/PAT <= 1.0 or not provided)
        _, _, _, label = classify_capital_allocation(cfo=100.0, cfi=-50.0, cff=-30.0, cfo_pat_ratio_avg=0.8)
        assert label == "Reinvestor"

        # 2. (+, -, -) with high CFO/PAT (>1.0) = Shareholder Returns
        _, _, _, label = classify_capital_allocation(cfo=100.0, cfi=-50.0, cff=-30.0, cfo_pat_ratio_avg=1.4)
        assert label == "Shareholder Returns"

        # 3. (+, +, -) = Liquidating Assets
        _, _, _, label = classify_capital_allocation(cfo=100.0, cfi=50.0, cff=-30.0)
        assert label == "Liquidating Assets"

        # 4. (-, +, +) = Distress Signal
        _, _, _, label = classify_capital_allocation(cfo=-100.0, cfi=50.0, cff=30.0)
        assert label == "Distress Signal"

        # 5. (-, -, +) = Growth Funded by Debt
        _, _, _, label = classify_capital_allocation(cfo=-100.0, cfi=-50.0, cff=30.0)
        assert label == "Growth Funded by Debt"

        # 6. (+, +, +) = Cash Accumulator
        _, _, _, label = classify_capital_allocation(cfo=100.0, cfi=50.0, cff=30.0)
        assert label == "Cash Accumulator"

        # 7. (-, -, -) = Pre-Revenue
        _, _, _, label = classify_capital_allocation(cfo=-100.0, cfi=-50.0, cff=-30.0)
        assert label == "Pre-Revenue"

        # 8. (+, -, +) = Mixed
        _, _, _, label = classify_capital_allocation(cfo=100.0, cfi=-50.0, cff=30.0)
        assert label == "Mixed"

    def test_07_capital_allocation_signs_and_none(self):
        """7. Capital allocation returns correct signs (+1, -1, 0) and None for missing data."""
        s_cfo, s_cfi, s_cff, label = classify_capital_allocation(cfo=250.0, cfi=-120.0, cff=-80.0)
        assert s_cfo == 1
        assert s_cfi == -1
        assert s_cff == -1
        assert label == "Reinvestor"

        # If any component is None, pattern_label is None
        s_cfo, s_cfi, s_cff, label = classify_capital_allocation(cfo=None, cfi=-120.0, cff=-80.0)
        assert s_cfo is None
        assert label is None

    def test_08_csv_generation_and_columns(self, tmp_path):
        """8. Write CSV and verify schema: company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label."""
        test_csv = tmp_path / "test_capital_allocation.csv"
        records = [
            {
                "company_id": "INFY",
                "year": "2024-03",
                "cfo_sign": 1,
                "cfi_sign": -1,
                "cff_sign": -1,
                "pattern_label": "Shareholder Returns",
            },
            {
                "company_id": "TATAMOTORS",
                "year": "2024-03",
                "cfo_sign": 1,
                "cfi_sign": -1,
                "cff_sign": 1,
                "pattern_label": "Mixed",
            },
        ]
        count = write_csv(records, test_csv)
        assert count == 2
        assert test_csv.exists()

        with test_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            expected_fields = ["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"]
            assert reader.fieldnames == expected_fields
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["company_id"] == "INFY"
            assert rows[0]["pattern_label"] == "Shareholder Returns"
            assert rows[1]["pattern_label"] == "Mixed"
