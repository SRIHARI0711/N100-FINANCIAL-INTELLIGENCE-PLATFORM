"""Excel data loaders and normalisers for core and supplementary datasets."""

import logging
import sys
from pathlib import Path

# Base project paths & sys.path setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd

from src.etl.normaliser import clean_string, normalize_ticker, normalize_year

logger = logging.getLogger(__name__)

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw"
DEFAULT_SUPPORTING_DIR = BASE_DIR / "data" / "supporting"


def _to_numeric(series: pd.Series) -> pd.Series:
    """Coerce a series to numeric, stripping commas and formatting artifacts."""
    if series.dtype == "object":
        cleaned = series.astype(str).str.replace(",", "").str.strip()
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def load_companies(path: str | Path | None = None) -> pd.DataFrame:
    """Load companies Excel dataset with header=1 and normalised fields."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "companies.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["id"] = df["id"].apply(normalize_ticker)
        df["company_name"] = df["company_name"].apply(clean_string)
        if "about_company" in df.columns:
            df["about_company"] = df["about_company"].apply(clean_string)

        numeric_cols = ["face_value", "book_value", "roce_percentage", "roe_percentage"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        # Drop rows where primary key is invalid
        df = df.dropna(subset=["id"]).reset_index(drop=True)
        logger.info(f"Loaded {len(df)} companies from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading companies from {file_path}: {e}")
        raise


def load_profit_and_loss(path: str | Path | None = None) -> pd.DataFrame:
    """Load profit and loss Excel dataset with header=1 and normalised year."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "profitandloss.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        df["year"] = df["year"].apply(normalize_year)

        numeric_cols = [
            "sales",
            "expenses",
            "operating_profit",
            "opm_percentage",
            "other_income",
            "interest",
            "depreciation",
            "profit_before_tax",
            "tax_percentage",
            "net_profit",
            "eps",
            "dividend_payout",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} P&L records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading profit and loss from {file_path}: {e}")
        raise


def load_balance_sheet(path: str | Path | None = None) -> pd.DataFrame:
    """Load balance sheet Excel dataset with header=1 and normalised year."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "balancesheet.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        df["year"] = df["year"].apply(normalize_year)

        numeric_cols = [
            "equity_capital",
            "reserves",
            "borrowings",
            "other_liabilities",
            "total_liabilities",
            "fixed_assets",
            "cwip",
            "investments",
            "other_asset",
            "total_assets",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} balance sheet records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading balance sheet from {file_path}: {e}")
        raise


def load_cash_flow(path: str | Path | None = None) -> pd.DataFrame:
    """Load cash flow Excel dataset with header=1 and normalised year."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "cashflow.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        df["year"] = df["year"].apply(normalize_year)

        numeric_cols = [
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} cash flow records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading cash flow from {file_path}: {e}")
        raise


def load_analysis(path: str | Path | None = None) -> pd.DataFrame:
    """Load qualitative analysis Excel dataset with header=1."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "analysis.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        for col in [
            "compounded_sales_growth",
            "compounded_profit_growth",
            "stock_price_cagr",
            "roe",
        ]:
            if col in df.columns:
                df[col] = df[col].apply(clean_string)

        logger.info(f"Loaded {len(df)} analysis records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading analysis from {file_path}: {e}")
        raise


def load_documents(path: str | Path | None = None) -> pd.DataFrame:
    """Load annual report documents Excel dataset with header=1."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "documents.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "Year" in df.columns:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
        if "Annual_Report" in df.columns:
            df["Annual_Report"] = df["Annual_Report"].astype(str).str.strip()

        logger.info(f"Loaded {len(df)} document records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading documents from {file_path}: {e}")
        raise


def load_pros_and_cons(path: str | Path | None = None) -> pd.DataFrame:
    """Load qualitative pros and cons Excel dataset with header=1."""
    file_path = Path(path) if path else DEFAULT_RAW_DIR / "prosandcons.xlsx"
    try:
        df = pd.read_excel(file_path, header=1)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "pros" in df.columns:
            df["pros"] = df["pros"].apply(clean_string)
        if "cons" in df.columns:
            df["cons"] = df["cons"].apply(clean_string)

        logger.info(f"Loaded {len(df)} pros and cons records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading pros and cons from {file_path}: {e}")
        raise


def load_sectors(path: str | Path | None = None) -> pd.DataFrame:
    """Load sectors supplementary dataset with header=0."""
    file_path = Path(path) if path else DEFAULT_SUPPORTING_DIR / "sectors.xlsx"
    if not file_path.exists():
        file_path = DEFAULT_SUPPORTING_DIR / "e-sectors.xlsx"

    try:
        df = pd.read_excel(file_path, header=0)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "broad_sector" in df.columns:
            df["broad_sector"] = df["broad_sector"].apply(clean_string)
        if "sub_sector" in df.columns:
            df["sub_sector"] = df["sub_sector"].apply(clean_string)
        if "index_weight_pct" in df.columns:
            df["index_weight_pct"] = _to_numeric(df["index_weight_pct"])

        logger.info(f"Loaded {len(df)} sector records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading sectors from {file_path}: {e}")
        raise


def load_stock_prices(path: str | Path | None = None) -> pd.DataFrame:
    """Load monthly stock prices supplementary dataset with header=0."""
    file_path = Path(path) if path else DEFAULT_SUPPORTING_DIR / "stock_prices.xlsx"
    try:
        df = pd.read_excel(file_path, header=0)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        for col in ["open_price", "high_price", "low_price", "close_price", "volume"]:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} stock price records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading stock prices from {file_path}: {e}")
        raise


def load_market_cap(path: str | Path | None = None) -> pd.DataFrame:
    """Load valuation multiples and market cap supplementary dataset with header=0."""
    file_path = Path(path) if path else DEFAULT_SUPPORTING_DIR / "market_cap.xlsx"
    try:
        df = pd.read_excel(file_path, header=0)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

        for col in [
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
        ]:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} market cap records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading market cap from {file_path}: {e}")
        raise


def load_financial_ratios(path: str | Path | None = None) -> pd.DataFrame:
    """Load pre-computed financial ratios supplementary dataset with header=0."""
    file_path = Path(path) if path else DEFAULT_SUPPORTING_DIR / "financial_ratios.xlsx"
    try:
        df = pd.read_excel(file_path, header=0)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "year" in df.columns:
            df["year"] = df["year"].apply(normalize_year)

        numeric_cols = [
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
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = _to_numeric(df[col])

        logger.info(f"Loaded {len(df)} financial ratio records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading financial ratios from {file_path}: {e}")
        raise


def load_peer_groups(path: str | Path | None = None) -> pd.DataFrame:
    """Load peer comparison groups supplementary dataset with header=0."""
    file_path = Path(path) if path else DEFAULT_SUPPORTING_DIR / "peer_groups.xlsx"
    try:
        df = pd.read_excel(file_path, header=0)
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        if "peer_group_name" in df.columns:
            df["peer_group_name"] = df["peer_group_name"].apply(clean_string)
        if "is_benchmark" in df.columns:
            df["is_benchmark"] = df["is_benchmark"].astype(bool)

        logger.info(f"Loaded {len(df)} peer group records from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading peer groups from {file_path}: {e}")
        raise


def load_all_core(raw_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Load and normalise all 7 core financial datasets."""
    r_dir = Path(raw_dir) if raw_dir else DEFAULT_RAW_DIR
    return {
        "companies": load_companies(r_dir / "companies.xlsx"),
        "profitandloss": load_profit_and_loss(r_dir / "profitandloss.xlsx"),
        "balancesheet": load_balance_sheet(r_dir / "balancesheet.xlsx"),
        "cashflow": load_cash_flow(r_dir / "cashflow.xlsx"),
        "analysis": load_analysis(r_dir / "analysis.xlsx"),
        "documents": load_documents(r_dir / "documents.xlsx"),
        "prosandcons": load_pros_and_cons(r_dir / "prosandcons.xlsx"),
    }


def load_all_datasets(data_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Load and normalise all 12 datasets (7 core + 5 supplementary)."""
    base = Path(data_dir) if data_dir else DEFAULT_RAW_DIR.parent
    r_dir = base / "raw"
    s_dir = base / "supporting"

    data = load_all_core(r_dir)
    data["sectors"] = load_sectors(s_dir / "sectors.xlsx")
    data["stock_prices"] = load_stock_prices(s_dir / "stock_prices.xlsx")
    data["market_cap"] = load_market_cap(s_dir / "market_cap.xlsx")
    data["financial_ratios"] = load_financial_ratios(s_dir / "financial_ratios.xlsx")
    data["peer_groups"] = load_peer_groups(s_dir / "peer_groups.xlsx")

    return data


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    from db.loader import load_database

    print("Running Full Data Ingestion & SQLite Load for N100...")
    audit_df = load_database(reset=True)
    print("\n" + "=" * 70)
    print("N100 PLATFORM — LOAD AUDIT SUMMARY")
    print("=" * 70)
    print(audit_df.to_string(index=False))
    print("=" * 70)
