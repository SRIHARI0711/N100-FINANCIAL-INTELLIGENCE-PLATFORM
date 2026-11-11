"""
N100 Financial Intelligence Platform — Sprint 2, Day 08
Ratio Engine: Profitability, Leverage, Efficiency, CAGR, Cash-Flow KPIs.

Populates / updates the `financial_ratios` table in nifty100.db.
All monetary values in ₹ Crore (as stored in source tables).

Run directly:
    python src/analytics/ratios.py

Or via run.ps1:
    .\\run.ps1 ratios
"""

from __future__ import annotations

import logging
import math
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap (so script works both as module and __main__)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.analytics.cagr import FLAG_INSUFFICIENT, calculate_cagr

DB_PATH = BASE_DIR / "data" / "nifty100.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Companies with insufficient history for CAGR (< 3 years)
CAGR_EXCLUDE: set[str] = {"JIOFIN"}

# Broad sector label used to flag banks / NBFCs
FINANCIALS_SECTOR = "Financials"

# Sentinel value for debt-free companies on interest-coverage
DEBT_FREE_COVERAGE = 999.0


# ---------------------------------------------------------------------------
# Pure math helpers
# ---------------------------------------------------------------------------


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
    """Multiply by 100 to convert ratio → percentage."""
    return None if ratio is None else ratio * 100.0


def cagr(start_val: float | None, end_val: float | None, years: int) -> float | None:
    """Compound Annual Growth Rate (%)."""
    return calculate_cagr(start_val, end_val, years).value


# ---------------------------------------------------------------------------
# Profitability KPIs
# ---------------------------------------------------------------------------


def net_profit_margin(net_profit: float | None, sales: float | None) -> float | None:
    """NPM = net_profit / sales × 100.  Returns None when sales ≤ 0."""
    if sales is None or sales <= 0:
        return None
    return _pct(_safe_div(net_profit, sales))


def operating_profit_margin(
    operating_profit: float | None,
    sales: float | None,
    is_financial: bool = False,
    opm_percentage: float | None = None,
    company_id: str | None = None,
    year: str | None = None,
) -> float | None:
    """OPM = operating_profit / sales × 100.  Skipped for Financials sector.

    Cross-checks computed OPM against reported opm_percentage field.
    Logs a warning if difference > 1%.
    """
    if is_financial:
        return None
    if sales is None or sales <= 0 or operating_profit is None:
        return None
    computed = _pct(_safe_div(operating_profit, sales))
    if computed is not None and opm_percentage is not None:
        diff = abs(computed - opm_percentage)
        if diff > 1.0:
            prefix = f"[{company_id} {year}] " if company_id else ""
            log.warning(
                "%sOPM cross-check mismatch: computed %.2f%% vs reported %.2f%% (diff: %.2f%% > 1%%)",
                prefix,
                computed,
                opm_percentage,
                diff,
            )
    return computed


def return_on_equity(
    net_profit: float | None,
    equity_capital: float | None,
    reserves: float | None,
) -> float | None:
    """ROE = net_profit / (equity_capital + reserves) × 100.
    Returns None for negative net-worth (inverted sign is misleading).
    """
    if equity_capital is None or reserves is None:
        return None
    net_worth = (equity_capital or 0.0) + (reserves or 0.0)
    if net_worth <= 0:
        return None
    return _pct(_safe_div(net_profit, net_worth))


def sector_relative_roce_benchmark(
    roce: float | None,
    sector_median: float | None,
) -> float | None:
    """Compute sector-relative ROCE benchmark spread: company ROCE - sector median ROCE.
    Used for Financials broad_sector where absolute ROCE threshold is misleading.
    """
    if roce is None or sector_median is None:
        return None
    return round(roce - sector_median, 4)


def return_on_capital_employed(
    operating_profit: float | None = None,
    other_income: float | None = 0.0,
    arg3: float | None = None,  # total_assets or equity_capital
    arg4: float | None = None,  # other_liabilities or reserves
    arg5: float | None = None,  # borrowings
    is_financial: bool = False,
    *,
    ebit: float | None = None,
    equity_capital: float | None = None,
    reserves: float | None = None,
    borrowings: float | None = None,
    total_assets: float | None = None,
    other_liabilities: float | None = None,
    sector_benchmark: float | None = None,
) -> float | None:
    """ROCE = EBIT / (equity + reserves + borrowings) × 100.

    EBIT             = operating_profit + other_income
    Capital employed = equity + reserves + borrowings
                     ≈ total_assets - other_liabilities   (balance-sheet proxy)

    For companies in Financials broad_sector:
    Uses sector-relative ROCE benchmark instead of absolute threshold.
    Returns sector_benchmark if provided, otherwise None (financials carve-out).
    Returns None if capital employed <= 0.
    """
    if is_financial:
        return sector_benchmark

    if ebit is not None:
        ebit_val = ebit
    elif operating_profit is not None:
        ebit_val = operating_profit + (other_income or 0.0)
    else:
        return None

    # Determine capital employed
    if equity_capital is not None or reserves is not None:
        if equity_capital is None or reserves is None:
            return None
        capital_employed = equity_capital + reserves + (borrowings or 0.0)
    elif total_assets is not None:
        capital_employed = total_assets - (other_liabilities or 0.0)
    elif arg5 is not None:
        # 5 positional arguments: op, oi, equity_capital, reserves, borrowings
        if arg3 is None or arg4 is None:
            return None
        capital_employed = arg3 + arg4 + (arg5 or 0.0)
    elif arg3 is not None:
        # 3 or 4 positional arguments: op, oi, total_assets, [other_liab]
        capital_employed = arg3 - (arg4 or 0.0)
    else:
        return None

    if capital_employed <= 0:
        return None
    return _pct(_safe_div(ebit_val, capital_employed))


def return_on_assets(
    net_profit: float | None,
    total_assets: float | None,
) -> float | None:
    """ROA = net_profit / total_assets × 100.  Used for banks / NBFCs."""
    if total_assets is None or total_assets <= 0:
        return None
    return _pct(_safe_div(net_profit, total_assets))


# ---------------------------------------------------------------------------
# Leverage & Efficiency KPIs
# ---------------------------------------------------------------------------


def debt_to_equity(
    borrowings: float | None,
    equity_capital: float | None,
    reserves: float | None,
    is_financial: bool = False,
) -> float | None:
    """D/E = borrowings / (equity_capital + reserves).
    Skipped for Financials (leverage interpretation differs; use CAR).
    Returns None for negative net-worth.
    Returns 0.0 (not None) if borrowings == 0.
    """
    if is_financial:
        return None
    if equity_capital is None or reserves is None:
        return None
    net_worth = (equity_capital or 0.0) + (reserves or 0.0)
    if net_worth <= 0:
        return None
    if borrowings is not None and borrowings == 0:
        return 0.0
    return _safe_div(borrowings or 0.0, net_worth)


def high_leverage_flag(
    debt_to_equity_val: float | None,
    is_financial: bool = False,
    threshold: float = 5.0,
) -> bool:
    """Return True if D/E > 5 and company is NOT in Financials sector, else False."""
    if is_financial or debt_to_equity_val is None:
        return False
    return debt_to_equity_val > threshold


def interest_coverage(
    operating_profit: float | None,
    other_income: float | None = 0.0,
    interest: float | None = None,
    borrowings: float | None = None,
) -> float | None:
    """Interest Coverage Ratio = (operating_profit + other_income) / interest.
    Returns None if interest == 0 or interest is None.
    If company is debt-free (borrowings == 0) and interest > 0, returns DEBT_FREE_COVERAGE (999.0).
    """
    intr = interest or 0.0
    if intr == 0:
        return None
    borr = borrowings or 0.0
    if borr == 0:
        return DEBT_FREE_COVERAGE
    ebit = (operating_profit or 0.0) + (other_income or 0.0)
    return _safe_div(ebit, intr)


def get_icr_label(
    icr: float | None,
    borrowings: float | None = None,
) -> str | None:
    """Return display label for ICR.
    For ICR = None (debt-free companies where borrowings == 0 or None), stores 'Debt Free'.
    If ICR is DEBT_FREE_COVERAGE (999), stores 'Debt Free'.
    If ICR is numeric, returns formatted string (e.g. '7.00x').
    """
    if icr is None:
        if borrowings is None or borrowings == 0:
            return "Debt Free"
        return None
    if icr == DEBT_FREE_COVERAGE:
        return "Debt Free"
    return f"{icr:.2f}x"


def icr_warning_flag(
    icr: float | None,
    is_financial: bool = False,
    threshold: float = 1.5,
) -> bool:
    """Return True if ICR < 1.5 (company is at risk of not covering interest payments), else False.
    Debt-free companies (ICR is None or 999.0) and Financials sector return False.
    """
    if is_financial or icr is None or icr == DEBT_FREE_COVERAGE:
        return False
    return icr < threshold


def net_debt(
    borrowings: float | None,
    investments: float | None,
) -> float | None:
    """Net Debt = borrowings - investments (using investments as liquid asset proxy).
    Returns None if borrowings is None.
    """
    if borrowings is None:
        return None
    inv = investments or 0.0
    return borrowings - inv


def asset_turnover(
    sales: float | None,
    total_assets: float | None,
) -> float | None:
    """Asset Turnover = sales / total_assets (times).  Returns None if total_assets <= 0."""
    if total_assets is None or total_assets <= 0 or sales is None:
        return None
    return _safe_div(sales, total_assets)


def working_capital(
    other_asset: float | None,
    other_liabilities: float | None,
) -> float | None:
    """Working Capital ≈ current_assets - current_liabilities
    (best proxy: other_asset - other_liabilities from balance-sheet).
    """
    ca = other_asset or 0.0
    cl = other_liabilities or 0.0
    return ca - cl


# ---------------------------------------------------------------------------
# Cash-Flow KPIs
# ---------------------------------------------------------------------------


def free_cash_flow(
    operating_activity: float | None,
    investing_activity: float | None,
) -> float | None:
    """FCF = operating_activity + investing_activity.

    investing_activity is typically negative (cash outflow).
    Adding it to CFO gives FCF net of capex.
    """
    if operating_activity is None:
        return None
    inv = investing_activity or 0.0
    return (operating_activity or 0.0) + inv


def capex(investing_activity: float | None) -> float | None:
    """CapEx proxy = abs(investing_activity).
    investing_activity is cash used in investing (usually negative),
    so we negate it to get a positive capex figure.
    """
    if investing_activity is None:
        return None
    return abs(investing_activity)


def cfo_quality_score(
    operating_activity: float | None,
    net_profit: float | None,
) -> float | None:
    """CFO Quality = operating_activity / net_profit (single-year).
    > 1 → earnings are well-backed by cash; < 1 → accrual quality concern.
    Returns None when net_profit == 0 (meaningless ratio).
    """
    return _safe_div(operating_activity, net_profit)


def cfo_quality_score_5yr(
    cfo_series: list[float | None],
    pat_series: list[float | None],
) -> float | None:
    """CFO Quality Score averaged over up to 5 years.

    For each paired (CFO, PAT) year where PAT != 0, computes CFO/PAT.
    Returns the average of valid ratios, or None if no valid pairs.

    Classification bands (see cfo_quality_label):
      > 1.0  → High Quality
      0.5–1.0 → Moderate
      < 0.5  → Accrual Risk
    """
    ratios: list[float] = []
    for cfo, pat in zip(cfo_series, pat_series):
        ratio = _safe_div(cfo, pat)
        if ratio is not None:
            ratios.append(ratio)
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def cfo_quality_label(score: float | None) -> str | None:
    """Classify a CFO quality score into a human-readable band.

    > 1.0  → 'High Quality'
    0.5–1.0 → 'Moderate'
    < 0.5  → 'Accrual Risk'
    Returns None if score is None.
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
    """CapEx Intensity = |investing_activity| / sales × 100."""
    if sales is None or sales <= 0:
        return None
    capex_val = capex(investing_activity)
    return _pct(_safe_div(capex_val, sales))


def capex_intensity_label(capex_intensity_pct: float | None) -> str | None:
    """Classify CapEx Intensity percentage into a capital-structure band.

    < 3%   → 'Asset Light'
    3–8%   → 'Moderate'
    > 8%   → 'Capital Intensive'
    Returns None if input is None.
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
    """FCF Conversion Rate = FCF / operating_profit × 100.

    Measures what fraction of operating profit converts to free cash flow.
    Returns None if operating_profit == 0 or None.
    """
    if operating_profit is None or operating_profit == 0:
        return None
    return _pct(_safe_div(fcf, operating_profit))


def calculate_composite_quality_score(
    roe: float | None = None,
    roce: float | None = None,
    npm: float | None = None,
    fcf: float | None = None,
    cfo_pat_ratio: float | None = None,
    revenue_cagr_5yr: float | None = None,
    pat_cagr_5yr: float | None = None,
    debt_to_equity: float | None = None,
    interest_coverage: float | None = None,
    is_financial: bool = False,
    icr_label: str | None = None,
    roa: float | None = None,
) -> float | None:
    """Compute Composite Financial Health Score (0–100) based on Section 25.1 weights:
    - Profitability (35%): ROE (15%), ROCE (10%), NPM (10%)
    - Cash Quality (30%): FCF > 0 flag (15%), CFO/PAT ratio (10%), FCF positivity (5%)
    - Growth (20%): Revenue CAGR 5yr (10%), PAT CAGR 5yr (10%)
    - Leverage (15%): D/E (10%), ICR (5%)
    """
    if roe is None and roce is None and npm is None and roa is None:
        return None

    # 1. Profitability (35%)
    s_roe = 0.0 if roe is None or roe <= 0 else min(100.0, (roe / 25.0) * 100.0)
    if is_financial:
        s_roce = 0.0 if roa is None or roa <= 0 else min(100.0, (roa / 2.0) * 100.0)
    else:
        s_roce = 0.0 if roce is None or roce <= 0 else min(100.0, (roce / 25.0) * 100.0)
    s_npm = 0.0 if npm is None or npm <= 0 else min(100.0, (npm / 20.0) * 100.0)
    prof = 0.15 * s_roe + 0.10 * s_roce + 0.10 * s_npm

    # 2. Cash Quality (30%)
    s_fcf_flag = 100.0 if fcf is not None and fcf > 0 else 0.0
    s_cfo_pat = (
        0.0
        if cfo_pat_ratio is None or cfo_pat_ratio <= 0
        else min(100.0, (cfo_pat_ratio / 1.0) * 100.0)
    )
    cash = 0.15 * s_fcf_flag + 0.10 * s_cfo_pat + 0.05 * s_fcf_flag

    # 3. Growth (20%)
    s_rev = (
        0.0
        if revenue_cagr_5yr is None or revenue_cagr_5yr <= 0
        else min(100.0, (revenue_cagr_5yr / 20.0) * 100.0)
    )
    s_pat = (
        0.0
        if pat_cagr_5yr is None or pat_cagr_5yr <= 0
        else min(100.0, (pat_cagr_5yr / 25.0) * 100.0)
    )
    if revenue_cagr_5yr is None and pat_cagr_5yr is None:
        growth = 0.20 * ((s_roe + s_npm) / 2.0)
    else:
        growth = 0.10 * s_rev + 0.10 * s_pat

    # 4. Leverage (15%)
    if is_financial:
        s_de = 85.0
    elif debt_to_equity is None or debt_to_equity <= 0:
        s_de = 100.0
    elif debt_to_equity <= 0.5:
        s_de = 100.0 - (debt_to_equity / 0.5) * 15.0
    elif debt_to_equity <= 1.0:
        s_de = 85.0 - ((debt_to_equity - 0.5) / 0.5) * 15.0
    elif debt_to_equity <= 2.0:
        s_de = 70.0 - ((debt_to_equity - 1.0) / 1.0) * 20.0
    elif debt_to_equity <= 5.0:
        s_de = max(0.0, 50.0 - ((debt_to_equity - 2.0) / 3.0) * 50.0)
    else:
        s_de = 0.0

    if is_financial or icr_label == "Debt Free":
        s_icr = 100.0
    elif interest_coverage is None:
        s_icr = 50.0
    elif interest_coverage >= 10.0:
        s_icr = 100.0
    elif interest_coverage >= 5.0:
        s_icr = 75.0 + ((interest_coverage - 5.0) / 5.0) * 25.0
    elif interest_coverage >= 3.0:
        s_icr = 50.0 + ((interest_coverage - 3.0) / 2.0) * 25.0
    elif interest_coverage >= 1.5:
        s_icr = max(0.0, ((interest_coverage - 1.5) / 1.5) * 50.0)
    else:
        s_icr = 0.0
    lev = 0.10 * s_de + 0.05 * s_icr

    return round(prof + cash + growth + lev, 2)


def book_value_per_share(
    equity_capital: float | None,
    reserves: float | None,
    face_value: float | None,
) -> float | None:
    """BVPS = net_worth / (equity_capital / face_value × 100).

    Shares outstanding (in Crore) ≈ equity_capital (₹ Cr) / face_value × 100
    because equity_capital is in ₹ Crore and face_value in ₹.
    """
    if (
        equity_capital is None
        or equity_capital == 0
        or face_value is None
        or face_value == 0
    ):
        return None
    net_worth = (equity_capital or 0.0) + (reserves or 0.0)
    if net_worth <= 0:
        return None
    # shares in Crore units
    shares_cr = equity_capital / face_value * 100
    # BVPS in ₹
    return _safe_div(
        net_worth * 1e7, shares_cr * 1e7
    )  # simplifies to net_worth/shares_cr


# ---------------------------------------------------------------------------
# CAGR engine — multi-period
# ---------------------------------------------------------------------------


def _cagr_series(
    rows: list[tuple],  # (year_str, value)
    target_years: list[int],
    company_id: str,
    include_flags: bool = False,
) -> dict[str, float | str | None]:
    """Compute CAGRs for 1Y, 3Y, 5Y, 10Y from a sorted (year, value) series.

    rows must be sorted ascending by year.
    Returns dict keyed by e.g. 'cagr_1y', 'cagr_3y', 'cagr_5y', 'cagr_10y'.
    If include_flags=True, also includes flag columns like 'cagr_3y_flag'.
    """
    result: dict[str, float | str | None] = {}
    valid_rows = [(y, v) for y, v in rows if v is not None]

    for yrs in target_years:
        key = f"cagr_{yrs}y"
        key_alias = f"cagr_{yrs}yr"
        flag_key = f"cagr_{yrs}y_flag"
        flag_alias = f"cagr_{yrs}yr_flag"

        if company_id in CAGR_EXCLUDE and yrs > 1:
            result[key] = None
            result[key_alias] = None
            if include_flags:
                result[flag_key] = FLAG_INSUFFICIENT
                result[flag_alias] = FLAG_INSUFFICIENT
            continue
        if len(valid_rows) <= yrs:
            result[key] = None
            result[key_alias] = None
            if include_flags:
                result[flag_key] = FLAG_INSUFFICIENT
                result[flag_alias] = FLAG_INSUFFICIENT
            continue

        end_val = valid_rows[-1][1]
        start_val = valid_rows[-(yrs + 1)][1]
        cagr_res = calculate_cagr(start_val, end_val, yrs)
        result[key] = cagr_res.value
        result[key_alias] = cagr_res.value
        if include_flags:
            result[flag_key] = cagr_res.flag
            result[flag_alias] = cagr_res.flag

    return result


# ---------------------------------------------------------------------------
# Database I/O helpers
# ---------------------------------------------------------------------------


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _load_financial_sector_ids(conn: sqlite3.Connection) -> set[str]:
    """Return set of company_ids in the Financials broad_sector."""
    cur = conn.execute(
        "SELECT company_id FROM sectors WHERE broad_sector = ?",
        (FINANCIALS_SECTOR,),
    )
    return {r["company_id"] for r in cur.fetchall()}


def _load_face_values(conn: sqlite3.Connection) -> dict[str, float | None]:
    """Return {company_id: face_value} for all companies."""
    cur = conn.execute("SELECT id, face_value FROM companies")
    return {r["id"]: r["face_value"] for r in cur.fetchall()}


def _load_merged_data(conn: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    """Load merged P&L + BS + CF rows per company, keyed by company_id.

    Returns dict: { company_id: [Row, ...] } sorted ascending by year.
    Uses CTE over all distinct (company_id, year) across P&L, Balance Sheet,
    and Cash Flow tables to ensure complete coverage (1,100+ rows).
    """
    sql = """
    WITH all_pairs AS (
        SELECT company_id, year FROM profitandloss
        UNION
        SELECT company_id, year FROM balancesheet
        UNION
        SELECT company_id, year FROM cashflow
    )
    SELECT
        ap.company_id,
        ap.year,
        pl.sales,
        pl.operating_profit,
        pl.opm_percentage,
        pl.other_income,
        pl.interest,
        pl.depreciation,
        pl.net_profit,
        pl.eps,
        pl.dividend_payout,
        bs.equity_capital,
        bs.reserves,
        bs.borrowings,
        bs.investments,
        bs.other_liabilities,
        bs.total_assets,
        bs.fixed_assets,
        bs.other_asset,
        cf.operating_activity,
        cf.investing_activity,
        cf.financing_activity,
        cf.net_cash_flow
    FROM all_pairs ap
    LEFT JOIN profitandloss pl
        ON ap.company_id = pl.company_id AND ap.year = pl.year
    LEFT JOIN balancesheet bs
        ON ap.company_id = bs.company_id AND ap.year = bs.year
    LEFT JOIN cashflow cf
        ON ap.company_id = cf.company_id AND ap.year = cf.year
    ORDER BY ap.company_id, ap.year
    """
    cur = conn.execute(sql)
    result: dict[str, list] = {}
    for row in cur.fetchall():
        cid = row["company_id"]
        result.setdefault(cid, []).append(row)
    return result


# ---------------------------------------------------------------------------
# Per-row ratio computation
# ---------------------------------------------------------------------------


def _compute_row_ratios(
    row: sqlite3.Row,
    is_financial: bool,
    face_value: float | None,
) -> dict:
    """Compute all KPIs for a single (company_id, year) merged row."""
    npm = net_profit_margin(row["net_profit"], row["sales"])
    opm = operating_profit_margin(
        row["operating_profit"],
        row["sales"],
        is_financial,
        opm_percentage=row["opm_percentage"],
        company_id=row["company_id"],
        year=row["year"],
    )
    roe = return_on_equity(row["net_profit"], row["equity_capital"], row["reserves"])
    roce = return_on_capital_employed(
        operating_profit=row["operating_profit"],
        other_income=row["other_income"],
        equity_capital=row["equity_capital"],
        reserves=row["reserves"],
        borrowings=row["borrowings"],
        total_assets=row["total_assets"],
        other_liabilities=row["other_liabilities"],
        is_financial=is_financial,
    )
    roa = return_on_assets(row["net_profit"], row["total_assets"])
    de = debt_to_equity(
        row["borrowings"], row["equity_capital"], row["reserves"], is_financial
    )
    ic = interest_coverage(
        row["operating_profit"],
        row["other_income"],
        row["interest"],
        row["borrowings"],
    )
    ic_label = get_icr_label(ic, row["borrowings"])
    high_lev = high_leverage_flag(de, is_financial)
    ic_warn = icr_warning_flag(ic, is_financial)
    nd = net_debt(row["borrowings"], row["investments"])
    at = asset_turnover(row["sales"], row["total_assets"])
    wc = working_capital(row["other_asset"], row["other_liabilities"])
    fcf = free_cash_flow(row["operating_activity"], row["investing_activity"])
    capex_val = capex(row["investing_activity"])
    cfo_q = cfo_quality_score(row["operating_activity"], row["net_profit"])
    capex_int = capex_intensity(row["investing_activity"], row["sales"])
    capex_int_label = capex_intensity_label(capex_int)
    fcf_conv = fcf_conversion_rate(fcf, row["operating_profit"])
    bvps = book_value_per_share(row["equity_capital"], row["reserves"], face_value)

    return {
        "company_id": row["company_id"],
        "year": row["year"],
        # Profitability
        "net_profit_margin_pct": _round(npm),
        "operating_profit_margin_pct": _round(opm),
        "return_on_equity_pct": _round(roe),
        "return_on_capital_employed_pct": _round(roce),
        "return_on_assets_pct": _round(roa),
        # Leverage & Coverage
        "debt_to_equity": _round(de),
        "interest_coverage": _round(ic),
        "icr_label": ic_label,
        "high_leverage_flag": 1 if high_lev else 0,
        "icr_warning_flag": 1 if ic_warn else 0,
        "net_debt_cr": _round(nd),
        # Efficiency
        "asset_turnover": _round(at),
        "working_capital_cr": _round(wc),
        # Cash-flow (Day 11 additions)
        "free_cash_flow_cr": _round(fcf),
        "capex_cr": _round(capex_val),
        "cfo_quality_score": _round(cfo_q),
        "capex_intensity_pct": _round(capex_int),
        "capex_intensity_label": capex_int_label,
        "fcf_conversion_rate_pct": _round(fcf_conv),
        # Per-share
        "earnings_per_share": _round(row["eps"]),
        "book_value_per_share": _round(bvps),
        "dividend_payout_ratio_pct": _round(row["dividend_payout"]),
        # Balance-sheet helper columns (for downstream use)
        "total_debt_cr": _round(row["borrowings"]),
        "cash_from_operations_cr": _round(row["operating_activity"]),
    }


def _round(val: float | None, ndigits: int = 4) -> float | None:
    if val is None:
        return None
    return round(val, ndigits)


# ---------------------------------------------------------------------------
# CAGR attachment
# ---------------------------------------------------------------------------


def _attach_cagr(
    ratios_by_company: dict[str, list[dict]],
    merged: dict[str, list],
    metric: str,
    prefix: str,
    exclude_set: set[str],
) -> None:
    """Inject CAGR columns into the most-recent row of each company's ratio list.

    metric: column name from merged rows (e.g. 'sales', 'net_profit', 'eps')
    prefix: output key prefix (e.g. 'revenue', 'pat', 'eps')
    """
    for cid, rows in merged.items():
        # Build (year, value) series, skip None values
        series = [(r["year"], r[metric]) for r in rows if r[metric] is not None]
        if not series:
            continue
        cagr_dict = _cagr_series(series, [1, 3, 5, 10], cid, include_flags=True)
        # Attach to every ratio row that matches the latest year
        last_year = series[-1][0]
        for ratio_row in ratios_by_company.get(cid, []):
            if ratio_row["year"] == last_year:
                for k, v in cagr_dict.items():
                    if k.endswith("_flag"):
                        ratio_row[f"{prefix}_{k}"] = v
                    else:
                        ratio_row[f"{prefix}_{k}"] = _round(v)


# ---------------------------------------------------------------------------
# Schema migration (adds new columns if they don't exist)
# ---------------------------------------------------------------------------

_EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("return_on_capital_employed_pct", "NUMERIC"),
    ("return_on_assets_pct", "NUMERIC"),
    ("working_capital_cr", "NUMERIC"),
    ("cfo_quality_score", "NUMERIC"),
    ("capex_intensity_pct", "NUMERIC"),
    ("book_value_per_share", "NUMERIC"),
    # Day 09 columns
    ("net_debt_cr", "NUMERIC"),
    ("high_leverage_flag", "BOOLEAN"),
    ("icr_warning_flag", "BOOLEAN"),
    ("icr_label", "VARCHAR(20)"),
    # Day 11 columns — Cash-Flow KPIs
    ("fcf_conversion_rate_pct", "NUMERIC"),
    ("cfo_quality_score_5yr", "NUMERIC"),
    ("cfo_quality_label", "VARCHAR(20)"),
    ("capex_intensity_label", "VARCHAR(20)"),
    # Day 12 columns — Composite Score
    ("composite_quality_score", "NUMERIC"),
    # CAGR columns — revenue
    ("revenue_cagr_1y", "NUMERIC"),
    ("revenue_cagr_1yr", "NUMERIC"),
    ("revenue_cagr_1y_flag", "VARCHAR(20)"),
    ("revenue_cagr_1yr_flag", "VARCHAR(20)"),
    ("revenue_cagr_3y", "NUMERIC"),
    ("revenue_cagr_3yr", "NUMERIC"),
    ("revenue_cagr_3y_flag", "VARCHAR(20)"),
    ("revenue_cagr_3yr_flag", "VARCHAR(20)"),
    ("revenue_cagr_5y", "NUMERIC"),
    ("revenue_cagr_5yr", "NUMERIC"),
    ("revenue_cagr_5y_flag", "VARCHAR(20)"),
    ("revenue_cagr_5yr_flag", "VARCHAR(20)"),
    ("revenue_cagr_10y", "NUMERIC"),
    ("revenue_cagr_10yr", "NUMERIC"),
    ("revenue_cagr_10y_flag", "VARCHAR(20)"),
    ("revenue_cagr_10yr_flag", "VARCHAR(20)"),
    # CAGR columns — PAT
    ("pat_cagr_1y", "NUMERIC"),
    ("pat_cagr_1yr", "NUMERIC"),
    ("pat_cagr_1y_flag", "VARCHAR(20)"),
    ("pat_cagr_1yr_flag", "VARCHAR(20)"),
    ("pat_cagr_3y", "NUMERIC"),
    ("pat_cagr_3yr", "NUMERIC"),
    ("pat_cagr_3y_flag", "VARCHAR(20)"),
    ("pat_cagr_3yr_flag", "VARCHAR(20)"),
    ("pat_cagr_5y", "NUMERIC"),
    ("pat_cagr_5yr", "NUMERIC"),
    ("pat_cagr_5y_flag", "VARCHAR(20)"),
    ("pat_cagr_5yr_flag", "VARCHAR(20)"),
    ("pat_cagr_10y", "NUMERIC"),
    ("pat_cagr_10yr", "NUMERIC"),
    ("pat_cagr_10y_flag", "VARCHAR(20)"),
    ("pat_cagr_10yr_flag", "VARCHAR(20)"),
    # CAGR columns — EPS
    ("eps_cagr_1y", "NUMERIC"),
    ("eps_cagr_1yr", "NUMERIC"),
    ("eps_cagr_1y_flag", "VARCHAR(20)"),
    ("eps_cagr_1yr_flag", "VARCHAR(20)"),
    ("eps_cagr_3y", "NUMERIC"),
    ("eps_cagr_3yr", "NUMERIC"),
    ("eps_cagr_3y_flag", "VARCHAR(20)"),
    ("eps_cagr_3yr_flag", "VARCHAR(20)"),
    ("eps_cagr_5y", "NUMERIC"),
    ("eps_cagr_5yr", "NUMERIC"),
    ("eps_cagr_5y_flag", "VARCHAR(20)"),
    ("eps_cagr_5yr_flag", "VARCHAR(20)"),
    ("eps_cagr_10y", "NUMERIC"),
    ("eps_cagr_10yr", "NUMERIC"),
    ("eps_cagr_10y_flag", "VARCHAR(20)"),
    ("eps_cagr_10yr_flag", "VARCHAR(20)"),
]


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add new KPI columns to financial_ratios if they don't exist yet."""
    cur = conn.execute("PRAGMA table_info(financial_ratios)")
    existing = {r["name"] for r in cur.fetchall()}
    for col_name, col_type in _EXTRA_COLUMNS:
        if col_name not in existing:
            conn.execute(
                f"ALTER TABLE financial_ratios ADD COLUMN {col_name} {col_type}"
            )
            log.info("  Schema migration: added column %s", col_name)
    conn.commit()


# ---------------------------------------------------------------------------
# Upsert computed ratios into DB
# ---------------------------------------------------------------------------

_UPSERT_COLS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",
    "debt_to_equity",
    "interest_coverage",
    "icr_label",
    "high_leverage_flag",
    "icr_warning_flag",
    "net_debt_cr",
    "asset_turnover",
    "working_capital_cr",
    "free_cash_flow_cr",
    "capex_cr",
    "cfo_quality_score",
    "capex_intensity_pct",
    "capex_intensity_label",
    "fcf_conversion_rate_pct",
    "cfo_quality_score_5yr",
    "cfo_quality_label",
    "composite_quality_score",
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
    "total_debt_cr",
    "cash_from_operations_cr",
    # CAGR columns (may be absent → default None)
    "revenue_cagr_1y",
    "revenue_cagr_1yr",
    "revenue_cagr_1y_flag",
    "revenue_cagr_1yr_flag",
    "revenue_cagr_3y",
    "revenue_cagr_3yr",
    "revenue_cagr_3y_flag",
    "revenue_cagr_3yr_flag",
    "revenue_cagr_5y",
    "revenue_cagr_5yr",
    "revenue_cagr_5y_flag",
    "revenue_cagr_5yr_flag",
    "revenue_cagr_10y",
    "revenue_cagr_10yr",
    "revenue_cagr_10y_flag",
    "revenue_cagr_10yr_flag",
    "pat_cagr_1y",
    "pat_cagr_1yr",
    "pat_cagr_1y_flag",
    "pat_cagr_1yr_flag",
    "pat_cagr_3y",
    "pat_cagr_3yr",
    "pat_cagr_3y_flag",
    "pat_cagr_3yr_flag",
    "pat_cagr_5y",
    "pat_cagr_5yr",
    "pat_cagr_5y_flag",
    "pat_cagr_5yr_flag",
    "pat_cagr_10y",
    "pat_cagr_10yr",
    "pat_cagr_10y_flag",
    "pat_cagr_10yr_flag",
    "eps_cagr_1y",
    "eps_cagr_1yr",
    "eps_cagr_1y_flag",
    "eps_cagr_1yr_flag",
    "eps_cagr_3y",
    "eps_cagr_3yr",
    "eps_cagr_3y_flag",
    "eps_cagr_3yr_flag",
    "eps_cagr_5y",
    "eps_cagr_5yr",
    "eps_cagr_5y_flag",
    "eps_cagr_5yr_flag",
    "eps_cagr_10y",
    "eps_cagr_10yr",
    "eps_cagr_10y_flag",
    "eps_cagr_10yr_flag",
]


def _upsert_rows(conn: sqlite3.Connection, ratio_rows: list[dict]) -> int:
    """INSERT OR REPLACE ratio rows into financial_ratios.  Returns # of rows written."""
    if not ratio_rows:
        return 0

    # Build dynamic column list (all keys present in first row)
    all_keys = ["company_id", "year"] + _UPSERT_COLS
    placeholders = ", ".join("?" for _ in all_keys)
    cols_sql = ", ".join(all_keys)

    sql = f"""
    INSERT OR REPLACE INTO financial_ratios ({cols_sql})
    VALUES ({placeholders})
    """

    rows_written = 0
    for row in ratio_rows:
        values = [row.get(k) for k in all_keys]
        conn.execute(sql, values)
        rows_written += 1

    conn.commit()
    return rows_written


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def compute_all_ratios() -> dict[str, int]:
    """Compute all financial KPIs for 92 companies and persist to DB.

    Returns summary dict: {company_id: rows_written}.
    """
    log.info("=" * 60)
    log.info("Day 08 — Ratio Engine START")
    log.info("DB: %s", DB_PATH)

    conn = _get_connection()

    # 1. Migrate schema (safe if already run)
    log.info("Step 1/5 — Schema migration …")
    _migrate_schema(conn)

    # 2. Load sector flags and face values
    log.info("Step 2/5 — Loading sector & company metadata …")
    financials_ids = _load_financial_sector_ids(conn)
    face_values = _load_face_values(conn)
    log.info("  Financials sector: %d companies", len(financials_ids))

    # 3. Load merged source data
    log.info("Step 3/5 — Loading merged P&L + BS + CF data …")
    merged = _load_merged_data(conn)
    log.info("  Companies with P&L data: %d", len(merged))

    # 4. Compute per-row ratios
    log.info("Step 4/5 — Computing KPIs …")
    ratios_by_company: dict[str, list[dict]] = {}
    for cid, rows in merged.items():
        is_fin = cid in financials_ids
        fv = face_values.get(cid)
        company_ratios = []
        for row in rows:
            computed = _compute_row_ratios(row, is_fin, fv)
            company_ratios.append(computed)
        ratios_by_company[cid] = company_ratios

    # 5. Attach CAGR metrics (only on the final/latest year row)
    log.info("Step 5/5 — Computing CAGR metrics …")
    _attach_cagr(ratios_by_company, merged, "sales", "revenue", CAGR_EXCLUDE)
    _attach_cagr(ratios_by_company, merged, "net_profit", "pat", CAGR_EXCLUDE)
    _attach_cagr(ratios_by_company, merged, "eps", "eps", CAGR_EXCLUDE)

    # 6. Attach 5-yr CFO Quality Score to every row (uses rolling window per row)
    log.info("Step 6/7 — Attaching 5-yr CFO Quality Score …")
    for cid, rows in merged.items():
        ratio_rows = ratios_by_company.get(cid, [])
        for idx, row in enumerate(rows):
            # Gather up to 5 years ending at current row (inclusive)
            window = rows[max(0, idx - 4) : idx + 1]
            cfo_series = [r["operating_activity"] for r in window]
            pat_series = [r["net_profit"] for r in window]
            score_5yr = cfo_quality_score_5yr(cfo_series, pat_series)
            label_5yr = cfo_quality_label(score_5yr)
            ratio_rows[idx]["cfo_quality_score_5yr"] = _round(score_5yr)
            ratio_rows[idx]["cfo_quality_label"] = label_5yr

    # 7. Attach Composite Financial Health Score
    log.info("Step 7/7 — Computing Composite Financial Health Score …")
    for cid, rows in merged.items():
        ratio_rows = ratios_by_company.get(cid, [])
        is_fin = cid in financials_ids
        for r_row in ratio_rows:
            comp_score = calculate_composite_quality_score(
                roe=r_row.get("return_on_equity_pct"),
                roce=r_row.get("return_on_capital_employed_pct"),
                npm=r_row.get("net_profit_margin_pct"),
                fcf=r_row.get("free_cash_flow_cr"),
                cfo_pat_ratio=r_row.get("cfo_quality_score_5yr")
                or r_row.get("cfo_quality_score"),
                revenue_cagr_5yr=r_row.get("revenue_cagr_5yr")
                or r_row.get("revenue_cagr_5y"),
                pat_cagr_5yr=r_row.get("pat_cagr_5yr") or r_row.get("pat_cagr_5y"),
                debt_to_equity=r_row.get("debt_to_equity"),
                interest_coverage=r_row.get("interest_coverage"),
                is_financial=is_fin,
                icr_label=r_row.get("icr_label"),
                roa=r_row.get("return_on_assets_pct"),
            )
            r_row["composite_quality_score"] = comp_score

    # 8. Persist to DB
    log.info("Persisting to DB …")
    summary: dict[str, int] = {}
    total = 0
    for cid, ratio_rows in ratios_by_company.items():
        written = _upsert_rows(conn, ratio_rows)
        summary[cid] = written
        total += written

    conn.close()

    log.info("=" * 60)
    log.info("Day 08 DONE — %d rows written across %d companies", total, len(summary))
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    summary = compute_all_ratios()
    print(
        f"\nRatio Engine complete -- {sum(summary.values())} rows written across {len(summary)} companies."
    )
