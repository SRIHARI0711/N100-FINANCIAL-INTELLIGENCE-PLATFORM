# Sprint 1 Retrospective & Wrap-Up Report

**Epic 01:** Data Ingestion & ETL  
**Duration:** Days 01 – 07  
**Story Points Delivered:** 34 SP / 34 SP (100% Velocity)  
**Database Output:** `data/nifty100.db`  
**Test Suite:** 81 Unit Tests (100% Green, 0 Failures)  
**Status:** **SPRINT 1 COMPLETED & SIGNED OFF**

---

## 1. Sprint Goal & Definition of Done Evaluation

| Exit Gate | Acceptance Criterion | Target | Actual Result | Status |
|---|---|---|---|---|
| **AC-01** | Data Coverage: Total Companies | 92 Companies | **92 Companies** | **PASSED** |
| **AC-02** | Time Coverage: Companies with $\ge 10$ Yrs | $\ge 90\%$ | **92.4% – 95.7%** | **PASSED** |
| **AC-03** | Schema Relational Integrity | 0 FK Violations | **0 Violations (`PRAGMA foreign_key_check`)** | **PASSED** |
| **AC-18** | Unit Test Coverage | $\ge 35$ Tests, 0 Failures | **81 Tests Passed, 0 Failures** | **PASSED** |
| **AC-19** | Data Quality Documentation | `validation_failures.csv` exists | **Generated (`output/validation_failures.csv`)** | **PASSED** |
| **D-02** | Load Audit Completeness | `load_audit.csv` exists | **Generated (`output/load_audit.csv`)** | **PASSED** |
| **D-04** | Exploratory SQL Queries | $\ge 10$ Valid Queries | **10 Queries Tested & Verified (`notebooks/`)** | **PASSED** |

---

## 2. Daily Deliverables Summary (Days 01 – 07)

- **Day 01 (Environment Setup):**
  - Scaffolded standard 20-directory project architecture (`data/`, `src/`, `tests/`, `config/`, `reports/`, `output/`, `docs/`).
  - Created `.venv` with Python 3.13, installed all 22 required libraries.
  - Built `.env.template`, `.env`, `Makefile`, and `run.ps1` helper.
- **Day 02 (Excel Loader & Normaliser):**
  - Built `src/etl/normaliser.py`: `normalize_year()` handling 14 fiscal year notation patterns + `normalize_ticker()`.
  - Built `src/etl/loader.py`: Support for `header=1` on core files and `header=0` on supplementary files.
  - Implemented 55 unit tests.
- **Day 03 (Schema Validator — 16 DQ Rules):**
  - Built `src/etl/validator.py` implementing rules `DQ-01` through `DQ-16`.
  - Generated `output/validation_failures.csv` categorising 732 Critical and 317 Warning findings.
  - Implemented 17 validation unit tests (`tests/dq/test_rules.py`).
- **Day 04 (SQLite Database Schema):**
  - Built `db/schema.sql`: 12 relational tables with foreign keys and unique composite indices.
  - Implemented `db/loader.py` with `PRAGMA foreign_keys = ON;`.
  - Added `tests/etl/test_schema.py` verifying FK violation rejection and annual PK deduplication.
- **Day 05 (Full Data Load — 12 Files):**
  - Executed full database ingestion: 92 companies, 1,073 P&L rows, 1,140 Balance Sheet rows, 1,056 Cash Flow rows, 5,520 stock prices.
  - Generated `output/load_audit.csv`.
- **Day 06 (Data Quality Manual Review):**
  - Conducted deep spot checks on 5 diverse companies (`TCS`, `HDFCBANK`, `RELIANCE`, `MARUTI`, `SUNPHARMA`).
  - Analyzed and documented single company with $<5$ years (`JIOFIN`).
  - Generated formal review artifact: `docs/dq_manual_review.md`.
- **Day 07 (Sprint Wrap-Up & Review):**
  - Authored `notebooks/exploratory_queries.sql` (10 tested queries).
  - Authored `query.py` CLI query tool for instant analysis.
  - Final test run: **81/81 passed**.

---

## 3. Engineering Challenges & Solutions

| Challenge Encountered | Root Cause | Engineering Solution Implemented |
|---|---|---|
| **OneDrive Permission Boundary** | Reparse points in OneDrive directory caused permission errors. | Executed commands via direct PowerShell environment runners with full file system access. |
| **Excel Dual-Header Structures** | Core files used Row 0 for metadata and Row 1 for headers; supplementary files used Row 0. | Engineered `loader.py` with explicit `header=1` for core files and `header=0` for supplementary files. |
| **Orphan Child Rows** | Child tables had rows for companies 93–100 (`WIPRO`, `ZOMATO`, `VEDL`, etc.) outside the 92 universe. | `DQ-03` FK filter rejects orphan child rows before insertion, ensuring 100% database foreign key compliance. |
| **Bank OPM Calculation Divergences** | Bank financing profit formats produced negative OPM numbers in source data. | Handled via `DQ-05` (WARNING flag) with NIM/ROA routing in Ratio Engine. |
| **TVSMOTOR Missing Face Value** | Raw Excel row had `NaN` for `face_value`. | Updated schema constraint to allow nullable face value and default to 1. |
| **Multi-line Command Prompt pasting** | Classic Windows `cmd.exe` does not handle multi-line string commands. | Created `query.py` script and automated `run.ps1` runner. |

---

## 4. Sprint Board Status

| Item ID | Description | Story Points | Status |
|---|---|---|---|
| **SP1-01** | Directory layout, venv setup, dependencies | 3 SP | **DONE** |
| **SP1-02** | Excel loaders & normalisers (`loader.py`, `normaliser.py`) | 5 SP | **DONE** |
| **SP1-03** | 16 Data Quality rules & `validation_failures.csv` | 6 SP | **DONE** |
| **SP1-04** | SQLite schema & FK constraints (`db/schema.sql`) | 5 SP | **DONE** |
| **SP1-05** | Full load of 12 datasets & `load_audit.csv` | 6 SP | **DONE** |
| **SP1-06** | Manual DQ audit of 5 companies & coverage verification | 5 SP | **DONE** |
| **SP1-07** | Exploratory SQL queries & sprint wrap-up | 4 SP | **DONE** |
| **Total** | **Sprint 1 Complete** | **34 SP** | **100% COMPLETE** |

---

## 5. Next Steps — Sprint 2: Financial Ratio Engine (Days 08 – 14)
- **Day 08:** Implement Profitability ratios: NPM, OPM, ROE, ROCE (negative equity edge cases, zero sales carve-outs).
- **Day 09:** Implement Leverage & Efficiency ratios: D/E (bank carve-out), Interest Coverage (debt-free substitution), Asset Turnover.
- **Day 10:** Implement CAGR Engine: 3Y, 5Y, 10Y Revenue, PAT, EPS CAGRs with turnaround detection.
- **Day 11:** Implement Cash Flow KPIs: FCF, CFO Quality Score, CapEx Intensity, Capital Allocation patterns (8 classes).
- **Day 12:** Populate `financial_ratios` table in SQLite for all 92 companies $\times$ 14 years.
- **Day 13:** Implement Bank/NBFC ROCE adjustments.
- **Day 14:** Run full KPI test suite and sprint retrospective.
