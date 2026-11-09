"""Unit tests for SQLite database schema, foreign keys, and integrity constraints."""

import sqlite3

from db.loader import check_foreign_keys, get_connection, init_db


def test_schema_creates_all_tables(tmp_path):
    """Verify that schema.sql creates all 12 core and supporting tables."""
    test_db = tmp_path / "test_schema.db"
    init_db(test_db)

    with get_connection(test_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "companies",
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
    }
    assert expected_tables.issubset(tables)


def test_foreign_key_constraint_enforced(tmp_path):
    """Verify that inserting child records with non-existent company_id fails."""
    test_db = tmp_path / "test_fk.db"
    init_db(test_db)

    with get_connection(test_db) as conn:
        # Inserting child row without parent company must fail
        try:
            conn.execute(
                "INSERT INTO profitandloss (company_id, year, sales, expenses, operating_profit, opm_percentage) "
                "VALUES ('NON_EXISTENT', '2023-03', 100, 80, 20, 20);"
            )
            assert False, "Expected sqlite3.IntegrityError for FK violation"
        except sqlite3.IntegrityError:
            pass


def test_annual_pk_uniqueness_enforced(tmp_path):
    """Verify that inserting duplicate (company_id, year) into P&L fails."""
    test_db = tmp_path / "test_pk.db"
    init_db(test_db)

    with get_connection(test_db) as conn:
        # First insert valid company
        conn.execute(
            "INSERT INTO companies (id, company_name, face_value) VALUES ('TCS', 'Tata Consultancy Services', 1);"
        )
        # First annual statement
        conn.execute(
            "INSERT INTO profitandloss (company_id, year, sales, expenses, operating_profit, opm_percentage) "
            "VALUES ('TCS', '2023-03', 100, 80, 20, 20);"
        )
        # Duplicate annual statement must fail
        try:
            conn.execute(
                "INSERT INTO profitandloss (company_id, year, sales, expenses, operating_profit, opm_percentage) "
                "VALUES ('TCS', '2023-03', 120, 90, 30, 25);"
            )
            assert False, (
                "Expected sqlite3.IntegrityError for duplicate (company_id, year)"
            )
        except sqlite3.IntegrityError:
            pass


def test_live_database_integrity():
    """Verify that the primary database nifty100.db passes foreign key checks and contains 92 companies."""
    from db.loader import DEFAULT_DB_PATH

    assert DEFAULT_DB_PATH.exists(), "nifty100.db must exist"

    with get_connection(DEFAULT_DB_PATH) as conn:
        # Check foreign keys
        violations = check_foreign_keys(conn)
        assert len(violations) == 0, (
            f"Expected 0 FK violations, found {len(violations)}"
        )

        # Check companies count == 92
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies;")
        company_count = cursor.fetchone()[0]
        assert company_count == 92
