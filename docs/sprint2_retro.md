# Sprint 2 Retrospective & Wrap-Up Report

**Epic 02:** Financial Ratio Engine  
**Duration:** Days 08 – 14  
**Story Points Delivered:** 42 SP / 42 SP (100% Velocity)  
**Database Output:** `financial_ratios` table in `data/nifty100.db` (1,155 rows)  
**Supporting Deliverables:** `output/capital_allocation.csv`, `output/ratio_edge_cases.log`, `output/sector_roce_notes.csv`  
**Test Suite:** 207 Unit Tests (100% Green, 0 Failures)  
**Status:** **SPRINT 2 COMPLETED & SIGNED OFF**

---

## 1. Sprint Goal & Definition of Done Evaluation

| Exit Gate | Acceptance Criterion | Target | Actual Result | Status |
|---|---|---|---|---|
| **AC-04** | Ratio Table Row Count | $\ge 1,100$ rows | **1,155 rows** across 92 companies | **PASSED** |
| **AC-05** | Computed KPI Coverage | 50+ financial KPIs | **50+ KPIs computed across all years** | **PASSED** |
| **AC-06** | Spot-Check Accuracy | Diff $< 0.1\%$ vs manual | **$< 0.0002\%$ error across TCS, INFY, ITC** | **PASSED** |
| **AC-07** | Bank/NBFC Carve-Outs | D/E & ROCE carved out | **100% suppressed / ROA utilized for banks** | **PASSED** |
| **AC-08** | Edge Case Handling | Negative equity, 0 denom, turnaround | **All 6 CAGR flags + sentinel logic active** | **PASSED** |
| **AC-09** | Capital Allocation Classifier | 8-pattern classification | **1,056 rows classified & exported to CSV** | **PASSED** |
| **AC-10** | Screener Sanity Check | $15 \le N \le 50$ (ROE $> 15\%$, D/E $< 1$) | **36 quality compounders returned** | **PASSED** |
| **AC-20** | Unit Test Coverage | All KPI tests green | **207 Tests Passed, 0 Failures** | **PASSED** |

---

## 2. Daily Deliverables Summary (Days 08 – 14)

- **Day 08 (Profitability Ratios):**
  - Built `src/analytics/ratios.py`: NPM, OPM, ROE, ROCE, ROA.
  - Implemented negative net-worth ROE carve-out (`None`), zero sales NPM/OPM guards.
  - Integrated OPM cross-check comparison with automated logger warning on diff $> 1\%$.
  - 8 unit tests created.
- **Day 09 (Leverage & Efficiency Ratios):**
  - Added Debt-to-Equity: debt-free companies return `0.0` (not `None`).
  - Implemented `high_leverage_flag`: triggered if D/E $> 5.0$ and NOT in Financials sector.
  - Added Interest Coverage Ratio: returns `None` if interest is zero; stores `'Debt Free'` in `icr_label`.
  - Added `icr_warning_flag`: True if ICR $< 1.5$.
  - Added Net Debt (`borrowings - investments`) and Asset Turnover (`sales / total_assets`).
- **Day 10 (CAGR Engine — Growth Metrics):**
  - Built `src/analytics/cagr.py`: 1Y, 3Y, 5Y, 10Y multi-period CAGR calculations for Revenue, PAT, and EPS.
  - Handled all 6 edge cases with explicit status flags:
    1. Normal growth: computed $((end/start)^{1/n} - 1) \times 100$.
    2. Decline to loss (positive $\to$ negative): `None` with `DECLINE_TO_LOSS`.
    3. Turnaround (negative $\to$ positive): `None` with `TURNAROUND`.
    4. Both negative: `None` with `BOTH_NEGATIVE`.
    5. Zero base: `None` with `ZERO_BASE`.
    6. Insufficient history ($< n$ years, e.g., JIOFIN): `None` with `INSUFFICIENT`.
  - 10 unit tests created.
- **Day 11 (Cash Flow KPIs & Capital Allocation):**
  - Implemented Free Cash Flow (`CFO + CFI`, allows negative values).
  - Implemented CFO Quality Score (rolling 5-year average of `CFO / PAT` with bands: $> 1.0$ High Quality, $0.5 - 1.0$ Moderate, $< 0.5$ Accrual Risk).
  - Implemented CapEx Intensity (`|CFI| / sales * 100` with labels: $< 3\%$ Asset Light, $3 - 8\%$ Moderate, $> 8\%$ Capital Intensive).
  - Implemented FCF Conversion Rate (`FCF / operating_profit * 100`).
  - Built `src/analytics/cashflow.py`: 8-pattern Capital Allocation classifier $(s_{\text{CFO}}, s_{\text{CFI}}, s_{\text{CFF}})$:
    - `(+,-,-)` $\to$ Reinvestor / Shareholder Returns
    - `(+,+,-)` $\to$ Liquidating Assets
    - `(-,+,+)` $\to$ Distress Signal
    - `(-,-,+)` $\to$ Growth Funded by Debt
    - `(+,+,+)` $\to$ Cash Accumulator
    - `(-,-,-)` $\to$ Pre-Revenue
    - `(+,-,+)` $\to$ Mixed
  - Generated `output/capital_allocation.csv` (1,056 rows).
- **Day 12 (Populate financial_ratios Table):**
  - Upgraded data loader to full outer union across P&L, Balance Sheet, and Cash Flow tables $\to$ expanded table to 1,155 rows.
  - Implemented Composite Financial Health Score ($0 - 100$) following Section 25.1 weights:
    - Profitability (35%): ROE, ROCE, NPM
    - Cash Quality (30%): FCF positivity, CFO/PAT quality, FCF flag
    - Growth (20%): 5Y Revenue CAGR, 5Y PAT CAGR
    - Leverage (15%): D/E scale, ICR scale
  - Verified manual spot checks for TCS, INFY, ITC: difference $< 0.0002\%$.
- **Day 13 (Bank ROCE Carve-Out & Edge Case Log):**
  - Verified `high_leverage_flag` suppression across all 272 Financials sector rows (0 false positives).
  - Suppressed corporate ROCE for banks/NBFCs to `None`, utilizing ROA for banking profitability.
  - Built `src/analytics/edge_cases.py` and generated `output/ratio_edge_cases.log` and `output/sector_roce_notes.csv`.
  - Categorized all discrepancies: Data Source Issue (11), Formula Discrepancy (28), Version Difference (28).
  - Discovered and documented TCS ROE unscaled decimal source anomaly (`0.52` vs `50.94%`).
- **Day 14 (Tests & Sprint Review):**
  - Ran full test suite: **207 unit tests passed with 0 failures** in 12.74s.
  - Executed screener preview: ROE $> 15\%$ and D/E $< 1.0$ returned **36 high-conviction quality compounders**.
  - Documented 5-company multi-sector demo.

---

## 3. Engineering Decisions & Edge Case Knowledge Base

| Metric / Area | Issue / Boundary Condition | Architectural Decision & Solution |
|---|---|---|
| **Negative Net Worth (ROE)** | Negative net worth and negative profit mathematically invert to positive ROE, misleading analysts. | ROE formula enforces `net_worth <= 0 -> return None`. |
| **Debt-Free Companies (D/E & ICR)** | `borrowings = 0` causes zero denominator in D/E or zero interest in ICR. | D/E explicitly returns `0.0`. ICR returns `None` and stores `'Debt Free'` in `icr_label`. `high_leverage_flag` and `icr_warning_flag` remain `False`. |
| **Bank Capital Structures** | Banks/NBFCs have high D/E ($> 5$) and liabilities composed of customer deposits. | Standard D/E flags are suppressed (`is_financial = True -> False`). ROCE is carved out (`None`); Return on Assets (ROA) is used as primary sector benchmark. |
| **CAGR Base Year Anomalies** | Negative start or end values cause complex roots or misleading growth signs. | Six explicit CAGR flags implemented (`TURNAROUND`, `DECLINE_TO_LOSS`, `BOTH_NEGATIVE`, `ZERO_BASE`, `INSUFFICIENT`, `NORMAL`). Values set to `None` for non-standard transitions to avoid distorted ranking. |
| **Young Companies (JIOFIN)** | Listed in 2023, has $< 3$ years of trading history. | Multi-year CAGRs (3Y, 5Y, 10Y) return `None` with `INSUFFICIENT` flag; 1Y CAGR computed normally. |
| **Source Data Scale Errors (TCS, BEL, HAL)** | Source `companies.xlsx` had `0.52` for TCS ROE; balance sheets for BEL/HAL had different unit scales. | Computed ratio engine metrics are treated as primary for analytics and screening; source snapshot values retained for display only. |

---

## 4. Sprint Board Status

| Item ID | Description | Story Points | Status |
|---|---|---|---|
| **SP2-01** | Profitability Ratios & OPM Cross-Check (`ratios.py`) | 6 SP | **DONE** |
| **SP2-02** | Leverage & Efficiency KPIs (`ratios.py`) | 6 SP | **DONE** |
| **SP2-03** | Multi-period CAGR Engine (`cagr.py`) | 6 SP | **DONE** |
| **SP2-04** | Cash Flow KPIs & 8-Pattern Classifier (`cashflow.py`) | 6 SP | **DONE** |
| **SP2-05** | Populate `financial_ratios` table & Composite Score | 6 SP | **DONE** |
| **SP2-06** | Bank ROCE Carve-Out & Edge Case Audit (`edge_cases.py`) | 6 SP | **DONE** |
| **SP2-07** | Unit Testing, Screener Verification & Sprint Wrap-Up | 6 SP | **DONE** |
| **Total** | **Sprint 2 Complete** | **42 SP** | **100% COMPLETE** |

---

## 5. Next Steps — Sprint 3: Screener, Scoring & Sector Analytics (Days 15 – 21)
- **Day 15:** Implement Investment Screener Core Engine (`src/analytics/screener/`).
- **Day 16:** Build 6 Preset Screeners (Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, Turnaround Watch).
- **Day 17:** Implement Custom Screener query builder with multi-parameter filtering.
- **Day 18:** Implement Financial Health Score & 5 risk bands (Strong, Good, Fair, Weak, Distressed).
- **Day 19:** Build Sector Analytics Module & compute sector medians across 11 broad sectors.
- **Day 20:** Implement Peer Comparison Percentiles across 11 peer groups.
- **Day 21:** Export `screener_output.xlsx` and Sprint 3 Retrospective.
