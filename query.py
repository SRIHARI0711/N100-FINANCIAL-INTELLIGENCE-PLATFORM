"""Simple script to run quick SQL queries against nifty100.db from command prompt."""

import sqlite3
import sys

DB_PATH = "data/nifty100.db"

# Default query if none provided
DEFAULT_SQL = "SELECT id, company_name, roce_percentage FROM companies LIMIT 5;"

sql = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_SQL

print(f"Connecting to {DB_PATH}...\nRunning query:\n  {sql}\n")
print("-" * 65)

try:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []

        # Print header
        if col_names:
            header_str = " | ".join(f"{c:<18}" for c in col_names)
            print(header_str)
            print("-" * 65)

        # Print rows
        for row in rows:
            print(" | ".join(f"{str(val):<18}" for val in row))

        print("-" * 65)
        print(f"Total rows returned: {len(rows)}\n")
except Exception as e:
    print(f"Error executing query: {e}")
