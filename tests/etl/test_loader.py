"""Unit tests for dataset Excel loaders and normalisation pipelines."""

import pandas as pd

from src.etl.loader import (
    load_all_core,
    load_all_datasets,
    load_analysis,
    load_balance_sheet,
    load_cash_flow,
    load_companies,
    load_documents,
    load_financial_ratios,
    load_market_cap,
    load_peer_groups,
    load_profit_and_loss,
    load_pros_and_cons,
    load_sectors,
    load_stock_prices,
)


def test_load_companies():
    """Verify companies dataset loads 92 records with valid tickers and clean names."""
    df = load_companies()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 92
    assert "id" in df.columns
    assert "company_name" in df.columns
    assert df["id"].isna().sum() == 0
    assert df["id"].nunique() == 92
    assert "TCS" in df["id"].values
    assert "RELIANCE" in df["id"].values
    # Check that embedded newlines were stripped from company names
    assert all("\n" not in str(name) for name in df["company_name"])


def test_load_profit_and_loss():
    """Verify profit and loss dataset loads 1276 records with standardised years."""
    df = load_profit_and_loss()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1276
    assert "company_id" in df.columns
    assert "year" in df.columns
    assert "sales" in df.columns
    assert "net_profit" in df.columns
    # Check that financial years match YYYY-MM or PARSE_ERROR (e.g. for TTM)
    sample_years = df[df["year"] != "PARSE_ERROR"]["year"]
    assert sample_years.str.match(r"^\d{4}-\d{2}$").all()


def test_load_balance_sheet():
    """Verify balance sheet dataset loads 1312 records with numeric totals."""
    df = load_balance_sheet()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1312
    assert "company_id" in df.columns
    assert "total_assets" in df.columns
    assert "total_liabilities" in df.columns
    assert pd.api.types.is_numeric_dtype(df["total_assets"])
    assert pd.api.types.is_numeric_dtype(df["total_liabilities"])


def test_load_cash_flow():
    """Verify cash flow dataset loads 1187 records."""
    df = load_cash_flow()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1187
    assert "operating_activity" in df.columns
    assert "investing_activity" in df.columns
    assert "financing_activity" in df.columns
    assert "net_cash_flow" in df.columns


def test_load_analysis():
    """Verify analysis dataset loads 20 records for partial coverage."""
    df = load_analysis()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 20
    assert "company_id" in df.columns
    assert "compounded_sales_growth" in df.columns


def test_load_documents():
    """Verify documents dataset loads 1585 records with integer years."""
    df = load_documents()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1585
    assert "Year" in df.columns
    assert "Annual_Report" in df.columns


def test_load_pros_and_cons():
    """Verify pros and cons dataset loads 16 records."""
    df = load_pros_and_cons()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 16
    assert "pros" in df.columns
    assert "cons" in df.columns


def test_load_supplementary_datasets():
    """Verify supplementary datasets: sectors (92), stock_prices (5520), market_cap (552), ratios (1184), peer_groups (56)."""
    df_sec = load_sectors()
    assert len(df_sec) == 92

    df_prices = load_stock_prices()
    assert len(df_prices) == 5520

    df_mkt = load_market_cap()
    assert len(df_mkt) == 552

    df_ratios = load_financial_ratios()
    assert len(df_ratios) == 1184

    df_peers = load_peer_groups()
    assert len(df_peers) == 56


def test_load_all_core():
    """Verify load_all_core returns all 7 core datasets in a single dictionary."""
    core = load_all_core()
    assert len(core) == 7
    expected_keys = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
    }
    assert set(core.keys()) == expected_keys


def test_load_all_datasets():
    """Verify load_all_datasets returns all 12 datasets."""
    all_data = load_all_datasets()
    assert len(all_data) == 12
