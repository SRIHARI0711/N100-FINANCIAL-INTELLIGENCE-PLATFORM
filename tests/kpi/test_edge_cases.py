"""
tests/kpi/test_edge_cases.py
Sprint 2 — Day 13: Unit tests for Bank ROCE Carve-Out & Ratio Edge Case Log.

Covers:
  1. Financials sector D/E warning flag is suppressed across all rows
  2. Financials sector ROCE carve-out (None for banks/NBFCs, ROA used instead)
  3. TCS ROE source anomaly detection (0.52 in source vs ~50.94% computed)
  4. Cross-check anomaly classification (Data Source Issue, Version Difference, Formula Discrepancy)
  5. output/ratio_edge_cases.log and output/sector_roce_notes.csv existence and integrity
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analytics.edge_cases import (
    CAT_DATA_SOURCE_ISSUE,
    CAT_FORMULA_DISCREPANCY,
    CAT_VERSION_DIFFERENCE,
    LOG_PATH,
    NOTES_CSV_PATH,
    cross_check_and_log_edge_cases,
)
from src.analytics.ratios import high_leverage_flag, return_on_capital_employed

DB_PATH = BASE_DIR / "data" / "nifty100.db"


class TestDay13BankCarveOutAndEdgeCases:
    """Sprint 2 Day 13 acceptance criteria unit tests."""

    def test_01_financials_de_flag_suppressed_in_ratios_function(self):
        """1. High leverage flag is suppressed for Financials companies even if D/E is high."""
        # Non-financial with D/E > 5 -> True
        assert high_leverage_flag(debt_to_equity_val=7.5, is_financial=False) is True
        # Financial with D/E > 5 -> False (structurally normal)
        assert high_leverage_flag(debt_to_equity_val=7.5, is_financial=True) is False
        assert high_leverage_flag(debt_to_equity_val=12.0, is_financial=True) is False

    def test_02_financials_de_suppression_verified_in_database(self):
        """2. Verify that 0 rows in financial_ratios for Financials broad_sector have high_leverage_flag = 1."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("""
            SELECT COUNT(*)
            FROM financial_ratios fr
            JOIN sectors s ON fr.company_id = s.company_id
            WHERE s.broad_sector = 'Financials' AND fr.high_leverage_flag = 1
        """)
        flagged_count = cur.fetchone()[0]
        conn.close()
        assert flagged_count == 0, f"Expected 0 Financials rows with high_leverage_flag=1, found {flagged_count}"

    def test_03_financials_roce_carve_out(self):
        """3. Bank/NBFC ROCE carve-out: returns None or sector_benchmark, never corporate EBIT/Capital."""
        # Bank with is_financial=True -> returns None when no sector_benchmark given
        result = return_on_capital_employed(
            operating_profit=5000.0,
            other_income=200.0,
            equity_capital=1000.0,
            reserves=20000.0,
            borrowings=80000.0,
            is_financial=True,
        )
        assert result is None

        # When sector benchmark is supplied, returns benchmark
        result_bm = return_on_capital_employed(
            operating_profit=5000.0,
            is_financial=True,
            sector_benchmark=4.25,
        )
        assert result_bm == pytest.approx(4.25)

    def test_04_tcs_roe_source_anomaly(self):
        """4. TCS source roe_percentage shows 0.52 while computed ROE is ~50.94%."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        src_row = conn.execute("SELECT roe_percentage FROM companies WHERE id = 'TCS'").fetchone()
        db_ratio = conn.execute(
            "SELECT return_on_equity_pct FROM financial_ratios WHERE company_id = 'TCS' AND year = '2024-03'"
        ).fetchone()
        conn.close()

        assert src_row["roe_percentage"] == pytest.approx(0.52)
        assert db_ratio["return_on_equity_pct"] == pytest.approx(50.9443, rel=1e-2)
        # Difference > 50%
        diff = abs(db_ratio["return_on_equity_pct"] - src_row["roe_percentage"])
        assert diff > 50.0

    def test_05_edge_case_cross_check_execution_and_log(self):
        """5. Run cross_check_and_log_edge_cases and verify output log and notes CSV."""
        conn = sqlite3.connect(DB_PATH)
        result = cross_check_and_log_edge_cases(conn)
        conn.close()

        assert len(result["roce_anomalies"]) > 0
        assert len(result["roe_anomalies"]) > 0
        assert LOG_PATH.exists()
        assert NOTES_CSV_PATH.exists()

        log_content = LOG_PATH.read_text(encoding="utf-8")
        assert "FINANCIAL INTELLIGENCE PLATFORM — RATIO ENGINE EDGE CASE LOG" in log_content
        assert CAT_DATA_SOURCE_ISSUE in log_content
        assert CAT_FORMULA_DISCREPANCY in log_content
        assert CAT_VERSION_DIFFERENCE in log_content
        assert "TCS" in log_content

        # Verify CSV has Financials rows
        with NOTES_CSV_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) >= 19
            assert all(r["broad_sector"] == "Financials" for r in rows)
