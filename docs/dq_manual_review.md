# Data Quality Manual Review Report (Day 06)

**Sprint:** Sprint 1 — Data Foundation  
**Date:** November 2026  
**Auditor:** Data Engineering Team  
**Database:** `data/nifty100.db`  
**Status:** **APPROVED / SIGNED OFF**

---

## 1. Executive Summary
A comprehensive manual data quality audit was conducted across the 92 Nifty 100 constituents loaded into `nifty100.db`. 
- **Universe Integrity:** 92/92 companies present in `companies` master table.
- **Relational Integrity:** `PRAGMA foreign_key_check` executed $\rightarrow$ **0 violations**.
- **Time Coverage Gate (AC-02):** **95.7%** of companies have $\ge 10$ years of P&L history (minimum required $\ge 90\%$).
- **Sample Deep-Dive:** 5 companies across 5 distinct sectors audited across P&L, Balance Sheet, and Cash Flow tables with 100% data fidelity vs raw filings.

---

## 2. Year Coverage Distribution Across 92 Companies

| Table | Total Companies | $\ge 10$ Years Coverage | 5–9 Years Coverage | $<5$ Years Coverage | Pass Gate |
|---|---|---|---|---|---|
| **`profitandloss`** | 92 | **88 (95.7%)** | 3 (`ADANIGREEN`, `ATGL`, `LICI`) | 1 (`JIOFIN`) | **PASS ($\ge 90\%$)** |
| **`balancesheet`** | 92 | **87 (94.6%)** | 3 (`ADANIGREEN`, `ATGL`, `LICI`) | 1 (`JIOFIN`) | **PASS ($\ge 90\%$)** |
| **`cashflow`** | 92 | **85 (92.4%)** | 5 (`ADANIGREEN`, `HAL`, `IRFC`, `LICI`, `LODHA`) | 1 (`JIOFIN`) | **PASS ($\ge 90\%$)** |

### Analysis of Companies with $<5$ Years (Rule DQ-16)
- **`JIOFIN` (Jio Financial Services Ltd):**
  - **Filing History:** 2 years (`2023-03`, `2024-03`).
  - **Root Cause:** Demerged from Reliance Industries and publicly listed in August 2023. Historical stand-alone statements prior to FY23 do not exist.
  - **Action Required:** Flagged under rule `DQ-16` (WARNING). Per specification, `JIOFIN` will be excluded from 3-year/5-year/10-year CAGR calculations in the Ratio Engine (Sprint 2) while retaining current-year profile metrics.

---

## 3. Deep-Dive Manual Audit — 5 Diverse Companies

### 1. Tata Consultancy Services Ltd (`TCS`) — Information Technology
- **Year Coverage:** 12 yrs P&L, 13 yrs Balance Sheet, 12 yrs Cash Flow, 16 Annual Reports, 60 Monthly Price records.
- **FY24 Statement Audit (Values in ₹ Crore):**
  - **P&L:** Sales = ₹240,893 | Operating Profit = ₹64,296 | OPM = 26.7% | Net Profit = ₹46,099 | EPS = ₹127.0
  - **Balance Sheet:** Equity Capital = ₹362 | Reserves = ₹90,127 | Total Assets = ₹145,472 | Total Liabilities = ₹145,472 (Exact $\Delta = 0$)
  - **Cash Flow:** CFO = ₹44,338 | CFI = ₹6,091 | CFF = -₹48,536 | Net Cash Flow = ₹1,893 (Sum balance verified)
- **Status:** **VERIFIED (100% Clean)**

### 2. HDFC Bank Ltd (`HDFCBANK`) — Financials (Private Banks)
- **Year Coverage:** 12 yrs P&L, 12 yrs Balance Sheet, 12 yrs Cash Flow, 16 Annual Reports, 60 Monthly Price records.
- **FY24 Statement Audit (Values in ₹ Crore):**
  - **P&L:** Sales = ₹283,649 | Operating Profit = ₹174,196 | Net Profit = ₹65,446 | EPS = ₹84.0
  - **Balance Sheet:** Equity Capital = ₹760 | Reserves = ₹455,636 | Borrowings = ₹3,107,503 | Total Assets = ₹4,030,194 | Total Liabilities = ₹4,030,194 (Exact $\Delta = 0$)
  - **Cash Flow:** CFO = ₹19,069 | CFI = ₹16,600 | CFF = -₹3,983 | Net Cash Flow = ₹31,687
- **Findings & Anomaly Notes:**
  - Source `opm_percentage` column contained negative value (`-44685`) due to Screener scraping financing margin convention for merged entities. Correctly caught by `DQ-05` (WARNING). The Ratio Engine will compute bank metrics using NIM and ROA per Section 28 guidelines.
- **Status:** **VERIFIED (DQ-05 Warning expected and logged)**

### 3. Reliance Industries Ltd (`RELIANCE`) — Energy (Oil & Gas)
- **Year Coverage:** 12 yrs P&L, 13 yrs Balance Sheet, 12 yrs Cash Flow, 16 Annual Reports, 60 Monthly Price records.
- **FY24 Statement Audit (Values in ₹ Crore):**
  - **P&L:** Sales = ₹899,041 | Operating Profit = ₹162,498 | OPM = 18.0% | Net Profit = ₹79,020 | EPS = ₹51.0
  - **Balance Sheet:** Equity Capital = ₹6,766 | Reserves = ₹786,715 | Borrowings = ₹458,991 | Total Assets = ₹1,755,048 | Total Liabilities = ₹1,755,048 (Exact $\Delta = 0$)
  - **Cash Flow:** CFO = ₹158,788 | CFI = -₹113,581 | CFF = -₹16,646 | Net Cash Flow = ₹28,561
- **Status:** **VERIFIED (100% Clean)**

### 4. Maruti Suzuki India Ltd (`MARUTI`) — Consumer Discretionary (Automobiles)
- **Year Coverage:** 12 yrs P&L, 13 yrs Balance Sheet, 12 yrs Cash Flow, 16 Annual Reports, 60 Monthly Price records.
- **FY24 Statement Audit (Values in ₹ Crore):**
  - **P&L:** Sales = ₹141,858 | Operating Profit = ₹18,626 | OPM = 13.1% | Net Profit = ₹13,488 | EPS = ₹429.0
  - **Balance Sheet:** Equity Capital = ₹157 | Reserves = ₹85,479 | Borrowings = ₹119 | Total Assets = ₹115,304 | Total Liabilities = ₹115,304 (Exact $\Delta = 0$)
  - **Cash Flow:** CFO = ₹16,801 | CFI = -₹11,865 | CFF = -₹4,062 | Net Cash Flow = ₹874
- **Status:** **VERIFIED (100% Clean)**

### 5. Sun Pharmaceutical Industries Ltd (`SUNPHARMA`) — Healthcare (Pharmaceuticals)
- **Year Coverage:** 12 yrs P&L, 13 yrs Balance Sheet, 12 yrs Cash Flow, 16 Annual Reports, 60 Monthly Price records.
- **FY24 Statement Audit (Values in ₹ Crore):**
  - **P&L:** Sales = ₹48,497 | Operating Profit = ₹13,018 | OPM = 27.5% | Net Profit = ₹9,610 | EPS = ₹40.0
  - **Balance Sheet:** Equity Capital = ₹240 | Reserves = ₹63,427 | Borrowings = ₹3,274 | Total Assets = ₹85,308 | Total Liabilities = ₹85,308 (Exact $\Delta = 0$)
  - **Cash Flow:** CFO = ₹12,135 | CFI = -₹763 | CFF = -₹6,710 | Net Cash Flow = ₹4,662
- **Status:** **VERIFIED (100% Clean)**

---

## 4. DQ Rules Summary & Loader Health

1. **CRITICAL Rules (0 Failures Remaining in Database):**
   - `DQ-01` (Company PK Uniqueness): 92 unique companies.
   - `DQ-02` (Annual PK Uniqueness): All duplicate time-series deduplicated (last occurrence preserved).
   - `DQ-03` (FK Integrity): All orphan rows from companies 93–100 rejected.
   - `DQ-07` (Year Format): Non-annual `TTM` records rejected from annual time-series tables.
   - `DQ-08` (Ticker Format): All tickers normalised to uppercase standard strings.

2. **WARNING Rules (Logged & Monitored):**
   - `DQ-04` (BS Balance): 0 imbalances $\ge 1\%$. Strict assets = liabilities holds across all 5 audited samples.
   - `DQ-05` (OPM Cross-Check): Source vs calculated discrepancies flagged for 216 rows, primarily in financial institutions where financing margin differs from EBITDA.
   - `DQ-10` (Non-negative Fixed Assets): Coerced negative values to 0.
   - `DQ-16` (Coverage Check): Only 1 company (`JIOFIN`) flagged with $<5$ years.

---

## 5. Sign-Off Decision
- **Gate AC-01:** Passed (92 companies)
- **Gate AC-02:** Passed (92.4% – 95.7% $\ge 10$ years)
- **Gate AC-03:** Passed (`PRAGMA foreign_key_check` = 0)
- **Verdict:** **Data Foundation Quality Approved for Sprint 1 Wrap-up.**
