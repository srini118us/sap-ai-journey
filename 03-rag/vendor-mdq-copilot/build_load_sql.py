#!/usr/bin/env python3
"""
Convert generated CSVs into HANA INSERT statements.
Produces 03_load_data.sql with batched INSERTs (100 rows per batch).
"""

import csv
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OUT = BASE / "03_load_data.sql"

def sql_val(v, col_name):
    """Format a value for HANA SQL."""
    if v is None or v == '':
        # empty strings for date columns become NULL
        if col_name in ('RESOLVED_ON', 'TAX_ID'):
            return 'NULL'
        return "''"
    # Numeric columns
    if col_name in ('AMOUNT', 'RISK_SCORE', 'CHUNK_ORDER', 'TOKEN_COUNT'):
        return str(v)
    # Date columns
    if col_name in ('CREATED_ON', 'LAST_MODIFIED', 'INVOICE_DATE', 'POSTING_DATE',
                    'DETECTED_ON', 'RESOLVED_ON'):
        return f"TO_DATE('{v}', 'YYYY-MM-DD')"
    # String: escape single quotes
    escaped = str(v).replace("'", "''")
    return f"'{escaped}'"

def build_inserts(csv_path, table_name, batch_size=1):
    """Single-row INSERTs for max HANA compatibility."""
    lines = [f"-- Loading {table_name}"]
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        col_list = ", ".join(cols)
        rows = list(reader)
        total = len(rows)
        for row in rows:
            vals = ", ".join(sql_val(row[c], c) for c in cols)
            lines.append(f"INSERT INTO {table_name} ({col_list}) VALUES ({vals});")
        lines.append(f"-- {table_name}: {total} rows loaded\n")
    return "\n".join(lines)

# Build full script
parts = [
    "-- ============================================================",
    "-- Vendor MDQ Copilot: bulk load CSV data into HANA tables",
    "-- Run AFTER 01_ddl.sql has created empty tables",
    "-- Executes ~10 large batched INSERT statements",
    "-- ============================================================\n",
    "-- Optional: clear existing data (safe rerun)",
    "DELETE FROM QUALITY_ISSUES;",
    "DELETE FROM QUALITY_RULES;",
    "DELETE FROM TRANSACTIONS;",
    "DELETE FROM VENDORS;\n",
    build_inserts(DATA / "vendors.csv", "VENDORS"),
    build_inserts(DATA / "transactions.csv", "TRANSACTIONS"),
    build_inserts(DATA / "quality_rules.csv", "QUALITY_RULES"),
    build_inserts(DATA / "quality_issues.csv", "QUALITY_ISSUES"),
    "-- ============================================================",
    "-- Verify row counts",
    "-- ============================================================",
    "SELECT 'VENDORS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM VENDORS",
    "UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM TRANSACTIONS",
    "UNION ALL SELECT 'QUALITY_RULES', COUNT(*) FROM QUALITY_RULES",
    "UNION ALL SELECT 'QUALITY_ISSUES', COUNT(*) FROM QUALITY_ISSUES;"
]

with open(OUT, "w", encoding='utf-8') as f:
    f.write("\n".join(parts))

size_kb = OUT.stat().st_size / 1024
print(f"Generated: {OUT}")
print(f"Size: {size_kb:.1f} KB")
