# N100 Financial Intelligence Platform

Production-grade fundamental analytics and intelligence platform for all 92 Nifty 100 companies.

## Overview
The **N100 Financial Intelligence Platform** processes over a decade of financial statements across P&L, Balance Sheet, Cash Flow, and Supplementary Market data to provide automated financial intelligence, including:
- **Unified SQLite Data Warehouse** (`nifty100.db`) with 10 structured tables.
- **Financial Ratio Engine** computing 30+ fundamental KPIs across 14 fiscal years.
- **Investment Screener** with 18 configurable filters and 6 institutional presets.
- **Composite Financial Health Score (0–100)** with 5 risk bands.
- **Sector & Peer Analytics** across 11 broad sectors and 11 peer groups.
- **Automated Reporting Suite** delivering 92 company tearsheets, 11 sector reports, and an all-universe summary.
- **Interactive Streamlit Web Dashboard** and **FastAPI REST Service**.

---

## Architecture & Directory Structure

```
N100 FINANCIAL INTELLIGENCE PLATFORM/
├── config/                  # Configuration files
│   ├── .env.template        # Template environment variables
│   ├── logging_config.yaml  # Standard logging configuration
│   └── screener_config.yaml # Screener rules & threshold definitions
├── data/
│   ├── raw/                 # 7 Core Excel datasets (P&L, BS, Cashflow, etc.)
│   ├── supporting/          # 5 Supplementary Excel datasets (Sectors, Prices, etc.)
│   └── nifty100.db          # Unified SQLite database
├── docs/                    # Project documentation & reference PDFs
├── notebooks/               # Exploratory data analysis notebooks
├── output/                  # Audit logs, screener exports & failure reports
├── reports/                 # Generated PDF tearsheets, sector reports & charts
│   ├── portfolio/
│   ├── radar_charts/
│   ├── sector/
│   └── tearsheets/
├── src/
│   ├── analytics/           # KPI calculations, CAGR, scoring, clustering
│   ├── api/                 # FastAPI REST API endpoints
│   ├── dashboard/           # Streamlit multi-page web application
│   ├── etl/                 # Excel loaders, normalisers, DQ validators, schema
│   ├── nlp/                 # Qualitative text processing & pros/cons generator
│   └── reports/             # Automated ReportLab PDF generator
├── tests/                   # Pytest test suite (ETL, KPI, API, DQ)
├── .env                     # Local environment settings
├── .gitignore               # Ignored files for version control
├── Makefile                 # Automation targets (load, ratios, test, dashboard, api)
├── run.ps1                  # PowerShell automation helper for Windows
├── README.md                # Platform documentation
└── requirements.txt         # Pinned python dependencies
```

---

## Quick-Start Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.10 – 3.13)
- Windows PowerShell or Unix Shell

### 2. Environment Setup
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.template` to `.env` (already created by setup):
```ini
DB_PATH=data/nifty100.db
PORT=8000
LOG_LEVEL=INFO
SIMULATED_DATA_FLAG=True
```

---

## Makefile / Script Commands

| Task | Makefile Command | PowerShell Command | Description |
|---|---|---|---|
| Load ETL | `make load` | `.\run.ps1 load` | Loads & validates 12 datasets into `nifty100.db` |
| Compute KPIs | `make ratios` | `.\run.ps1 ratios` | Computes 30+ financial ratios and populates database |
| Run Tests | `make test` | `.\run.ps1 test` | Executes full pytest suite and generates HTML report |
| Reports | `make report` | `.\run.ps1 report` | Generates 103 PDF reports (92 tearsheets + 11 sector) |
| Dashboard | `make dashboard` | `.\run.ps1 dashboard` | Launches Streamlit web app on `http://localhost:8501` |
| REST API | `make api` | `.\run.ps1 api` | Launches FastAPI server on `http://localhost:8000/docs` |
| Clean | `make clean` | `.\run.ps1 clean` | Removes cache files and temporary artifacts |
