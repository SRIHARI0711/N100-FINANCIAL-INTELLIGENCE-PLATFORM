"""Schema and Data Quality (DQ) Validator implementing rules DQ-01 to DQ-16."""

import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Base project paths & sys.path setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import requests

from src.etl.normaliser import normalize_ticker

logger = logging.getLogger(__name__)


@dataclass
class ValidationFailure:
    """Represents a single data quality rule failure or warning."""

    rule_id: str
    table: str
    company_id: str
    year: str | None
    field: str
    issue: str
    severity: str  # CRITICAL, WARNING, INFO


class DataQualityValidator:
    """Validates datasets against 16 core Data Quality (DQ) rules."""

    def __init__(self, output_dir: Path | str | None = None) -> None:
        """Initialize the validator with output directory."""
        self.output_dir = Path(output_dir) if output_dir else BASE_DIR / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.failures: list[ValidationFailure] = []

    def validate_dq01_company_pk(
        self, companies: pd.DataFrame
    ) -> list[ValidationFailure]:
        """DQ-01: Company PK Uniqueness. Halt load if duplicate ticker found."""
        failures: list[ValidationFailure] = []
        if "id" not in companies.columns:
            return failures

        dups = companies[companies.duplicated(subset=["id"], keep=False)]
        for _, row in dups.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-01",
                    table="companies",
                    company_id=str(row["id"]),
                    year=None,
                    field="id",
                    issue=f"Duplicate company primary key: {row['id']}",
                    severity="CRITICAL",
                )
            )
        return failures

    def validate_dq02_annual_pk(
        self, table_name: str, df: pd.DataFrame
    ) -> tuple[list[ValidationFailure], pd.DataFrame]:
        """DQ-02: Annual PK Uniqueness. Deduplicate (company_id, year) keeping last occurrence."""
        failures: list[ValidationFailure] = []
        if "company_id" not in df.columns or "year" not in df.columns:
            return failures, df

        # Filter out PARSE_ERROR or invalid rows before checking duplicates
        valid_mask = df["year"].notna() & (df["year"] != "PARSE_ERROR")
        df_valid = df[valid_mask]

        dup_mask = df_valid.duplicated(subset=["company_id", "year"], keep="last")
        duplicates = df_valid[
            df_valid.duplicated(subset=["company_id", "year"], keep=False)
        ]

        for _, row in duplicates.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-02",
                    table=table_name,
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="(company_id, year)",
                    issue=f"Duplicate annual PK in {table_name}: ({row['company_id']}, {row['year']})",
                    severity="CRITICAL",
                )
            )

        # Keep last occurrence
        deduped_df = df[~((df.index.isin(df_valid.index)) & dup_mask)].copy()
        return failures, deduped_df

    def validate_dq03_fk_integrity(
        self, table_name: str, df: pd.DataFrame, valid_companies: set[str]
    ) -> tuple[list[ValidationFailure], pd.DataFrame]:
        """DQ-03: FK Integrity. Reject orphan rows not present in companies."""
        failures: list[ValidationFailure] = []
        if "company_id" not in df.columns:
            return failures, df

        orphan_mask = ~df["company_id"].isin(valid_companies)
        orphans = df[orphan_mask]

        for _, row in orphans.iterrows():
            yr = (
                str(row["year"])
                if "year" in row
                else (str(row["Year"]) if "Year" in row else None)
            )
            failures.append(
                ValidationFailure(
                    rule_id="DQ-03",
                    table=table_name,
                    company_id=str(row["company_id"]),
                    year=yr,
                    field="company_id",
                    issue=f"Foreign key violation: company '{row['company_id']}' not in companies table",
                    severity="CRITICAL",
                )
            )

        clean_df = df[~orphan_mask].copy()
        return failures, clean_df

    def validate_dq04_bs_balance(self, bs: pd.DataFrame) -> list[ValidationFailure]:
        """DQ-04: Balance Sheet Balance. Flag rows where assets != liabilities by >= 1%."""
        failures: list[ValidationFailure] = []
        required_cols = {"company_id", "year", "total_assets", "total_liabilities"}
        if not required_cols.issubset(bs.columns):
            return failures

        assets = pd.to_numeric(bs["total_assets"], errors="coerce")
        liab = pd.to_numeric(bs["total_liabilities"], errors="coerce")
        denom = assets.replace(0, np.nan)
        diff_pct = (assets - liab).abs() / denom

        imbalanced = bs[diff_pct >= 0.01]
        for _, row in imbalanced.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-04",
                    table="balancesheet",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="total_assets / total_liabilities",
                    issue=(
                        f"BS imbalance >= 1%: Assets={row['total_assets']}, "
                        f"Liabilities={row['total_liabilities']}"
                    ),
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq05_opm_cross_check(
        self, pl: pd.DataFrame
    ) -> list[ValidationFailure]:
        """DQ-05: OPM Cross-Check. Flag rows where source OPM differs from calculated by >= 1.0%."""
        failures: list[ValidationFailure] = []
        required_cols = {
            "company_id",
            "year",
            "operating_profit",
            "sales",
            "opm_percentage",
        }
        if not required_cols.issubset(pl.columns):
            return failures

        sales = pd.to_numeric(pl["sales"], errors="coerce")
        op = pd.to_numeric(pl["operating_profit"], errors="coerce")
        source_opm = pd.to_numeric(pl["opm_percentage"], errors="coerce")

        calc_opm = (op / sales.replace(0, np.nan)) * 100.0
        diff = (source_opm - calc_opm).abs()

        mismatches = pl[diff >= 1.0]
        for _, row in mismatches.iterrows():
            calc_val = (
                (row["operating_profit"] / row["sales"] * 100.0)
                if row["sales"]
                else 0.0
            )
            failures.append(
                ValidationFailure(
                    rule_id="DQ-05",
                    table="profitandloss",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="opm_percentage",
                    issue=(
                        f"OPM mismatch >= 1%: Source OPM={row['opm_percentage']}%, "
                        f"Computed={calc_val:.2f}%"
                    ),
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq06_positive_sales(
        self, pl: pd.DataFrame, bank_companies: set[str] | None = None
    ) -> list[ValidationFailure]:
        """DQ-06: Positive Sales. Flag non-bank companies with sales <= 0."""
        failures: list[ValidationFailure] = []
        if "sales" not in pl.columns or "company_id" not in pl.columns:
            return failures

        banks = bank_companies or set()
        sales = pd.to_numeric(pl["sales"], errors="coerce")
        non_positive = pl[(sales <= 0) & (~pl["company_id"].isin(banks))]

        for _, row in non_positive.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-06",
                    table="profitandloss",
                    company_id=str(row["company_id"]),
                    year=str(row.get("year", "N/A")),
                    field="sales",
                    issue=f"Non-positive sales in non-bank company: {row['sales']}",
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq07_year_format(
        self, table_name: str, df: pd.DataFrame
    ) -> tuple[list[ValidationFailure], pd.DataFrame]:
        """DQ-07: Year Format. Reject rows where normalised year does not match 'YYYY-MM'."""
        failures: list[ValidationFailure] = []
        if "year" not in df.columns:
            return failures, df

        invalid_mask = ~df["year"].astype(str).str.match(r"^\d{4}-\d{2}$")
        invalids = df[invalid_mask]

        for _, row in invalids.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-07",
                    table=table_name,
                    company_id=str(row.get("company_id", "UNKNOWN")),
                    year=str(row["year"]),
                    field="year",
                    issue=f"Invalid financial year format: '{row['year']}' (expected YYYY-MM)",
                    severity="CRITICAL",
                )
            )

        clean_df = df[~invalid_mask].copy()
        return failures, clean_df

    def validate_dq08_ticker_format(
        self, table_name: str, df: pd.DataFrame
    ) -> tuple[list[ValidationFailure], pd.DataFrame]:
        """DQ-08: Ticker Format. Normalise and reject if length out of range (2-12) or malformed."""
        failures: list[ValidationFailure] = []
        col = (
            "id"
            if "id" in df.columns
            else ("company_id" if "company_id" in df.columns else None)
        )
        if not col:
            return failures, df

        invalid_indices = []
        for idx, val in df[col].items():
            norm = normalize_ticker(val)
            if not norm:
                invalid_indices.append(idx)
                failures.append(
                    ValidationFailure(
                        rule_id="DQ-08",
                        table=table_name,
                        company_id=str(val),
                        year=None,
                        field=col,
                        issue=f"Invalid ticker format: '{val}' (must be 2-12 alphanumeric chars)",
                        severity="CRITICAL",
                    )
                )

        clean_df = df.drop(index=invalid_indices).copy()
        return failures, clean_df

    def validate_dq09_net_cash(self, cf: pd.DataFrame) -> list[ValidationFailure]:
        """DQ-09: Net Cash Check. Flag net cash flow mismatch > 10 Cr from CFO+CFI+CFF."""
        failures: list[ValidationFailure] = []
        required = {
            "company_id",
            "year",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        }
        if not required.issubset(cf.columns):
            return failures

        cfo = pd.to_numeric(cf["operating_activity"], errors="coerce").fillna(0)
        cfi = pd.to_numeric(cf["investing_activity"], errors="coerce").fillna(0)
        cff = pd.to_numeric(cf["financing_activity"], errors="coerce").fillna(0)
        net_cf = pd.to_numeric(cf["net_cash_flow"], errors="coerce").fillna(0)

        diff = (net_cf - (cfo + cfi + cff)).abs()
        mismatches = cf[diff > 10.0]

        for _, row in mismatches.iterrows():
            expected = (
                row["operating_activity"]
                + row["investing_activity"]
                + row["financing_activity"]
            )
            failures.append(
                ValidationFailure(
                    rule_id="DQ-09",
                    table="cashflow",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="net_cash_flow",
                    issue=(
                        f"Net cash flow mismatch > 10 Cr: Reported={row['net_cash_flow']}, "
                        f"Sum(CFO+CFI+CFF)={expected:.2f}"
                    ),
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq10_fixed_assets(
        self, bs: pd.DataFrame
    ) -> tuple[list[ValidationFailure], pd.DataFrame]:
        """DQ-10: Non-Negative Fixed Assets. Coerce negative fixed assets to 0 and log."""
        failures: list[ValidationFailure] = []
        if "fixed_assets" not in bs.columns:
            return failures, bs

        clean_bs = bs.copy()
        neg_mask = pd.to_numeric(clean_bs["fixed_assets"], errors="coerce") < 0
        negatives = clean_bs[neg_mask]

        for _, row in negatives.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-10",
                    table="balancesheet",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="fixed_assets",
                    issue=f"Negative fixed assets: {row['fixed_assets']} (coerced to 0)",
                    severity="WARNING",
                )
            )

        clean_bs.loc[neg_mask, "fixed_assets"] = 0
        return failures, clean_bs

    def validate_dq11_tax_rate(self, pl: pd.DataFrame) -> list[ValidationFailure]:
        """DQ-11: Tax Rate Range. Flag effective tax rate outside [0, 60]%."""
        failures: list[ValidationFailure] = []
        if "tax_percentage" not in pl.columns:
            return failures

        tax = pd.to_numeric(pl["tax_percentage"], errors="coerce")
        out_of_range = pl[tax.notna() & ((tax < 0) | (tax > 60))]

        for _, row in out_of_range.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-11",
                    table="profitandloss",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="tax_percentage",
                    issue=f"Tax rate out of bounds [0, 60]%: {row['tax_percentage']}%",
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq12_dividend_payout(
        self, pl: pd.DataFrame
    ) -> list[ValidationFailure]:
        """DQ-12: Dividend Payout Cap. Flag dividend payout > 200%."""
        failures: list[ValidationFailure] = []
        if "dividend_payout" not in pl.columns:
            return failures

        payout = pd.to_numeric(pl["dividend_payout"], errors="coerce")
        excessive = pl[payout > 200.0]

        for _, row in excessive.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-12",
                    table="profitandloss",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="dividend_payout",
                    issue=f"Excessive dividend payout > 200%: {row['dividend_payout']}%",
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq13_url_validity(
        self, docs: pd.DataFrame, sample_size: int | None = 20, timeout: float = 3.0
    ) -> list[ValidationFailure]:
        """DQ-13: URL Validity. Check document report URLs (head request). Flag 404s without rejecting."""
        failures: list[ValidationFailure] = []
        if "Annual_Report" not in docs.columns:
            return failures

        sample = docs.head(sample_size) if sample_size else docs
        for _, row in sample.iterrows():
            url = str(row["Annual_Report"]).strip()
            if not url or url.lower() in ("nan", "none") or not url.startswith("http"):
                failures.append(
                    ValidationFailure(
                        rule_id="DQ-13",
                        table="documents",
                        company_id=str(row["company_id"]),
                        year=str(row.get("Year", "N/A")),
                        field="Annual_Report",
                        issue=f"Malformed URL: '{url}'",
                        severity="WARNING",
                    )
                )
                continue

            try:
                res = requests.head(url, timeout=timeout, allow_redirects=True)
                if res.status_code >= 400:
                    failures.append(
                        ValidationFailure(
                            rule_id="DQ-13",
                            table="documents",
                            company_id=str(row["company_id"]),
                            year=str(row.get("Year", "N/A")),
                            field="Annual_Report",
                            issue=f"URL unreachable (HTTP {res.status_code}): {url}",
                            severity="WARNING",
                        )
                    )
            except (requests.RequestException, OSError) as e:
                failures.append(
                    ValidationFailure(
                        rule_id="DQ-13",
                        table="documents",
                        company_id=str(row["company_id"]),
                        year=str(row.get("Year", "N/A")),
                        field="Annual_Report",
                        issue=f"URL request failed ({e.__class__.__name__}): {url}",
                        severity="WARNING",
                    )
                )
        return failures

    def validate_dq14_eps_sign(self, pl: pd.DataFrame) -> list[ValidationFailure]:
        """DQ-14: EPS Sign Consistency. Flag rows where net_profit > 0 but eps <= 0."""
        failures: list[ValidationFailure] = []
        if "net_profit" not in pl.columns or "eps" not in pl.columns:
            return failures

        net_profit = pd.to_numeric(pl["net_profit"], errors="coerce")
        eps = pd.to_numeric(pl["eps"], errors="coerce")
        mismatches = pl[(net_profit > 0) & (eps <= 0)]

        for _, row in mismatches.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-14",
                    table="profitandloss",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="eps",
                    issue=f"EPS sign inconsistency: Net Profit={row['net_profit']} Cr but EPS={row['eps']}",
                    severity="WARNING",
                )
            )
        return failures

    def validate_dq15_bse_balance(self, bs: pd.DataFrame) -> list[ValidationFailure]:
        """DQ-15: BSE/ASE Strict Balance. Information check for total_assets == total_liabilities."""
        failures: list[ValidationFailure] = []
        if "total_assets" not in bs.columns or "total_liabilities" not in bs.columns:
            return failures

        assets = pd.to_numeric(bs["total_assets"], errors="coerce")
        liab = pd.to_numeric(bs["total_liabilities"], errors="coerce")
        imbalanced = bs[assets != liab]

        for _, row in imbalanced.iterrows():
            failures.append(
                ValidationFailure(
                    rule_id="DQ-15",
                    table="balancesheet",
                    company_id=str(row["company_id"]),
                    year=str(row["year"]),
                    field="total_assets == total_liabilities",
                    issue=f"Strict balance difference: Assets={row['total_assets']}, Liab={row['total_liabilities']}",
                    severity="INFO",
                )
            )
        return failures

    def validate_dq16_coverage(
        self, pl: pd.DataFrame, bs: pd.DataFrame, cf: pd.DataFrame
    ) -> list[ValidationFailure]:
        """DQ-16: Coverage Check. Flag companies with < 5 years of history in core tables."""
        failures: list[ValidationFailure] = []
        company_years: dict[str, set[str]] = {}

        for df in [pl, bs, cf]:
            if "company_id" in df.columns and "year" in df.columns:
                valid = df[df["year"].astype(str).str.match(r"^\d{4}-\d{2}$")]
                for cid, grp in valid.groupby("company_id"):
                    if cid not in company_years:
                        company_years[cid] = set()
                    company_years[cid].update(grp["year"].dropna().tolist())

        for cid, yrs in company_years.items():
            if len(yrs) < 5:
                failures.append(
                    ValidationFailure(
                        rule_id="DQ-16",
                        table="multi_table",
                        company_id=cid,
                        year=None,
                        field="coverage",
                        issue=f"Company '{cid}' has only {len(yrs)} years of history (< 5 years required)",
                        severity="WARNING",
                    )
                )
        return failures

    def validate_all(
        self, datasets: dict[str, pd.DataFrame], check_urls: bool = False
    ) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
        """Run all 16 DQ rules, apply resolutions, and export validation_failures.csv."""
        self.failures.clear()
        cleaned: dict[str, pd.DataFrame] = {k: v.copy() for k, v in datasets.items()}

        companies = cleaned.get("companies", pd.DataFrame())
        sectors = cleaned.get("sectors", pd.DataFrame())

        # DQ-01: Company PK Uniqueness
        self.failures.extend(self.validate_dq01_company_pk(companies))

        # DQ-08: Ticker format check on companies
        f_dq08, companies = self.validate_dq08_ticker_format("companies", companies)
        self.failures.extend(f_dq08)
        cleaned["companies"] = companies
        valid_companies = set(companies["id"].dropna().unique())

        # Extract bank tickers for DQ-06
        bank_companies = set()
        if (
            not sectors.empty
            and "company_id" in sectors.columns
            and "broad_sector" in sectors.columns
        ):
            bank_mask = sectors["broad_sector"].astype(str).str.contains(
                "Financial", case=False
            ) | (sectors["sub_sector"].astype(str).str.contains("Bank", case=False))
            bank_companies = set(sectors[bank_mask]["company_id"].unique())

        # Process all child tables for FK integrity (DQ-03)
        child_tables = [
            "profitandloss",
            "balancesheet",
            "cashflow",
            "analysis",
            "documents",
            "prosandcons",
            "sectors",
            "stock_prices",
            "market_cap",
            "financial_ratios",
            "peer_groups",
        ]
        for name in child_tables:
            if name in cleaned:
                f_dq03, clean_child = self.validate_dq03_fk_integrity(
                    name, cleaned[name], valid_companies
                )
                self.failures.extend(f_dq03)
                cleaned[name] = clean_child

        # Process core time-series tables for year format (DQ-07) and dedup (DQ-02)
        time_series_tables = [
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
        ]
        for name in time_series_tables:
            if name in cleaned:
                df = cleaned[name]
                # DQ-07: Year format (CRITICAL - reject invalid rows e.g. TTM)
                f_dq07, df = self.validate_dq07_year_format(name, df)
                self.failures.extend(f_dq07)

                # DQ-02: Annual PK Uniqueness (CRITICAL - deduplicate keep last)
                f_dq02, df = self.validate_dq02_annual_pk(name, df)
                self.failures.extend(f_dq02)

                cleaned[name] = df

        # Analytical Warning / Info rules
        if "balancesheet" in cleaned:
            self.failures.extend(self.validate_dq04_bs_balance(cleaned["balancesheet"]))
            f_dq10, bs_clean = self.validate_dq10_fixed_assets(cleaned["balancesheet"])
            self.failures.extend(f_dq10)
            cleaned["balancesheet"] = bs_clean
            self.failures.extend(
                self.validate_dq15_bse_balance(cleaned["balancesheet"])
            )

        if "profitandloss" in cleaned:
            self.failures.extend(
                self.validate_dq05_opm_cross_check(cleaned["profitandloss"])
            )
            self.failures.extend(
                self.validate_dq06_positive_sales(
                    cleaned["profitandloss"], bank_companies
                )
            )
            self.failures.extend(self.validate_dq11_tax_rate(cleaned["profitandloss"]))
            self.failures.extend(
                self.validate_dq12_dividend_payout(cleaned["profitandloss"])
            )
            self.failures.extend(self.validate_dq14_eps_sign(cleaned["profitandloss"]))

        if "cashflow" in cleaned:
            self.failures.extend(self.validate_dq09_net_cash(cleaned["cashflow"]))

        if "documents" in cleaned and check_urls:
            self.failures.extend(self.validate_dq13_url_validity(cleaned["documents"]))

        if (
            "profitandloss" in cleaned
            and "balancesheet" in cleaned
            and "cashflow" in cleaned
        ):
            self.failures.extend(
                self.validate_dq16_coverage(
                    cleaned["profitandloss"],
                    cleaned["balancesheet"],
                    cleaned["cashflow"],
                )
            )

        # Convert failures to DataFrame
        failures_data = [asdict(f) for f in self.failures]
        failures_df = pd.DataFrame(failures_data)
        if failures_df.empty:
            failures_df = pd.DataFrame(
                columns=[
                    "rule_id",
                    "table",
                    "company_id",
                    "year",
                    "field",
                    "issue",
                    "severity",
                ]
            )

        # Write to output/validation_failures.csv
        out_csv = self.output_dir / "validation_failures.csv"
        failures_df.to_csv(out_csv, index=False)
        logger.info(f"Exported {len(failures_df)} validation failures to {out_csv}")

        return failures_df, cleaned


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    from src.etl.loader import load_all_datasets

    print("Running DQ Validation on all datasets...")
    raw_data = load_all_datasets()
    validator = DataQualityValidator()
    failures_df, cleaned_data = validator.validate_all(raw_data)

    print(f"\nTotal Validation Findings: {len(failures_df)}")
    print("Breakdown by Severity:")
    print(failures_df["severity"].value_counts())
    print("\nBreakdown by Rule ID:")
    print(failures_df["rule_id"].value_counts())
