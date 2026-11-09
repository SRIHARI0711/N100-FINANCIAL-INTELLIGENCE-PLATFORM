"""Unit tests for the 16 Data Quality (DQ) validation rules."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.etl.validator import DataQualityValidator


def test_dq01_company_pk_uniqueness():
    """DQ-01: Duplicate company primary key should trigger CRITICAL failure."""
    validator = DataQualityValidator()
    df_companies = pd.DataFrame(
        {
            "id": ["TCS", "INFY", "TCS"],
            "company_name": ["Tata Consultancy Services", "Infosys", "Tata Duplicate"],
        }
    )
    failures = validator.validate_dq01_company_pk(df_companies)
    assert len(failures) == 2
    assert all(f.rule_id == "DQ-01" for f in failures)
    assert all(f.severity == "CRITICAL" for f in failures)
    assert all(f.company_id == "TCS" for f in failures)


def test_dq02_annual_pk_uniqueness():
    """DQ-02: Duplicate (company_id, year) in annual statements triggers CRITICAL and deduplicates."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS", "INFY"],
            "year": ["2023-03", "2023-03", "2023-03"],
            "sales": [100, 110, 200],
        }
    )
    failures, deduped = validator.validate_dq02_annual_pk("profitandloss", df_pl)
    assert len(failures) == 2
    assert failures[0].rule_id == "DQ-02"
    assert failures[0].severity == "CRITICAL"
    # Deduplication keeps last occurrence
    assert len(deduped) == 2
    tcs_row = deduped[deduped["company_id"] == "TCS"].iloc[0]
    assert tcs_row["sales"] == 110


def test_dq03_fk_integrity():
    """DQ-03: Orphan company_id not in companies master table triggers CRITICAL and rejects row."""
    validator = DataQualityValidator()
    valid_companies = {"TCS", "INFY"}
    df_bs = pd.DataFrame(
        {
            "company_id": ["TCS", "UNKNOWN_CO", "INFY"],
            "year": ["2023-03", "2023-03", "2023-03"],
            "total_assets": [1000, 500, 2000],
        }
    )
    failures, clean_df = validator.validate_dq03_fk_integrity(
        "balancesheet", df_bs, valid_companies
    )
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-03"
    assert failures[0].severity == "CRITICAL"
    assert failures[0].company_id == "UNKNOWN_CO"
    assert len(clean_df) == 2
    assert "UNKNOWN_CO" not in clean_df["company_id"].values


def test_dq04_bs_balance():
    """DQ-04: |total_assets - total_liabilities| / total_assets >= 1% triggers WARNING."""
    validator = DataQualityValidator()
    # Case from spec: assets=1000, liab=1020 (diff is 20/1000 = 2% >= 1%)
    df_bs = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "total_assets": [1000, 1000],
            "total_liabilities": [1020, 1005],  # 2% vs 0.5%
        }
    )
    failures = validator.validate_dq04_bs_balance(df_bs)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-04"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "TCS"


def test_dq05_opm_cross_check():
    """DQ-05: Source OPM differs from calculated operating profit margin by >= 1% triggers WARNING."""
    validator = DataQualityValidator()
    # op_profit=20, sales=100 -> calc OPM = 20.0%. Source is 25.0% (diff 5% >= 1%)
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "sales": [100.0, 100.0],
            "operating_profit": [20.0, 20.0],
            "opm_percentage": [25.0, 20.2],
        }
    )
    failures = validator.validate_dq05_opm_cross_check(df_pl)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-05"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "TCS"


def test_dq06_zero_sales():
    """DQ-06: Non-bank company with sales <= 0 triggers WARNING."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "HDFCBANK"],
            "year": ["2023-03", "2023-03"],
            "sales": [0.0, 0.0],
        }
    )
    failures = validator.validate_dq06_positive_sales(
        df_pl, bank_companies={"HDFCBANK"}
    )
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-06"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "TCS"


def test_dq07_year_format():
    """DQ-07: Unparseable year format triggers CRITICAL and rejects row."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "TCS"],
            "year": ["2023-03", "PARSE_ERROR"],
            "sales": [1000, 1050],
        }
    )
    failures, clean_df = validator.validate_dq07_year_format("profitandloss", df_pl)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-07"
    assert failures[0].severity == "CRITICAL"
    assert len(clean_df) == 1
    assert clean_df.iloc[0]["year"] == "2023-03"


def test_dq08_ticker_format():
    """DQ-08: Invalid ticker length or characters triggers CRITICAL and rejects row."""
    validator = DataQualityValidator()
    df_co = pd.DataFrame(
        {
            "id": ["TCS", "A", "VERYLONGSYMBOLNAME", "VALID1"],
            "company_name": ["TCS", "A Corp", "Long Corp", "Valid Corp"],
        }
    )
    failures, clean_df = validator.validate_dq08_ticker_format("companies", df_co)
    assert len(failures) == 2
    assert all(f.rule_id == "DQ-08" for f in failures)
    assert all(f.severity == "CRITICAL" for f in failures)
    assert set(clean_df["id"]) == {"TCS", "VALID1"}


def test_dq09_net_cash():
    """DQ-09: |net_cash_flow - (CFO+CFI+CFF)| > 10 Cr triggers WARNING."""
    validator = DataQualityValidator()
    df_cf = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "operating_activity": [100, 100],
            "investing_activity": [-50, -50],
            "financing_activity": [-30, -30],
            "net_cash_flow": [20, 50],  # expected 20. INFY reports 50 (diff 30 > 10)
        }
    )
    failures = validator.validate_dq09_net_cash(df_cf)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-09"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "INFY"


def test_dq10_fixed_assets():
    """DQ-10: Negative fixed assets triggers WARNING and coerces to 0."""
    validator = DataQualityValidator()
    df_bs = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "fixed_assets": [-150.0, 500.0],
        }
    )
    failures, clean_bs = validator.validate_dq10_fixed_assets(df_bs)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-10"
    assert failures[0].severity == "WARNING"
    assert clean_bs.loc[clean_bs["company_id"] == "TCS", "fixed_assets"].iloc[0] == 0.0


def test_dq11_tax_rate():
    """DQ-11: Effective tax rate outside [0, 60]% triggers WARNING."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY", "WIPRO"],
            "year": ["2023-03", "2023-03", "2023-03"],
            "tax_percentage": [25.0, 75.0, -5.0],
        }
    )
    failures = validator.validate_dq11_tax_rate(df_pl)
    assert len(failures) == 2
    assert all(f.rule_id == "DQ-11" for f in failures)
    assert all(f.severity == "WARNING" for f in failures)


def test_dq12_dividend_payout():
    """DQ-12: Dividend payout > 200% triggers WARNING."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "dividend_payout": [45.0, 240.0],
        }
    )
    failures = validator.validate_dq12_dividend_payout(df_pl)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-12"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "INFY"


def test_dq13_url_validity():
    """DQ-13: URL checking logs 404 or connection failure as WARNING."""
    validator = DataQualityValidator()
    df_docs = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "Year": [2023, 2023],
            "Annual_Report": [
                "https://www.bseindia.com/valid.pdf",
                "https://www.bseindia.com/notfound.pdf",
            ],
        }
    )

    def mock_head(url, **kwargs):
        mock_resp = MagicMock()
        if "notfound" in url:
            mock_resp.status_code = 404
        else:
            mock_resp.status_code = 200
        return mock_resp

    with patch("requests.head", side_effect=mock_head):
        failures = validator.validate_dq13_url_validity(df_docs, sample_size=None)
        assert len(failures) == 1
        assert failures[0].rule_id == "DQ-13"
        assert failures[0].severity == "WARNING"
        assert failures[0].company_id == "INFY"


def test_dq14_eps_sign():
    """DQ-14: Positive net profit with non-positive EPS triggers WARNING."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "net_profit": [100.0, 150.0],
            "eps": [15.0, -2.5],
        }
    )
    failures = validator.validate_dq14_eps_sign(df_pl)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-14"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "INFY"


def test_dq15_bse_balance():
    """DQ-15: Strict balance difference triggers INFO."""
    validator = DataQualityValidator()
    df_bs = pd.DataFrame(
        {
            "company_id": ["TCS", "INFY"],
            "year": ["2023-03", "2023-03"],
            "total_assets": [1000, 1000],
            "total_liabilities": [1000, 1001],
        }
    )
    failures = validator.validate_dq15_bse_balance(df_bs)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-15"
    assert failures[0].severity == "INFO"
    assert failures[0].company_id == "INFY"


def test_dq16_coverage():
    """DQ-16: Companies with < 5 years of financial history trigger WARNING."""
    validator = DataQualityValidator()
    df_pl = pd.DataFrame(
        {
            "company_id": ["TCS"] * 6 + ["NEWCO"] * 3,
            "year": ["2018-03", "2019-03", "2020-03", "2021-03", "2022-03", "2023-03"]
            + ["2021-03", "2022-03", "2023-03"],
        }
    )
    df_bs = df_pl.copy()
    df_cf = df_pl.copy()
    failures = validator.validate_dq16_coverage(df_pl, df_bs, df_cf)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-16"
    assert failures[0].severity == "WARNING"
    assert failures[0].company_id == "NEWCO"


def test_validation_failures_csv_created(tmp_path):
    """Verify validation_failures.csv is created with mandatory columns."""
    validator = DataQualityValidator(output_dir=tmp_path)
    datasets = {
        "companies": pd.DataFrame(
            {"id": ["TCS", "TCS"], "company_name": ["Tata 1", "Tata 2"]}
        ),
    }
    failures_df, _ = validator.validate_all(datasets)
    csv_file = tmp_path / "validation_failures.csv"
    assert csv_file.exists()
    assert {"company_id", "field", "issue", "severity"}.issubset(failures_df.columns)
