"""Database initialisation, loader, and audit engine for N100 platform."""

import logging
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Base project paths & sys.path setup
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd

from src.etl.loader import load_all_datasets
from src.etl.validator import DataQualityValidator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = BASE_DIR / "data" / "nifty100.db"
DEFAULT_SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"

# Table load order: parents must be loaded before child tables
TABLE_LOAD_ORDER = [
    "companies",
    "sectors",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "stock_prices",
    "market_cap",
    "financial_ratios",
    "peer_groups",
]


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with Foreign Keys enabled."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(
    db_path: Path | str | None = None,
    schema_path: Path | str | None = None,
) -> None:
    """Create all 12 tables and indexes defined in schema.sql with foreign keys enabled."""
    db_file = Path(db_path) if db_path else DEFAULT_DB_PATH
    schema_file = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH

    logger.info(f"Initialising database schema at: {db_file}")
    with open(schema_file, encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection(db_file) as conn:
        conn.executescript(schema_sql)
        conn.commit()

    logger.info("Database schema successfully created.")


def insert_dataframe(
    conn: sqlite3.Connection,
    table_name: str,
    df: pd.DataFrame,
) -> int:
    """Insert records from a DataFrame into an existing SQLite table, ignoring id auto-pk collisions."""
    if df.empty:
        return 0

    # Ensure foreign keys are enabled on connection
    conn.execute("PRAGMA foreign_keys = ON;")

    # Drop source 'id' column if table has auto-increment primary key (except for companies where id is ticker)
    df_to_insert = df.copy()
    if table_name != "companies" and "id" in df_to_insert.columns:
        df_to_insert = df_to_insert.drop(columns=["id"])

    # Standardise column names for documents (Year -> year, Annual_Report -> annual_report)
    if table_name == "documents":
        df_to_insert = df_to_insert.rename(
            columns={"Year": "year", "Annual_Report": "annual_report"}
        )

    # Fetch table columns from database to ensure exact column alignment
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    db_cols = [
        row[1]
        for row in cursor.fetchall()
        if row[1] != "id" or table_name == "companies"
    ]

    # Select only columns that exist in the database table
    valid_cols = [c for c in db_cols if c in df_to_insert.columns]
    df_aligned = df_to_insert[valid_cols]

    # Convert DataFrame records to tuples for batch insertion
    placeholders = ", ".join(["?"] * len(valid_cols))
    col_names = ", ".join(valid_cols)
    sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"

    # Coerce NaN to None for SQL NULL compatibility
    records = df_aligned.replace({float("nan"): None}).to_dict(orient="split")["data"]
    cursor.executemany(sql, records)
    conn.commit()

    logger.info(f"Inserted {len(records)} rows into '{table_name}'")
    return len(records)


def check_foreign_keys(conn: sqlite3.Connection) -> list[Any]:
    """Execute PRAGMA foreign_key_check to verify relational integrity."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()
    return violations


def load_database(
    db_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    reset: bool = True,
) -> pd.DataFrame:
    """Orchestrate full load of all 12 validated datasets into SQLite and generate load_audit.csv."""
    db_file = Path(db_path) if db_path else DEFAULT_DB_PATH
    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if reset and db_file.exists():
        db_file.unlink()

    # Initialise schema
    init_db(db_file)

    # Ingest and validate data
    logger.info("Loading and validating datasets for database load...")
    raw_datasets = load_all_datasets()
    validator = DataQualityValidator(output_dir=out_dir)
    _, cleaned_datasets = validator.validate_all(raw_datasets)

    audit_records: list[dict[str, Any]] = []

    with get_connection(db_file) as conn:
        for table_name in TABLE_LOAD_ORDER:
            t0 = time.perf_counter()
            rows_in = len(raw_datasets[table_name]) if table_name in raw_datasets else 0
            df_clean = cleaned_datasets.get(table_name, pd.DataFrame())

            rows_out = insert_dataframe(conn, table_name, df_clean)
            runtime_s = round(time.perf_counter() - t0, 3)
            rejected = max(0, rows_in - rows_out)

            audit_records.append(
                {
                    "table": table_name,
                    "rows_in": rows_in,
                    "rows_out": rows_out,
                    "rejected": rejected,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "runtime_s": runtime_s,
                }
            )

        # Verify foreign keys
        violations = check_foreign_keys(conn)
        if violations:
            logger.error(
                f"Foreign key integrity check failed with {len(violations)} violations!"
            )
            raise ValueError(f"Foreign key violations found: {violations[:5]}")

        logger.info("Foreign key check passed: 0 violations.")

    audit_df = pd.DataFrame(audit_records)
    audit_csv = out_dir / "load_audit.csv"
    audit_df.to_csv(audit_csv, index=False)
    logger.info(f"Exported load audit to {audit_csv}")

    return audit_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    audit = load_database(reset=True)
    print("\n" + "=" * 70)
    print("N100 PLATFORM — FULL DATA LOAD AUDIT (12 DATASETS)")
    print("=" * 70)
    print(audit.to_string(index=False))
    print("=" * 70)
