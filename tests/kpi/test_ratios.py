"""
tests/kpi/test_ratios.py
Sprint 2 — Day 08: Unit tests for src/analytics/ratios.py

Coverage:
  - Pure math helpers (_safe_div, _pct, cagr)
  - Profitability KPIs (NPM, OPM, ROE, ROCE, ROA)
  - Leverage KPIs (D/E, Interest Coverage)
  - Efficiency KPIs (Asset Turnover, Working Capital)
  - Cash-Flow KPIs (FCF, CapEx, CFO Quality, CapEx Intensity)
  - Per-share KPIs (BVPS)
  - CAGR engine (_cagr_series)
  - Bank / Financials carve-out
  - Edge cases: None, zero, negative values, JIOFIN exclusion
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap (mirror conftest.py approach)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.analytics.ratios import (
    DEBT_FREE_COVERAGE,
    _cagr_series,
    _pct,
    _round,
    _safe_div,
    asset_turnover,
    book_value_per_share,
    cagr,
    calculate_composite_quality_score,
    capex,
    capex_intensity,
    cfo_quality_score,
    debt_to_equity,
    free_cash_flow,
    get_icr_label,
    high_leverage_flag,
    icr_warning_flag,
    interest_coverage,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
    sector_relative_roce_benchmark,
    working_capital,
)

# ===========================================================================
# _safe_div
# ===========================================================================


class TestSafeDiv:
    def test_normal_division(self):
        assert _safe_div(10.0, 4.0) == pytest.approx(2.5)

    def test_zero_denominator_returns_none(self):
        assert _safe_div(10.0, 0.0) is None

    def test_zero_denominator_int(self):
        assert _safe_div(10, 0) is None

    def test_none_numerator_returns_none(self):
        assert _safe_div(None, 5.0) is None

    def test_none_denominator_returns_none(self):
        assert _safe_div(5.0, None) is None

    def test_both_none_returns_none(self):
        assert _safe_div(None, None) is None

    def test_negative_values(self):
        assert _safe_div(-100.0, 50.0) == pytest.approx(-2.0)

    def test_nan_numerator_returns_none(self):
        import math

        assert _safe_div(math.nan, 5.0) is None


# ===========================================================================
# _pct
# ===========================================================================


class TestPct:
    def test_converts_ratio_to_percent(self):
        assert _pct(0.25) == pytest.approx(25.0)

    def test_none_returns_none(self):
        assert _pct(None) is None

    def test_zero(self):
        assert _pct(0.0) == pytest.approx(0.0)

    def test_negative(self):
        assert _pct(-0.05) == pytest.approx(-5.0)


# ===========================================================================
# CAGR
# ===========================================================================


class TestCagr:
    def test_positive_growth(self):
        # 100 → 121 over 2 years = 10% CAGR
        result = cagr(100.0, 121.0, 2)
        assert result == pytest.approx(10.0, rel=1e-4)

    def test_zero_growth(self):
        result = cagr(100.0, 100.0, 5)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_negative_start_returns_none(self):
        assert cagr(-100.0, 50.0, 3) is None

    def test_negative_end_returns_none(self):
        assert cagr(100.0, -50.0, 3) is None

    def test_zero_start_returns_none(self):
        assert cagr(0.0, 100.0, 5) is None

    def test_none_values_return_none(self):
        assert cagr(None, 100.0, 5) is None
        assert cagr(100.0, None, 5) is None

    def test_zero_years_returns_none(self):
        assert cagr(100.0, 200.0, 0) is None

    def test_negative_years_returns_none(self):
        assert cagr(100.0, 200.0, -1) is None

    def test_one_year(self):
        assert cagr(200.0, 220.0, 1) == pytest.approx(10.0, rel=1e-4)


# ===========================================================================
# Net Profit Margin
# ===========================================================================


class TestNetProfitMargin:
    def test_normal(self):
        assert net_profit_margin(200.0, 1000.0) == pytest.approx(20.0)

    def test_zero_sales_returns_none(self):
        assert net_profit_margin(200.0, 0.0) is None

    def test_negative_sales_returns_none(self):
        assert net_profit_margin(200.0, -100.0) is None

    def test_none_sales_returns_none(self):
        assert net_profit_margin(200.0, None) is None

    def test_loss_company(self):
        result = net_profit_margin(-50.0, 500.0)
        assert result == pytest.approx(-10.0)


# ===========================================================================
# Operating Profit Margin
# ===========================================================================


class TestOperatingProfitMargin:
    def test_normal(self):
        assert operating_profit_margin(300.0, 1000.0) == pytest.approx(30.0)

    def test_financials_returns_none(self):
        assert operating_profit_margin(300.0, 1000.0, is_financial=True) is None

    def test_zero_sales_returns_none(self):
        assert operating_profit_margin(300.0, 0.0) is None

    def test_none_sales_returns_none(self):
        assert operating_profit_margin(300.0, None) is None


# ===========================================================================
# Return on Equity
# ===========================================================================


class TestReturnOnEquity:
    def test_normal(self):
        # net_profit=200, equity=100, reserves=900 → net_worth=1000
        result = return_on_equity(200.0, 100.0, 900.0)
        assert result == pytest.approx(20.0)

    def test_negative_net_worth_returns_none(self):
        assert return_on_equity(200.0, 100.0, -500.0) is None

    def test_zero_net_worth_returns_none(self):
        assert return_on_equity(200.0, 0.0, 0.0) is None

    def test_none_equity_returns_none(self):
        assert return_on_equity(200.0, None, 900.0) is None

    def test_loss_roe(self):
        result = return_on_equity(-100.0, 100.0, 400.0)
        assert result == pytest.approx(-20.0)


# ===========================================================================
# Return on Capital Employed
# ===========================================================================


class TestReturnOnCapitalEmployed:
    def test_normal(self):
        # EBIT = 300 + 50 = 350; CE = 2000 - 400 = 1600
        result = return_on_capital_employed(300.0, 50.0, 2000.0, 400.0)
        assert result == pytest.approx(21.875)

    def test_financials_returns_none(self):
        result = return_on_capital_employed(
            300.0, 50.0, 2000.0, 400.0, is_financial=True
        )
        assert result is None

    def test_zero_capital_employed_returns_none(self):
        # CE = 1000 - 1000 = 0
        assert return_on_capital_employed(300.0, 50.0, 1000.0, 1000.0) is None

    def test_none_total_assets_returns_none(self):
        assert return_on_capital_employed(300.0, 50.0, None, 400.0) is None


# ===========================================================================
# Return on Assets
# ===========================================================================


class TestReturnOnAssets:
    def test_normal(self):
        result = return_on_assets(100.0, 2000.0)
        assert result == pytest.approx(5.0)

    def test_zero_assets_returns_none(self):
        assert return_on_assets(100.0, 0.0) is None

    def test_none_assets_returns_none(self):
        assert return_on_assets(100.0, None) is None


# ===========================================================================
# Debt to Equity
# ===========================================================================


class TestDebtToEquity:
    def test_normal(self):
        # D/E = 500 / 1000 = 0.5
        result = debt_to_equity(500.0, 100.0, 900.0)
        assert result == pytest.approx(0.5)

    def test_zero_debt(self):
        result = debt_to_equity(0.0, 100.0, 900.0)
        assert result == pytest.approx(0.0)

    def test_financials_returns_none(self):
        assert debt_to_equity(500.0, 100.0, 900.0, is_financial=True) is None

    def test_negative_networth_returns_none(self):
        assert debt_to_equity(500.0, 100.0, -200.0) is None

    def test_none_equity_returns_none(self):
        assert debt_to_equity(500.0, None, 900.0) is None


# ===========================================================================
# Interest Coverage
# ===========================================================================


class TestInterestCoverage:
    def test_normal(self):
        # EBIT = 300 + 50 = 350; interest = 50
        result = interest_coverage(300.0, 50.0, 50.0, 500.0)
        assert result == pytest.approx(7.0)

    def test_zero_borrowings_returns_sentinel(self):
        result = interest_coverage(300.0, 50.0, 50.0, 0.0)
        assert result == DEBT_FREE_COVERAGE

    def test_zero_interest_with_borrowings_returns_none(self):
        assert interest_coverage(300.0, 50.0, 0.0, 500.0) is None

    def test_none_borrowings_treated_as_zero_returns_sentinel(self):
        result = interest_coverage(300.0, 50.0, 50.0, None)
        assert result == DEBT_FREE_COVERAGE


# ===========================================================================
# Asset Turnover
# ===========================================================================


class TestAssetTurnover:
    def test_normal(self):
        result = asset_turnover(2000.0, 1000.0)
        assert result == pytest.approx(2.0)

    def test_zero_assets_returns_none(self):
        assert asset_turnover(2000.0, 0.0) is None

    def test_none_assets_returns_none(self):
        assert asset_turnover(2000.0, None) is None


# ===========================================================================
# Working Capital
# ===========================================================================


class TestWorkingCapital:
    def test_normal(self):
        assert working_capital(500.0, 300.0) == pytest.approx(200.0)

    def test_negative_working_capital(self):
        assert working_capital(200.0, 500.0) == pytest.approx(-300.0)

    def test_none_values_treated_as_zero(self):
        assert working_capital(None, None) == pytest.approx(0.0)


# ===========================================================================
# Free Cash Flow
# ===========================================================================


class TestFreeCashFlow:
    def test_normal(self):
        # CFO = 1000, investing = -300 → FCF = 700
        result = free_cash_flow(1000.0, -300.0)
        assert result == pytest.approx(700.0)

    def test_none_operating_returns_none(self):
        assert free_cash_flow(None, -300.0) is None

    def test_none_investing_treated_as_zero(self):
        assert free_cash_flow(1000.0, None) == pytest.approx(1000.0)


# ===========================================================================
# CapEx
# ===========================================================================


class TestCapex:
    def test_negative_investing_returns_positive(self):
        assert capex(-500.0) == pytest.approx(500.0)

    def test_positive_investing_returns_abs(self):
        assert capex(200.0) == pytest.approx(200.0)

    def test_none_returns_none(self):
        assert capex(None) is None


# ===========================================================================
# CFO Quality Score
# ===========================================================================


class TestCFOQualityScore:
    def test_high_quality(self):
        # CFO > net_profit → quality > 1
        result = cfo_quality_score(1200.0, 1000.0)
        assert result == pytest.approx(1.2)

    def test_zero_net_profit_returns_none(self):
        assert cfo_quality_score(1200.0, 0.0) is None

    def test_none_values_propagate(self):
        assert cfo_quality_score(None, 1000.0) is None


# ===========================================================================
# CapEx Intensity
# ===========================================================================


class TestCapexIntensity:
    def test_normal(self):
        # capex = 300 (from investing = -300), sales = 1000 → 30%
        result = capex_intensity(-300.0, 1000.0)
        assert result == pytest.approx(30.0)

    def test_zero_sales_returns_none(self):
        assert capex_intensity(-300.0, 0.0) is None

    def test_none_sales_returns_none(self):
        assert capex_intensity(-300.0, None) is None


# ===========================================================================
# Book Value Per Share
# ===========================================================================


class TestBookValuePerShare:
    def test_normal(self):
        # equity=200 Cr, reserves=800 Cr, fv=10 → net_worth=1000 Cr
        # shares = 200/10 * 100 = 2000 Cr units
        # BVPS = 1000/2000 = 0.5 Cr/Cr = 0.5 (simplifies; units match)
        result = book_value_per_share(200.0, 800.0, 10.0)
        assert result == pytest.approx(0.5)

    def test_zero_equity_returns_none(self):
        assert book_value_per_share(0.0, 800.0, 10.0) is None

    def test_none_face_value_returns_none(self):
        assert book_value_per_share(200.0, 800.0, None) is None

    def test_zero_face_value_returns_none(self):
        assert book_value_per_share(200.0, 800.0, 0.0) is None


# ===========================================================================
# CAGR series engine
# ===========================================================================


class TestCagrSeries:
    def _make_series(self, values: list[float]) -> list[tuple]:
        years = [f"20{10 + i:02d}-03" for i in range(len(values))]
        return list(zip(years, values))

    def test_10_year_series(self):
        # 11 rows → index 0=100 … 10=259
        # 1Y CAGR: index[-2]=236, index[-1]=259
        # 10Y CAGR: index[-11]=100, index[-1]=259 → ≈10%
        series = self._make_series(
            [100, 110, 121, 133, 146, 161, 177, 195, 214, 236, 259]
        )
        result = _cagr_series(series, [1, 3, 5, 10], "TESTCO")
        assert result["cagr_1y"] == pytest.approx(cagr(236.0, 259.0, 1), rel=1e-3)
        assert result["cagr_10y"] == pytest.approx(10.0, rel=1e-2)

    def test_short_series_returns_none_for_longer_cagr(self):
        series = self._make_series([100, 110, 121])
        result = _cagr_series(series, [1, 3, 5, 10], "TESTCO")
        assert result["cagr_1y"] is not None
        assert result["cagr_3y"] is None  # only 3 rows → need 4 for 3Y
        assert result["cagr_5y"] is None
        assert result["cagr_10y"] is None

    def test_jiofin_excluded_from_multi_year(self):
        series = self._make_series([100, 110, 121, 133])
        result = _cagr_series(series, [1, 3, 5, 10], "JIOFIN")
        assert result["cagr_1y"] is not None  # 1Y still computed
        assert result["cagr_3y"] is None  # excluded
        assert result["cagr_5y"] is None  # excluded
        assert result["cagr_10y"] is None  # excluded

    def test_negative_start_cagr_returns_none(self):
        series = self._make_series([-100, 110, 121, 133])
        result = _cagr_series(series, [3], "TESTCO")
        assert result["cagr_3y"] is None

    def test_empty_series_all_none(self):
        result = _cagr_series([], [1, 3, 5, 10], "TESTCO")
        for k in result.values():
            assert k is None


# ===========================================================================
# _round helper
# ===========================================================================


class TestRound:
    def test_rounds_to_4_places(self):
        assert _round(3.14159265) == 3.1416

    def test_none_passthrough(self):
        assert _round(None) is None

    def test_exact_value_unchanged(self):
        assert _round(25.0) == 25.0


# ===========================================================================
# Day 08 — Profitability Ratios Dedicated Test Suite (8 Required Unit Tests)
# ===========================================================================


class TestDay08ProfitabilityRatios:
    """Sprint 2 Day 08 acceptance criteria unit tests.
    Covers:
      1. Normal case calculations for all profitability ratios
      2. Zero denominator handling (sales = 0 -> None for NPM)
      3. Zero denominator handling (sales = 0 -> None for OPM)
      4. Zero denominator handling (assets = 0 -> None for ROA)
      5. Zero denominator handling (equity + reserves = 0 -> None for ROE)
      6. Negative equity handling (equity + reserves <= 0 -> None for ROE)
      7. OPM cross-check mismatch logging (diff > 1% logs warning, <= 1% does not)
      8. ROCE calculation with (equity + reserves + borrowings) & Financials sector benchmark
    """

    def test_profitability_normal_cases(self):
        """1. Normal case: verifies all profitability KPI formulas with standard positive values."""
        # NPM: 200 / 1000 * 100 = 20.0%
        assert net_profit_margin(200.0, 1000.0) == pytest.approx(20.0)
        # OPM: 300 / 1000 * 100 = 30.0%
        assert operating_profit_margin(300.0, 1000.0) == pytest.approx(30.0)
        # ROE: 200 / (100 + 900) * 100 = 20.0%
        assert return_on_equity(200.0, 100.0, 900.0) == pytest.approx(20.0)
        # ROCE: EBIT (300+50=350) / (100 + 900 + 600) * 100 = 350 / 1600 * 100 = 21.875%
        assert return_on_capital_employed(
            operating_profit=300.0,
            other_income=50.0,
            equity_capital=100.0,
            reserves=900.0,
            borrowings=600.0,
        ) == pytest.approx(21.875)
        # ROA: 100 / 2000 * 100 = 5.0%
        assert return_on_assets(100.0, 2000.0) == pytest.approx(5.0)

    def test_zero_denominator_npm(self):
        """2. Zero denominator: NPM returns None when sales = 0."""
        assert net_profit_margin(200.0, 0.0) is None

    def test_zero_denominator_opm(self):
        """3. Zero denominator: OPM returns None when sales = 0."""
        assert operating_profit_margin(300.0, 0.0) is None

    def test_zero_denominator_roa(self):
        """4. Zero denominator: ROA returns None when total_assets = 0."""
        assert return_on_assets(100.0, 0.0) is None

    def test_zero_denominator_roe(self):
        """5. Zero denominator: ROE returns None when equity + reserves = 0."""
        assert return_on_equity(200.0, 0.0, 0.0) is None

    def test_negative_equity_roe_returns_none(self):
        """6. Negative equity: ROE returns None when equity + reserves < 0."""
        # equity=100, reserves=-500 -> net_worth = -400 <= 0
        assert return_on_equity(200.0, 100.0, -500.0) is None
        # Both negative
        assert return_on_equity(200.0, -50.0, -100.0) is None

    def test_opm_cross_check_mismatch_logging(self, caplog):
        """7. OPM cross-check: logs warning when |computed - reported| > 1%, silent when <= 1%."""
        import logging

        # Case 1: Difference > 1% (computed = 20.0%, reported = 25.0%, diff = 5.0% > 1%) -> logs warning
        with caplog.at_level(logging.WARNING):
            caplog.clear()
            opm = operating_profit_margin(
                operating_profit=20.0,
                sales=100.0,
                opm_percentage=25.0,
                company_id="TESTCO",
                year="2024-03",
            )
            assert opm == pytest.approx(20.0)
            assert any(
                "OPM cross-check mismatch" in record.message and "TESTCO" in record.message
                for record in caplog.records
            )

        # Case 2: Difference <= 1% (computed = 20.0%, reported = 20.5%, diff = 0.5% <= 1%) -> no warning
        with caplog.at_level(logging.WARNING):
            caplog.clear()
            opm = operating_profit_margin(
                operating_profit=20.0,
                sales=100.0,
                opm_percentage=20.5,
            )
            assert opm == pytest.approx(20.0)
            assert not any("OPM cross-check mismatch" in record.message for record in caplog.records)

    def test_financials_sector_roce_benchmark(self):
        """8. Financials broad_sector ROCE: uses sector-relative ROCE benchmark instead of absolute threshold."""
        # Financials sector company default carve-out returns None
        assert return_on_capital_employed(
            300.0, 50.0, equity_capital=100.0, reserves=900.0, borrowings=600.0, is_financial=True
        ) is None

        # Financials sector company with relative benchmark returns the benchmark value
        benchmark_val = 14.5
        assert return_on_capital_employed(
            300.0,
            50.0,
            equity_capital=100.0,
            reserves=900.0,
            borrowings=600.0,
            is_financial=True,
            sector_benchmark=benchmark_val,
        ) == pytest.approx(benchmark_val)

        # Relative benchmark computation helper test
        spread = sector_relative_roce_benchmark(roce=16.5, sector_median=12.0)
        assert spread == pytest.approx(4.5)


# ===========================================================================
# Day 09 — Leverage & Efficiency Ratios Dedicated Test Suite (8 Required Unit Tests)
# ===========================================================================


class TestDay09LeverageAndEfficiencyRatios:
    """Sprint 2 Day 09 acceptance criteria unit tests.
    Covers:
      1. D/E debt-free returns 0 (not None) when borrowings = 0
      2. D/E normal calculation: borrowings / (equity + reserves)
      3. High D/E flag: True when D/E > 5 and NOT in Financials sector; False for Financials
      4. ICR interest = 0 returns None
      5. ICR normal calculation: (operating_profit + other_income) / interest
      6. ICR display label 'Debt Free' stored in icr_label when company is debt-free (borrowings == 0 or None)
      7. ICR warning flag: True when ICR < 1.5 (at risk of not covering interest payments)
      8. Net Debt (borrowings - investments) & Asset Turnover (sales / total_assets, None if total_assets = 0)
    """

    def test_debt_to_equity_debt_free_returns_zero(self):
        """1. D/E debt-free returns 0 (not None) if borrowings = 0."""
        result = debt_to_equity(borrowings=0.0, equity_capital=100.0, reserves=900.0)
        assert result == 0.0
        assert result is not None

    def test_debt_to_equity_normal(self):
        """2. D/E normal calculation: 500 / (100 + 900) = 0.5."""
        result = debt_to_equity(borrowings=500.0, equity_capital=100.0, reserves=900.0)
        assert result == pytest.approx(0.5)

    def test_high_leverage_flag(self):
        """3. High D/E flag: if D/E > 5 and company is NOT in Financials sector -> high_leverage_flag = True."""
        # D/E > 5, non-financial -> True
        assert high_leverage_flag(6.2, is_financial=False) is True
        # D/E <= 5, non-financial -> False
        assert high_leverage_flag(4.8, is_financial=False) is False
        assert high_leverage_flag(5.0, is_financial=False) is False
        # D/E > 5, but company IS in Financials sector -> False (exempt)
        assert high_leverage_flag(8.5, is_financial=True) is False
        # D/E is None -> False
        assert high_leverage_flag(None, is_financial=False) is False

    def test_interest_coverage_interest_zero_returns_none(self):
        """4. ICR interest = 0 returns None."""
        assert interest_coverage(operating_profit=300.0, other_income=50.0, interest=0.0) is None
        assert interest_coverage(operating_profit=300.0, other_income=50.0, interest=None) is None

    def test_interest_coverage_normal(self):
        """5. ICR normal calculation: (300 + 50) / 50 = 7.0."""
        result = interest_coverage(operating_profit=300.0, other_income=50.0, interest=50.0, borrowings=500.0)
        assert result == pytest.approx(7.0)

    def test_icr_label_debt_free(self):
        """6. For ICR = None (debt-free companies) -> store display label 'Debt Free' in icr_label."""
        # Debt-free company with no borrowings (borrowings == 0) and ICR = None
        assert get_icr_label(icr=None, borrowings=0.0) == "Debt Free"
        # Debt-free company with borrowings = None and ICR = None
        assert get_icr_label(icr=None, borrowings=None) == "Debt Free"
        # Sentinel value for debt-free coverage
        assert get_icr_label(icr=DEBT_FREE_COVERAGE, borrowings=0.0) == "Debt Free"
        # Company with debt and valid ICR -> formatted ratio string (e.g. '7.00x')
        assert get_icr_label(icr=7.0, borrowings=500.0) == "7.00x"
        # Company with debt but interest=0 (data gap) -> returns None (not 'Debt Free')
        assert get_icr_label(icr=None, borrowings=500.0) is None

    def test_icr_warning_flag(self):
        """7. ICR warning flag: if ICR < 1.5 -> company is at risk of not covering interest payments."""
        # At risk: ICR < 1.5
        assert icr_warning_flag(1.2, is_financial=False) is True
        assert icr_warning_flag(0.8, is_financial=False) is True
        assert icr_warning_flag(-0.5, is_financial=False) is True
        # Safe: ICR >= 1.5
        assert icr_warning_flag(1.5, is_financial=False) is False
        assert icr_warning_flag(4.2, is_financial=False) is False
        # Debt-free companies (ICR is None or 999) -> False (no interest payment risk)
        assert icr_warning_flag(None, is_financial=False) is False
        assert icr_warning_flag(DEBT_FREE_COVERAGE, is_financial=False) is False
        # Financials sector -> False (carved out)
        assert icr_warning_flag(1.1, is_financial=True) is False

    def test_net_debt_and_asset_turnover(self):
        """8. Implement Net Debt (borrowings - investments) and Asset Turnover (sales / total_assets)."""
        # Net Debt = borrowings - investments
        assert net_debt(borrowings=1000.0, investments=250.0) == pytest.approx(750.0)
        # Net Cash position (investments > borrowings)
        assert net_debt(borrowings=100.0, investments=500.0) == pytest.approx(-400.0)
        # None handling
        assert net_debt(borrowings=None, investments=100.0) is None
        assert net_debt(borrowings=500.0, investments=None) == pytest.approx(500.0)

        # Asset Turnover: sales / total_assets
        assert asset_turnover(sales=3000.0, total_assets=1500.0) == pytest.approx(2.0)
        # Asset Turnover: returns None if total_assets = 0
        assert asset_turnover(sales=3000.0, total_assets=0.0) is None
        assert asset_turnover(sales=3000.0, total_assets=None) is None
        assert asset_turnover(sales=None, total_assets=1500.0) is None


# ===========================================================================
# Day 12 — Populate financial_ratios Table & Spot-Checks
# ===========================================================================


class TestDay12FinancialRatiosPopulation:
    """Sprint 2 Day 12 acceptance criteria unit tests."""

    DB_PATH = BASE_DIR / "data" / "nifty100.db"

    def test_row_count_gte_1100(self):
        """1. Verify row count: SELECT COUNT(*) FROM financial_ratios >= 1,100 rows."""
        import sqlite3

        conn = sqlite3.connect(self.DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
        conn.close()
        assert count >= 1100, f"Expected >= 1,100 rows, got {count}"

    def test_all_14_plus_required_kpi_columns_exist_and_populated(self):
        """2. Write all 14+ computed KPI columns into financial_ratios."""
        import sqlite3

        required_kpis = [
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
        conn = sqlite3.connect(self.DB_PATH)
        cur = conn.execute("PRAGMA table_info(financial_ratios)")
        existing_cols = {r[1] for r in cur.fetchall()}

        for kpi in required_kpis:
            assert kpi in existing_cols, f"Required KPI column '{kpi}' missing from financial_ratios"
            non_null_count = conn.execute(f"SELECT COUNT({kpi}) FROM financial_ratios").fetchone()[0]
            assert non_null_count > 0, f"Column '{kpi}' has zero non-null values"
        conn.close()

    def _verify_manual_spot_check(self, company_id: str):
        """Helper to recompute ROE and 5-yr Revenue CAGR manually and check diff < 0.1%."""
        import sqlite3

        conn = sqlite3.connect(self.DB_PATH)
        conn.row_factory = sqlite3.Row

        pl_rows = conn.execute(
            "SELECT year, sales, net_profit FROM profitandloss WHERE company_id = ? ORDER BY year",
            (company_id,),
        ).fetchall()
        bs_rows = conn.execute(
            "SELECT year, equity_capital, reserves FROM balancesheet WHERE company_id = ? ORDER BY year",
            (company_id,),
        ).fetchall()

        latest_pl = pl_rows[-1]
        latest_year = latest_pl["year"]
        latest_bs = next(b for b in bs_rows if b["year"] == latest_year)

        # 1. Manual ROE calculation
        net_profit = latest_pl["net_profit"]
        net_worth = latest_bs["equity_capital"] + latest_bs["reserves"]
        manual_roe = (net_profit / net_worth) * 100.0

        # 2. Manual 5-yr Revenue CAGR calculation
        sales_end = pl_rows[-1]["sales"]
        sales_start = pl_rows[-6]["sales"]
        manual_rev_cagr_5yr = ((sales_end / sales_start) ** (1.0 / 5.0) - 1.0) * 100.0

        # Retrieve DB values
        ratio_row = conn.execute(
            "SELECT return_on_equity_pct, revenue_cagr_5yr, revenue_cagr_5y FROM financial_ratios WHERE company_id = ? AND year = ?",
            (company_id, latest_year),
        ).fetchone()
        conn.close()

        db_roe = ratio_row["return_on_equity_pct"]
        db_rev_cagr = ratio_row["revenue_cagr_5yr"] or ratio_row["revenue_cagr_5y"]

        diff_roe = abs(manual_roe - db_roe) / db_roe * 100.0
        diff_cagr = abs(manual_rev_cagr_5yr - db_rev_cagr) / db_rev_cagr * 100.0

        assert diff_roe < 0.1, f"{company_id} ROE diff {diff_roe:.6f}% >= 0.1%"
        assert diff_cagr < 0.1, f"{company_id} 5Y Rev CAGR diff {diff_cagr:.6f}% >= 0.1%"

    def test_spot_check_tcs(self):
        """3. Manual spot-check: TCS ROE and 5-yr Revenue CAGR diff < 0.1%."""
        self._verify_manual_spot_check("TCS")

    def test_spot_check_infy(self):
        """4. Manual spot-check: INFY ROE and 5-yr Revenue CAGR diff < 0.1%."""
        self._verify_manual_spot_check("INFY")

    def test_spot_check_itc(self):
        """5. Manual spot-check: ITC ROE and 5-yr Revenue CAGR diff < 0.1%."""
        self._verify_manual_spot_check("ITC")

    def test_composite_quality_score_calculation(self):
        """6. Composite quality score bounds and healthy vs distressed company ranking."""
        # High quality company (TCS-like metrics)
        score_high = calculate_composite_quality_score(
            roe=35.0,
            roce=45.0,
            npm=19.0,
            fcf=30000.0,
            cfo_pat_ratio=1.1,
            revenue_cagr_5yr=10.0,
            pat_cagr_5yr=10.0,
            debt_to_equity=0.0,
            interest_coverage=None,
            icr_label="Debt Free",
        )
        assert score_high is not None
        assert 80.0 <= score_high <= 100.0

        # Distressed company
        score_low = calculate_composite_quality_score(
            roe=-10.0,
            roce=-2.0,
            npm=-5.0,
            fcf=-1000.0,
            cfo_pat_ratio=0.1,
            revenue_cagr_5yr=-5.0,
            pat_cagr_5yr=-15.0,
            debt_to_equity=5.5,
            interest_coverage=0.8,
            icr_label=None,
        )
        assert score_low is not None
        assert 0.0 <= score_low <= 25.0
        assert score_high > score_low
